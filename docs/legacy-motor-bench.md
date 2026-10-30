# Cutie Circuits motor bench

Control path: computer → private laptop hotspot → NodeMCU ESP8266 → hobby ESC → BLDC motor.
USB control remains available for diagnostics and recovery.
This firmware provides throttle commands, not measured RPM or motor telemetry.

## Wiring and power

With the motor battery disconnected:

- NodeMCU D5 (GPIO14) → verified ESC signal input.
- NodeMCU GND → ESC thin signal ground.
- ESC thin red BEC output, if present: disconnected and insulated.
- NodeMCU powered through computer USB.
- ESC motor outputs → motor; battery power goes directly to the ESC.

Use a motor and ESC rated for the battery (3S LiPo: 12.6 V fully charged).
Remove the propeller and secure the motor's mounting base; keep the bell clear.
Do not plug in the battery during flashing or `check` mode.

## Build and upload

```powershell
python -m pip install -r requirements.txt
powershell.exe -NoProfile -File tools/hotspot.ps1
python -m platformio run
python -m platformio run --target upload
python tools/bench.py discover
python tools/bench.py check --host auto --battery-disconnected
python tools/check_wifi.py --battery-disconnected
```

Default port is COM18; use `--port COMx` on the Python tool or
`--upload-port COMx` with PlatformIO if Windows assigns another port.

The old 4 MB flash backup is in `hardware-backups/`, excluded from git because
old firmware may contain Wi-Fi credentials. Restore only with the battery unplugged:

```powershell
python -m esptool --port COM18 write-flash 0 hardware-backups/nodemcu-original-2026-10-27.bin
```

## Private Wi-Fi connection

`tools/hotspot.ps1` starts Windows Mobile hotspot named `CutieCircuits-Bench`
on 2.4 GHz, sharing the current internet connection. It generates a random
Wi-Fi password and command token in `.local/wifi.json`, then generates
`include/secrets.h` for the firmware. Both are excluded from git. Firmware
binaries also contain these credentials and should stay private.

The NodeMCU joins this private hotspot automatically; it never joins the venue
network. The computer's internet uplink is separate. The tested uplink on
2026-10-28 was Ethernet with a TP-Link Wireless USB Adapter providing the
hotspot. Concurrent main Wi-Fi plus hotspot remains to be tested on the demo
setup. Legacy `netsh` hosted-network support is not required by Mobile hotspot.

After restarting Windows, run the hotspot script again. `discover` reads the
board IP over USB and saves it locally; rerun if the board's DHCP address
changes. USB is not involved in commands sent with `--host auto`. For a
wireless demo the board still needs a suitable independent power supply,
such as USB power from a power bank; do not connect the unverified ESC BEC
directly to an ESP GPIO or its 3.3 V pin.

The command server listens on TCP port 8266 and requires `AUTH <token>` first.
It accepts one controller at a time; subsequent connections are closed.
Authentication failures cannot issue motor commands. The private hotspot
provides Wi-Fi encryption; this TCP protocol itself does not provide TLS.

## Bench control

Firmware v4 adds `LIMIT <microseconds>` over authenticated Wi-Fi or USB.
It is accepted only while disarmed, ranges from 1000 to 2000 µs, and resets
to 1100 µs when the board reboots. Set a ceiling before arming, for example:

```powershell
python tools/bench.py limit --host auto --limit-us 1150
python tools/bench.py pulse --host auto --pulse-us 1150 --seconds 1
```

The ceiling allows commands up to the chosen value; it does not start the motor.
The 750 ms heartbeat and three-second armed limits remain in force. The `check`
workflow assumes the default 1100 µs ceiling; reboot or set it to 1100 first.

### LED indicators (Wi-Fi firmware v3)

- ESP module LED, GPIO2 / D4, active low: blinks every 300 ms while Wi-Fi is
  disconnected; solid on while joined to the hotspot. It indicates Wi-Fi
  association, not an active authenticated controller session.
- Second DevKit LED, GPIO16 / D0, active low: blinks every 125 ms while an
  accepted armed throttle command is above 1000 µs; off when stopped or disarmed.

This uses the common two-LED DevKit mapping. Clones may omit one LED or wire
it differently; physical observation is needed to confirm both indicators.
Neither LED proves that the ESC receives the waveform or that the motor turns.
No extra LED wiring is required on boards with both onboard LEDs.

```powershell
python tools/bench.py status --host auto
python tools/bench.py stop --host auto
# Only after verifying voltage compatibility and preparing the motor bench:
python tools/bench.py pulse --host auto --pulse-us 1020 --seconds 1
```

Board always boots disarmed, emitting 1000 µs pulses on D5 with the ESP8266 core
Servo library's 20 ms frame. The initial pulse is explicitly 1000 µs, avoiding
the library's default neutral. Wi-Fi joining runs without waiting in setup,
so minimum-throttle output and USB control do not depend on a network.

Serial protocol at 115200 baud (newline terminated):

- `STATUS`: firmware version, armed state, commanded pulse, limit, uptime.
- `ARM`: arm at 1000 µs, only after three seconds of uptime; repeated ARM disarms.
- `SET 1000` through `SET 1100`: accepted only while armed. Does not refresh heartbeat.
- `PING`: renew heartbeat while armed.
- `STOP`: immediately command 1000 µs and disarm.

Missing heartbeats for 750 ms, malformed commands, out-of-range values, and
an absolute three-second armed limit command 1000 µs and disarm. Re-arming
requires another explicit ARM. The host tool sends STOP in its cleanup path.
Wi-Fi loss and an authenticated controller disconnect also disarm. Only the
transport that armed the board may refresh its heartbeat or set throttle;
USB STOP remains available during network control.
The cap is 10% of a presumed 1000–2000 µs input range, **not 10% RPM or power**.
There is no automatic ESC calibration or full-throttle command in this build.

These protections depend on running firmware and the ESC accepting 1000 µs
as stop. They are not a hardware power cutoff. A firmware lockup or lost board
power still depends on the ESC's own signal-loss behaviour. Disconnect the
battery to cut motor power. Keep it disconnected if the ESC model/rating or
stop behaviour is uncertain.

## Validation scope

`check` exercises real board commands, rejected throttle while disarmed,
out-of-range and malformed input, heartbeat loss, and the absolute run limit.
It produces output signals, so run it only with the motor battery disconnected.
Serial state cannot verify the physical pulse waveform, ESC compatibility,
motor rotation, current, or actual speed; those require bench measurements
and a supervised powered test.

On 2026-10-28 the firmware built and uploaded with hash verification. The
complete command/timeout check passed over Wi-Fi with motor power unplugged.
`check_wifi.py` also verified authentication rejection, single-controller
access, and disarming on abrupt TCP disconnect. Final state was disarmed at
1000 µs. Powered motor operation is still unverified.

References: [PlatformIO ESP8266](https://docs.platformio.org/en/stable/platforms/espressif8266.html),
[ESP8266 Servo implementation](https://github.com/esp8266/Arduino/blob/3.1.2/libraries/Servo/src/Servo.cpp).
