"""
STEM::EXTRACT — Professional Audio Source Separation
Powered by Meta's Demucs HTDemucs deep learning model.

Supports: MP3, WAV, FLAC, OGG, M4A, AAC, WMA, OPUS, AIFF
Outputs:  Instrumental, Vocals, Drums, Bass, Other stems
"""

from flask import Flask, request, jsonify, render_template, send_file, abort, Response
from werkzeug.utils import secure_filename
from pathlib import Path
from io import BytesIO
import os, uuid, threading, subprocess, shutil, time, json, re, zipfile, sys

# ──────────────────────────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────────────────────────
app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 500 * 1024 * 1024   # 500 MB

BASE_DIR    = Path(__file__).parent
UPLOAD_DIR  = BASE_DIR / "uploads"
OUTPUT_DIR  = BASE_DIR / "outputs"
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

ALLOWED_EXT = {".mp3", ".wav", ".flac", ".ogg", ".m4a", ".aac",
               ".wma", ".opus", ".aiff", ".aif", ".mp4"}

MODELS = {
    "htdemucs": {
        "label":  "HTDemucs",
        "detail": "Hybrid Transformer · best all-round quality",
        "speed":  "standard",
    },
    "htdemucs_ft": {
        "label":  "HTDemucs Fine-tuned",
        "detail": "Fine-tuned on music · best vocal clarity",
        "speed":  "standard",
    },
    "mdx_extra": {
        "label":  "MDX Extra",
        "detail": "Excels at vocal isolation",
        "speed":  "standard",
    },
    "mdx_extra_q": {
        "label":  "MDX Extra Quantized",
        "detail": "Faster, lower VRAM requirement",
        "speed":  "fast",
    },
}

STEM_META = {
    "no_vocals": {"label": "Instrumental",  "icon": "🎵", "color": "#00ffd0"},
    "vocals":    {"label": "Vocals",         "icon": "🎤", "color": "#ff3c8a"},
    "drums":     {"label": "Drums",          "icon": "🥁", "color": "#ffaa00"},
    "bass":      {"label": "Bass",           "icon": "🎸", "color": "#7c6aff"},
    "other":     {"label": "Other / Melody", "icon": "🎹", "color": "#00cfff"},
}

# ──────────────────────────────────────────────────────────────────
# Job registry (in-memory)
# ──────────────────────────────────────────────────────────────────
jobs: dict = {}
_lock = threading.Lock()


def _ts():
    return time.strftime("%H:%M:%S")


def update_job(job_id: str, **kw):
    with _lock:
        if job_id not in jobs:
            return
        jobs[job_id].update(kw)
        if "message" in kw:
            jobs[job_id].setdefault("log", []).append(f"[{_ts()}] {kw['message']}")


# ──────────────────────────────────────────────────────────────────
# Routes
# ──────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html", models=MODELS, stem_meta=STEM_META)


@app.route("/upload", methods=["POST"])
def upload():
    if "file" not in request.files:
        return jsonify({"error": "No file in request"}), 400

    f = request.files["file"]
    if not f.filename:
        return jsonify({"error": "Empty filename"}), 400

    ext = Path(f.filename).suffix.lower()
    if ext not in ALLOWED_EXT:
        return jsonify({"error": f"Unsupported format: {ext}"}), 400

    job_id  = str(uuid.uuid4())[:8]
    fname   = secure_filename(f.filename)
    job_dir = UPLOAD_DIR / job_id
    job_dir.mkdir(parents=True)

    fpath = job_dir / fname
    f.save(str(fpath))
    size  = fpath.stat().st_size

    with _lock:
        jobs[job_id] = {
            "id":         job_id,
            "filename":   fname,
            "filepath":   str(fpath),
            "size":       size,
            "status":     "ready",
            "progress":   0,
            "message":    "Awaiting configuration",
            "log":        [f"[{_ts()}] Received {fname} ({size/1024/1024:.2f} MB)"],
            "stems":      {},
            "created_at": time.time(),
        }

    return jsonify({"job_id": job_id, "filename": fname, "size_mb": round(size/1024/1024, 2)})


@app.route("/process/<job_id>", methods=["POST"])
def process(job_id: str):
    with _lock:
        job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    if job["status"] == "processing":
        return jsonify({"error": "Already running"}), 409

    data   = request.get_json() or {}
    mode   = data.get("mode",   "instrumental")   # "instrumental" | "full"
    model  = data.get("model",  "htdemucs")
    fmt    = data.get("format", "wav")             # "wav" | "mp3"

    if model not in MODELS:
        model = "htdemucs"

    t = threading.Thread(target=_run, args=(job_id, mode, model, fmt), daemon=True)
    t.start()

    return jsonify({"status": "started"})


