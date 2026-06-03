# Instru-Extract
### Professional Audio Source Separation — Powered by Meta's Demucs

Splits any music track into individual stems — **Instrumental, Vocals, Drums, Bass, Other** —
using state-of-the-art deep learning, served via a clean retro-futuristic web interface.

---

## Supported Input Formats

| Format | Extension |
|--------|-----------|
| MP3    | .mp3      |
| WAV    | .wav      |
| FLAC   | .flac     |
| OGG    | .ogg      |
| M4A    | .m4a      |
| AAC    | .aac      |
| WMA    | .wma      |
| Opus   | .opus     |
| AIFF   | .aiff     |

---

## Prerequisites

| Requirement | Version  | Notes |
|-------------|----------|-------|
| Python      | ≥ 3.9    | [python.org](https://python.org) |
| pip         | latest   | `python -m pip install --upgrade pip` |
| ffmpeg      | any      | **Required** — [ffmpeg.org](https://ffmpeg.org/download.html) |
| GPU (opt.)  | CUDA/MPS | CPU works too, slower |

### Installing ffmpeg

**Windows:**
```
winget install ffmpeg
```
or download from https://ffmpeg.org and add to PATH.

**macOS:**
```
brew install ffmpeg
```

**Ubuntu/Debian:**
```
sudo apt install ffmpeg
```

---

## Quick Start

```bash
# 1. Clone / unzip the project
cd stem_extract

# 2. Create a virtual environment (recommended)
python -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Launch
python app.py
```

Then open **http://localhost:5000** in your browser.

---

## Usage

1. **Drop** (or click to select) any audio file onto the upload zone.
2. **Choose** a model and separation mode:
   - **Instrumental Only** — extracts `instrumental` + `vocals` (fast, 2 stems)
   - **Full 4-Stem Split** — extracts `vocals`, `drums`, `bass`, `other` (slower, more stems)
3. Select WAV (lossless) or MP3 (smaller) output format.
4. Click **INITIATE EXTRACTION** and watch the real-time log.
5. **Download** individual stems or all as a single ZIP.

---

## Models

| Model | Description | Best for |
|-------|-------------|----------|
| `htdemucs` | Hybrid Transformer (default) | General use |
| `htdemucs_ft` | Fine-tuned variant | Music with clean vocals |
| `mdx_extra` | MDX architecture | Vocal isolation |
| `mdx_extra_q` | Quantized MDX | Speed / low VRAM |

On first run, Demucs will download the model weights (~200 MB each) automatically.

---

## Custom Port

```bash
python app.py 8080
```

---

## GPU Acceleration

Demucs automatically uses CUDA (NVIDIA) or MPS (Apple Silicon) if available.
To force CPU:
```bash
python -c "import demucs.separate; demucs.separate.main(['--device','cpu','file.mp3'])"
```
Or modify `app.py` and add `'--device', 'cpu'` to the `cmd` list in `_run()`.

---

## File Size Limits

Default: **500 MB** per file.  
To increase, edit `app.py`:
```python
app.config["MAX_CONTENT_LENGTH"] = 1024 * 1024 * 1024   # 1 GB
```

---

## Notes

- Output files are stored in `outputs/` and `uploads/` during the session.
- Clicking **"Extract Another Track"** removes the previous job's files automatically.
- WAV outputs are float32 @ 44.1 kHz (lossless). MP3 outputs are 320 kbps.

---

## Credits

- **Demucs** — © Meta AI Research (MIT License)  
  https://github.com/facebookresearch/demucs  
- **Flask** — © Pallets  
- UI design — Instru-Extract
