# Smart Room Monitor

An AI-powered room monitoring system that uses a webcam, cloud vision analysis, and an ESP32 microcontroller to automatically manage room lighting, a fan, and audio alerts based on occupancy and cleanliness.

---

## Features

- **Two-tier person detection** — fast local face/body detection via OpenCV Haar Cascades, supplemented by Groq Vision LLM analysis for richer scene understanding
- **Automatic device control** — turns light and fan ON when a person enters, OFF when the room is empty
- **Messy room alerts** — identifies cluttered objects (bottles, cups, books, clothes, etc.) and plays a clean-up audio reminder
- **Homework reminder** — fires a timed audio reminder after a configurable delay
- **Welcome & warning audio** — plays a welcome sound on arrival and a warning when the room is left with devices still on
- **Override mode** — press `SPACE` to suspend automation while keeping the live feed and HUD active
- **Real-time HUD overlay** — semi-transparent status panel showing device states, person detection, object alerts, and next-scan countdown

---

## Project Structure

```
smart-room-monitor/
├── main.py               # Entry point — orchestrates all modules
├── config.py             # All tunable settings (API key, timing, paths, camera)
├── detection.py          # Two-tier detection engine (OpenCV + Groq Vision)
├── device_controller.py  # ESP32 serial control for LED and fan
├── audio_manager.py      # Thread-safe MP3 playback with cooldown policies
├── ui_renderer.py        # OpenCV HUD overlay renderer
├── requirements.txt      # Pinned Python dependencies
└── audio/
    ├── welcome.mp3
    ├── warning.mp3
    ├── clean_room.mp3
    └── homework.mp3
```

---

## Requirements

**Python 3.10 or later** is required (uses `int | None` union type hints).

Install all dependencies from the provided `requirements.txt`:

```bash
pip install -r requirements.txt
```

| Package          | Min version | Purpose                                    |
|------------------|-------------|--------------------------------------------|
| `opencv-python`  | `4.9.0`     | Webcam capture, Haar Cascades, HUD drawing |
| `groq`           | `0.9.0`     | Groq Vision LLM API client                 |
| `pygame`         | `2.5.0`     | MP3 audio playback                         |
| `numpy`          | `1.26.0`    | Array operations (OpenCV dependency)       |

> **ESP32 users:** `pyserial` is required for hardware control but is not included in `requirements.txt`. Install it separately:
> ```bash
> pip install pyserial
> ```
> If no ESP32 is connected the system runs in simulation mode without it.

---

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/your-username/smart-room-monitor.git
cd smart-room-monitor
```

### 2. Set your Groq API key

The recommended approach is to export it as an environment variable:

```bash
# Linux / macOS
export GROQ_API_KEY="gsk_your_key_here"

# Windows (Command Prompt)
set GROQ_API_KEY=gsk_your_key_here
```

Alternatively, open `config.py` and paste the key directly into the `GROQ_API_KEY` field (not recommended for shared code).

Get a free API key at [console.groq.com](https://console.groq.com).

### 3. Add your audio files

Place four MP3 files in the `audio/` folder (create it if it doesn't exist):

```
audio/welcome.mp3       # Played when a person enters
audio/warning.mp3       # Played when the room is left with devices on
audio/clean_room.mp3    # Played when clutter is detected
audio/homework.mp3      # Timed homework reminder
```

The paths can be changed in `config.py`.

### 4. Connect the ESP32 (optional)

The system auto-detects ESP32 boards by scanning serial ports for USB/CP210x/CH340 descriptors. To specify a port manually, edit `main.py`:

```python
self.devices = DeviceController(port="COM6")   # Windows
self.devices = DeviceController(port="/dev/ttyUSB0")  # Linux / macOS
```

If no ESP32 is found the system starts in **simulation mode** — all device state changes are printed to the console but no serial commands are sent.

#### Expected ESP32 serial commands

Your ESP32 firmware should listen for these newline-terminated strings at **115200 baud**:

| Command      | Action          |
|--------------|-----------------|
| `LIGHT_ON`   | Turn LED on     |
| `LIGHT_OFF`  | Turn LED off    |
| `FAN_ON`     | Start fan motor |
| `FAN_OFF`    | Stop fan motor  |

### 5. Run

```bash
python main.py
```

---

## Configuration

All settings are centralised in `config.py`:

| Setting              | Default | Description                                                   |
|----------------------|---------|---------------------------------------------------------------|
| `GROQ_API_KEY`       | —       | Your Groq API key (prefer env var)                            |
| `GROQ_VISION_MODEL`  | `meta-llama/llama-4-scout-17b-16e-instruct` | Vision model to use |
| `DETECTION_INTERVAL` | `10`    | Seconds between cloud API calls                               |
| `HOMEWORK_REMINDER`  | `30`    | Seconds after launch before the homework reminder fires       |
| `AUDIO_COOLDOWN`     | `30`    | Minimum gap (seconds) before the same audio event re-fires    |
| `CAMERA_INDEX`       | `0`     | Webcam index (0 = default system camera)                      |
| `CAMERA_WIDTH`       | `1280`  | Capture resolution width                                      |
| `CAMERA_HEIGHT`      | `720`   | Capture resolution height                                     |

---

## Architecture

```
main.py (SmartRoomMonitor)
├── DetectionEngine        — Tier-1 local + Tier-2 Groq cloud detection
│     ├── detect_faces()   — OpenCV Haar Cascade (runs every frame)
│     └── analyze_frame()  — Groq Vision API (runs every N seconds, background thread)
│
├── DeviceController       — ESP32 serial bridge for light and fan
│
├── AudioManager           — Thread-safe MP3 player with per-event cooldown
│     └── Policies: queue | interrupt | skip
│
└── UIRenderer             — OpenCV HUD overlay drawn on each frame
```

The cloud analysis runs on a **dedicated daemon thread** so it never blocks the video loop. Results are passed back via a single-slot `queue.Queue`.

---

## Controls

| Key         | Action                                      |
|-------------|---------------------------------------------|
| `SPACE`     | Toggle override mode (suspend automation)   |
| `Q` / `ESC` | Quit and release all resources              |

---

## HUD Overview

```
┌─────────────────────────────┐
│  AUTO MODE                  │
│ ─────────────────────────── │
│  LIGHT :  ON                │
│  FAN   :  ON                │
│  PERSON : DETECTED          │
│  Room  : Clean              │
│  Next scan : 7s             │
└─────────────────────────────┘
                    [hint bar: SPACE / Q]
```

The panel becomes **OVERRIDE MODE** (yellow) when automation is suspended.

---

## Troubleshooting

**Webcam not opening**
Verify `CAMERA_INDEX` in `config.py`. Try index `1` or `2` if you have multiple cameras.

**Groq API errors**
Confirm your API key is set correctly and that the model name in `GROQ_VISION_MODEL` is still valid — check [console.groq.com/docs/vision](https://console.groq.com/docs/vision) for the current model list.

**No audio playback**
Check that `pygame.mixer` initialised successfully (look for `[AUDIO] pygame init failed` in the console). Ensure the MP3 files exist at the configured paths.

**ESP32 not detected**
On Linux you may need to add your user to the `dialout` group:
```bash
sudo usermod -aG dialout $USER
```
Then log out and back in.

---

## License

MIT License. See `LICENSE` for details.