def _run(job_id: str, mode: str, model: str, fmt: str):
    job = jobs.get(job_id)
    if not job:
        return

    fp       = job["filepath"]
    out_base = OUTPUT_DIR / job_id
    out_base.mkdir(parents=True, exist_ok=True)

    update_job(job_id, status="processing", progress=5,
               message=f"Initialising {MODELS[model]['label']}…")

    try:
        cmd = [sys.executable, "-m", "demucs",
               "--out",  str(out_base),
               "--name", model]

        if mode == "instrumental":
            cmd += ["--two-stems", "vocals"]

        # Native MP3 export (requires ffmpeg)
        if fmt == "mp3":
            cmd += ["--mp3", "--mp3-bitrate", "320"]

        cmd.append(fp)

        update_job(job_id, progress=10, message=f"Running model: {model}")

        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )

        for line in proc.stdout:
            line = line.strip()
            if not line:
                continue
            m = re.search(r"(\d+(?:\.\d+)?)%", line)
            if m:
                pct  = float(m.group(1))
                prog = int(12 + pct * 0.83)
                update_job(job_id, progress=prog,
                           message=f"Separating stems… {int(pct)}%")
            elif re.search(r"[Ee]rror|[Ww]arning|[Ff]ailed", line):
                update_job(job_id, message=f"⚠ {line}")

        proc.wait()

        if proc.returncode != 0:
            raise RuntimeError(f"demucs exited with code {proc.returncode}")

        update_job(job_id, progress=97, message="Scanning output files…")

        # ── Locate stems ───────────────────────────────────────────
        stems: dict = {}
        stem_dir = out_base / model / Path(fp).stem
        ext_pat  = "*.mp3" if fmt == "mp3" else "*.wav"

        if stem_dir.exists():
            for sf in stem_dir.glob(ext_pat):
                stems[sf.stem] = str(sf)

        if not stems:
            # Fallback: recursive search
            for sf in sorted(out_base.rglob(ext_pat)):
                stems[sf.stem] = str(sf)

        if not stems:
            raise RuntimeError("No output files found — check ffmpeg is installed")

        update_job(job_id,
                   status="completed", progress=100,
                   message=f"✓ Done — {len(stems)} stem(s) ready",
                   stems=stems)

    except Exception as exc:
        update_job(job_id, status="failed", progress=0,
                   message=f"✗ {exc}")


# ──────────────────────────────────────────────────────────────────
# Status / SSE
# ──────────────────────────────────────────────────────────────────
@app.route("/status/<job_id>")
def status(job_id: str):
    with _lock:
        job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "Not found"}), 404
    return jsonify({
        "id":       job["id"],
        "status":   job["status"],
        "progress": job["progress"],
        "message":  job["message"],
        "log":      job.get("log", []),
        "stems":    list(job["stems"].keys()),
    })


@app.route("/stream/<job_id>")
def stream(job_id: str):
    """Server-Sent Events: real-time progress feed."""
    def generate():
        seen = 0
        while True:
            with _lock:
                job = jobs.get(job_id)
            if not job:
                yield f"data: {json.dumps({'error': 'not_found'})}\n\n"
                break

            log      = job.get("log", [])
            new_logs = log[seen:]
            seen     = len(log)

            payload = {
                "status":   job["status"],
                "progress": job["progress"],
                "message":  job["message"],
                "new_log":  new_logs,
                "stems":    list(job["stems"].keys()),
            }
            yield f"data: {json.dumps(payload)}\n\n"

            if job["status"] in ("completed", "failed", "cancelled"):
                break
            time.sleep(0.4)

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ──────────────────────────────────────────────────────────────────
# Download
# ──────────────────────────────────────────────────────────────────
@app.route("/download/<job_id>/<stem_name>")
def download_stem(job_id: str, stem_name: str):
    with _lock:
        job = jobs.get(job_id)
    if not job or not job.get("stems"):
        abort(404)
    path = job["stems"].get(stem_name)
    if not path or not Path(path).exists():
        abort(404)
    base = Path(job["filename"]).stem
    ext  = Path(path).suffix
    return send_file(path, as_attachment=True,
                     download_name=f"{base}_{stem_name}{ext}")


@app.route("/download/<job_id>/all/zip")
def download_all_zip(job_id: str):
    with _lock:
        job = jobs.get(job_id)
    if not job or not job.get("stems"):
        abort(404)

    buf  = BytesIO()
    base = Path(job["filename"]).stem
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, path in job["stems"].items():
            if Path(path).exists():
                zf.write(path, f"{base}_{name}{Path(path).suffix}")
    buf.seek(0)
    return send_file(buf, as_attachment=True,
                     download_name=f"{base}_stems.zip",
                     mimetype="application/zip")


# ──────────────────────────────────────────────────────────────────
# Cleanup
# ──────────────────────────────────────────────────────────────────
@app.route("/cleanup/<job_id>", methods=["DELETE"])
def cleanup(job_id: str):
    with _lock:
        job = jobs.pop(job_id, None)
    if job:
        for d in [UPLOAD_DIR / job_id, OUTPUT_DIR / job_id]:
            if d.exists():
                shutil.rmtree(d, ignore_errors=True)
    return jsonify({"ok": True})


# ──────────────────────────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
    print(f"\n  ╔══ Instru-Extract ═══════════════════════════╗")
    print(f"  ║  Running at  http://localhost:{port}         ║")
    print(f"  ╚════════════════════════════════════════════╝\n")
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
