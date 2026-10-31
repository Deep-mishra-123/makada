# Makada (मकड़ा) — Voice-Agent Hexapod Robot

[![Repo](https://img.shields.io/badge/GitHub-Deep--mishra--123%2Fmakada-blue.svg)](https://github.com/Deep-mishra-123/makada)
[![Ecosystem](https://img.shields.io/badge/Robotic%20Agents-Cyberwave-orange.svg)](https://cyberwave.ai)
[![Voice AI](https://img.shields.io/badge/Voice%20AI-Sarvam%20AI%20(Bulbul%20v4--flash)-green.svg)](https://sarvam.ai)

**Makada (मकड़ा)** is a voice-enabled, three-servo wire-leg hexapod robot developed for the **Cyberwave Robotic Agents** ecosystem. It bridges physical hardware locomotion with real-time generative voice agents powered by **Sarvam AI**.

Motion primitives and gait sequences run onboard an ESP8266 (NodeMCU), communicating over a private 2.4 GHz laptop hotspot with a Python controller. The controller maintains a real-time heartbeat and synchronizes live physical motion with witty, context-aware speech commentary delivered through the laptop using **Sarvam AI's low-latency `bulbul:v4-flash` model**.

*Lineage:* Built and evolved from the original Cutie Circuits Spidey base by [Rtx09x](https://github.com/Rtx09x/cutie-circuits-spidey).

---

## 🌟 Key Highlights

- **Cyberwave Robotic Agent Locomotion:** 8-phase tripod gait executing with 20ms update cycles, individual joint calibration, and TCP telemetry streaming (`step`, `phase`, `action`, `enabled_mask`).
- **Sarvam AI Voice Intelligence:** Integrated with Sarvam's `bulbul:v4-flash` text-to-speech engine using **Ritu** (`ritu_en_reels` / `ritu_hi_reels`) and **Shubh** personas. Pre-fetches and caches synthesized audio clips locally to guarantee zero-latency async playback while walking.
- **Multilingual Persona Support:**
  - `spidey`: Witty, self-aware English robot spider commenting on mechanical balance, rightward drift, and 6-legged cardio.
  - `desi`: Hilarious Hinglish comedy persona (*"Arre bhai bhai bhai! Spidey aa gaya, raasta saaf karo!"*).
- **Synchronized Gait Milestones:** Voice triggers dynamically at takeoff, midway (~50% mark), final approach (~85%), and touchdown/parking.
- **Fail-Safe Architecture:** Watchdog heartbeat with automatic servo signal detachment upon Wi-Fi interruption, STOP command, or 3-second communication silence.

---

## 🔌 Hardware & Wiring

> [!CAUTION]
> **Always disconnect the LiPo battery before wiring, flashing, or untangling the robot.**
> Shared ground is mandatory between the BEC/receiver ground and NodeMCU GND even when operating on separate power supplies.

| Connection | Pin / Target | Function |
|---|---|---|
| **D5 / GPIO14** | Servo Joint 1 | Left walking servo signal |
| **D6 / GPIO12** | Servo Joint 2 | Right walking servo signal |
| **D7 / GPIO13** | Servo Joint 3 | Middle tilt servo signal |
| **ESC / BEC (5V)** | Receiver Power Rails | Servo red/+ wires |
| **Receiver Ground** | Servo black/brown wires | **Shared with NodeMCU GND** |
| **Micro-USB** | Laptop / Power Bank | NodeMCU 3.3V logic power |

*Note: Never supply 5V directly to ESP8266 GPIO/3V3 pins. Keep VIN disconnected when powered over USB.*

---

## 🚀 Quickstart & Setup (Windows)

### 1. Clone the Repository
```powershell
git clone https://github.com/Deep-mishra-123/makada.git
cd makada
```

### 2. Run Automatic PC Setup
Requires Python 3.11+ and a 2.4 GHz capable Wi-Fi adapter.
```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File setup.ps1
```
*Setup builds `.venv`, installs pinned dependencies (`platformio`, `pyserial`, `requests`), starts the private 2.4 GHz Windows Mobile Hotspot (`CutieCircuits-Bench`), and generates credential headers.*

### 3. Configure Sarvam AI Voice
Save your [Sarvam AI](https://sarvam.ai) API key locally (stored in `.local/sarvam.json`, strictly excluded from git):
```powershell
.venv/Scripts/python.exe tools/talking_walk.py --set-key "YOUR_SARVAM_API_KEY"
```

Test the speaker directly on your PC:
```powershell
.venv/Scripts/python.exe tools/sarvam_speaker.py "Hello Cyberwave! Makada is ready to walk and talk."
```

---

## 🤖 Operation & Demo Commands

### A. Walk & Talk (Sarvam AI Voice Commentary)
```powershell
# English witty spider (10 steps)
.venv/Scripts/python.exe tools/talking_walk.py --steps 10 --speed 100 --persona spidey

# Hinglish comedic spider (20 steps)
.venv/Scripts/python.exe tools/talking_walk.py --steps 20 --speed 100 --persona desi

# Custom speed, steps, and voice model
.venv/Scripts/python.exe tools/talking_walk.py --steps 15 --speed 80 --persona spidey --speaker ritu --model bulbul:v4-flash
```

### B. Standard Silent Walk
```powershell
# Single test cycle for mechanical clearance
.venv/Scripts/python.exe tools/onboard_walk.py --steps 1 --speed 100

# 20 full cycles
.venv/Scripts/python.exe tools/onboard_walk.py --steps 20 --speed 100
```

### C. Emergency Stop & Diagnostics
```powershell
# Immediate stop & servo signal detachment
.venv/Scripts/python.exe tools/hexapod.py stop

# Read real-time MCU status
.venv/Scripts/python.exe tools/hexapod.py status

# Inspect joint calibration
.venv/Scripts/python.exe tools/hexapod.py config

# Adjust move/settle timing (default 25ms move / 25ms settle)
.venv/Scripts/python.exe tools/hexapod.py timing 25 25
```

---

## ⚡ Flashing the Firmware

If you are setting up a fresh NodeMCU board:
1. Disconnect the LiPo and servo power.
2. Connect NodeMCU via USB and install the CP2102/CH340 driver if prompted.
3. Flash the hexapod firmware:
   ```powershell
   powershell.exe -NoProfile -ExecutionPolicy Bypass -File setup.ps1 -Flash -Port COM3 -ServoPowerDisconnected
   ```

---

## 📁 Repository Structure

- `hexapod/` — NodeMCU ESP8266 Arduino firmware (EEPROM calibration, motion engine, TCP server).
- `tools/talking_walk.py` — Synchronized walking runner with Sarvam AI voice triggers.
- `tools/sarvam_speaker.py` — Sarvam TTS client with local audio cache and non-blocking Windows audio playback.
- `tools/onboard_walk.py` — Core bounded gait execution tool with telemetry heartbeat.
- `tools/hexapod.py` — CLI for direct TCP robot control (`status`, `config`, `timing`, `stop`).
- `tools/setup_robot.py` — Hotspot discovery and credential setup.
- `profiles/` — Credential-free joint calibration snapshots.

---

## 🛡️ Security & Privacy Notice

All private configuration files (`.local/wifi.json`, `.local/sarvam.json`, `include/secrets.h`, and audio caches) are strictly git-ignored. Never commit or share your local Wi-Fi tokens or API keys publicly.

---

## 📜 Credits & License

- **Ecosystem:** Developed for [Cyberwave](https://cyberwave.ai) Robotic Agents Hackathon.
- **Voice Intelligence:** Powered by [Sarvam AI](https://sarvam.ai) Text-to-Speech API (`bulbul:v4-flash`).
- **Base Architecture:** Derived from Cutie Circuits Spidey by [Rtx09x](https://github.com/Rtx09x/cutie-circuits-spidey).
- Gait research references [Beetle Ringo](https://github.com/beetle-ringo/arduino) (GPL-2.0).
