# Cutie Circuits — Spidey

A three-servo wire-leg hexapod controlled over a private laptop hotspot by a
NodeMCU ESP8266. Motion runs on the MCU; Python sends commands and maintains a
heartbeat. Includes firmware, migration tools, calibration and earlier experiments.

**Status:** the owner observed smooth forward walking after joining the servo
supply ground to NodeMCU GND. Rightward drift is unresolved. Only the forward
eight-phase gait is implemented. A cycle is a gait repetition, not a distance.

## Wiring

Disconnect the LiPo before wiring, flashing or untangling the robot.

| Connection | Destination |
|---|---|
| D5 / GPIO14 | Left walking servo signal, joint 1 |
| D6 / GPIO12 | Right walking servo signal, joint 2 |
| D7 / GPIO13 | Middle tilt servo signal, joint 3 |
| ESC/BEC regulated 5 V | Receiver power rails → servo red/+ wires |
| Receiver/BEC ground | Servo brown/black wires **and NodeMCU GND** |
| USB charger, power bank or laptop | NodeMCU USB power |

**Shared ground is required even with separate supplies.** The missing ground
caused unreliable behavior during development. Leave VIN disconnected when USB
powers NodeMCU. Never put 5 V on GPIO/3V3 or connect the 3S LiPo directly to the MCU.
The receiver distributes power only; servo signals come from NodeMCU, not receiver
channel outputs. BEC capacity under three-servo load has not been measured. The
BLDC motor is not part of the gait; remove any propeller if it remains connected.

## Move the same robot to another Windows laptop

Install Git and **Python 3.11 or 3.12** with Add Python to PATH. Install the board's
appropriate USB serial driver (CH340 or CP210x, depending on the clone). Use Windows
10/11 and a Wi-Fi adapter capable of a 2.4 GHz Mobile hotspot.

```powershell
git clone https://github.com/Rtx09x/cutie-circuits-spidey.git
cd cutie-circuits-spidey
```

**Privately copy `.local/wifi.json` from the old PC into the same location before
running setup.** It contains the hotspot password and command token already
flashed on the board. Never upload it or share screenshots of it. Stop the old
PC's hotspot before running the same hotspot on the new PC.

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File setup.ps1
```

Setup creates `.venv`, installs pinned tools, reuses private credentials, generates
`include/secrets.h`, starts Windows Mobile hotspot, and lists serial ports. It
does not flash or move the robot. With matching copied credentials and the same
board, **no upload or calibration restore is needed**: settings remain in EEPROM.

Connect the laptop to venue Wi-Fi or Ethernet first; the hotspot helper needs an
internet connection profile. NodeMCU joins only the private hotspot. Ethernet
uplink plus USB Wi-Fi hotspot was tested. Simultaneous venue Wi-Fi and hotspot
depends on the laptop/adapter; rehearse it or bring the second USB Wi-Fi adapter.

Discover the board and check its settings:

```powershell
.venv/Scripts/python.exe tools/setup_robot.py discover
.venv/Scripts/python.exe tools/hexapod.py status
.venv/Scripts/python.exe tools/hexapod.py config
.venv/Scripts/python.exe tools/hexapod.py timing
```

DHCP addresses change. If cached-neighbor discovery fails, get its address from
Windows Settings → Mobile hotspot → connected devices, then authenticate and save
it (the address below is only an example):

```powershell
.venv/Scripts/python.exe tools/setup_robot.py discover --host 192.168.137.123
```

Or disconnect the LiPo and discover via USB; this resets the board:

```powershell
.venv/Scripts/python.exe tools/setup_robot.py discover --port COM7 --servo-power-disconnected
```

## Fresh credentials or replacement board

Without a copied private configuration, setup generates new credentials. The
existing board must be flashed to learn them. Unplug the LiPo and BEC + to VIN;
leave NodeMCU on USB. Replace COM7 with the actual port:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File setup.ps1 -Flash -Port COM7 -ServoPowerDisconnected
```

This uploads **hexapod firmware**. Do not run a bare root `platformio run -t upload`;
the root project is an older motor experiment. Manual equivalent:

```powershell
.venv/Scripts/python.exe tools/setup_robot.py init
powershell.exe -NoProfile -ExecutionPolicy Bypass -File tools/hotspot.ps1
.venv/Scripts/python.exe -m platformio run -d hexapod
.venv/Scripts/python.exe -m platformio run -d hexapod -t upload --upload-port COM7
.venv/Scripts/python.exe tools/setup_robot.py discover --port COM7 --servo-power-disconnected
```

Normal upload usually preserves EEPROM calibration. Back it up first; don't use
erase-flash casually. Replacement boards need a profile and mechanical calibration.

## Demo commands

Verify horn alignment, mapping and clearance before connecting servo power.
Start with one cycle, then increase the count:

```powershell
.venv/Scripts/python.exe tools/onboard_walk.py --steps 1 --speed 100
.venv/Scripts/python.exe tools/onboard_walk.py --steps 20 --speed 100
.venv/Scripts/python.exe tools/hexapod.py stop
```

The runner centers servos individually on enable, runs 1–20 cycles, and maintains
the heartbeat. **Enable sends a direct center command**; the MCU cannot know the
actual position after an unpowered servo relaxes. Keep legs clear. The robot can
drift right: use a clear floor area. Signals turn off after completion, STOP,
detected Wi-Fi loss or three seconds without an authenticated command.

Ctrl+C interrupts the runner. Only one TCP client is accepted, so a separate STOP
client may be rejected while the runner owns the connection. If stopping fails or
a leg jams, disconnect the LiPo. A hung MCU or electrical fault can defeat software
stopping. An SG90 provides no external angle/stall feedback; a blocked servo can
keep pushing even within saved pulse limits. Signals off may let legs relax.

Timing is adjustable over Wi-Fi and saved on the MCU, with all signals off:

```powershell
# Last fast demo setting (rounded upward by the controller's update interval).
.venv/Scripts/python.exe tools/hexapod.py timing 25 25
# Slower reference for supervised clearance checks.
.venv/Scripts/python.exe tools/hexapod.py timing 500 500
```

Numbers are movement and pause milliseconds. Movement supports 20–60000 ms,
pause 0–60000 ms. The motion loop updates every 20 ms. These are command durations,
not measured servo speed. Speed 100 uses that duration; lower speeds stretch it
toward 8 seconds without changing the settling pause. Extremely short commands
may not allow the physical servo to reach its target before the next phase.

## Calibration backup and restore

Export a live credential-free snapshot before travel:

```powershell
.venv/Scripts/python.exe tools/setup_robot.py snapshot --output profiles/my-spidey.json
```

The included [last-known profile](profiles/spidey-last-known.json) is from the chat
record, **not a fresh snapshot**: the board was offline during packaging. It
includes the latest unverified D5 drift adjustment. Prefer your live snapshot.
For the same mechanical assembly, restore with servo power disconnected:

```powershell
.venv/Scripts/python.exe tools/setup_robot.py restore profiles/my-spidey.json --servo-power-disconnected
```

Restore keeps signals detached. Repositioned horns invalidate physical endpoints;
verify individual clearance before walking, even with a previously valid profile.

## Troubleshooting

- **No hotspot:** connect a laptop internet uplink first. Disable Mobile hotspot's
  automatic power-saving shutdown. A captive portal may need completing on the
  laptop. Rehearse with the new laptop before the demo.
- **Adapter cannot host:** configure Windows Mobile hotspot manually on 2.4 GHz,
  or use the USB Wi-Fi adapter. Simultaneous internet Wi-Fi and hotspot isn't
  guaranteed on every adapter.
- **Manual hotspot:** on a fresh local configuration run
  `python tools/setup_robot.py init --existing --ssid YOUR_SSID`; enter its password
  privately, then flash the generated token/header. Init deliberately reuses an
  existing JSON file rather than silently rotating a working board's credentials.
- **AUTH fails:** local token and flashed token differ. Copy the original private
  JSON or flash the new credentials. Never post them publicly.
- **Offline after restart:** restart the hotspot and rediscover; don't blindly
  resend motion commands. Check power, data cable, and the shared ground.
- **COM missing:** install the matching USB driver; close other serial terminals.
  `python -m serial.tools.list_ports` lists available ports.
- **macOS/Linux:** Python control/PlatformIO should be portable, but the Windows
  hotspot helper is not. Configure a private 2.4 GHz hotspot manually and use
  `init --existing`; use the actual serial device path for upload. This path has
  not been rehearsed on those systems.

## Before leaving for the hackathon

Install dependencies and build once while online: PlatformIO must download its
ESP8266 platform and toolchain. A clone alone is not an offline installer. Rehearse
the new laptop's hotspot and one cycle, then a longer run. Bring the USB data cable,
power supplies, Wi-Fi adapter, private `.local/wifi.json`, and calibration snapshot.
Keep the shared-ground wire secure. Store credentials and firmware binaries privately.

## Repository map

- `hexapod/`: current robot firmware and [protocol](hexapod/README.md).
- `tools/hexapod.py`, `onboard_walk.py`, `setup_robot.py`: supported demo tools.
- `setup.ps1`, `tools/hotspot.ps1`: Windows setup.
- `profiles/`: credential-free calibration records.
- Root `src/` and root `platformio.ini`: older ESC/BLDC/piezo project, **not Spidey**.
- `servo_center/`, `digispark/`, `diagnostics/`: earlier hardware experiments.
- Other Python tools: historical tests with old addresses/poses and assumptions;
  retained as source, **not supported demo controls**.

[Legacy motor notes](docs/legacy-motor-bench.md) apply only to that old firmware.
Private flash dumps and the sampled-audio header are excluded; the old motor
firmware uses silent audio when that private header is absent.

Gait research referenced [Beetle Ringo](https://github.com/beetle-ringo/arduino),
which is GPL-2.0. This repository's current eight-phase implementation was developed
for this assembly; its geometry and angles are not interchangeable with Ringo's.
No third-party audio is distributed or licensed by this repository.
