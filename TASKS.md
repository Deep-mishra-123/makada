Mission: establish USB control of the NodeMCU ESC output before powering the motor.

- [x] Identify board and preserve original 4 MB flash.
- [x] Implement disarmed boot, bounded throttle, heartbeat timeout and bench time limit.
- [x] Build and flash firmware; upload hash verified on COM18.
- [x] Exercise serial commands, rejection paths and timeouts with battery disconnected.
- [x] Document wiring and controlled next test; leave board disarmed.

Verification on 2026-10-27: PlatformIO build/upload succeeded; Python syntax
check passed; `python tools/bench.py check --battery-disconnected` passed on
the actual ESP8266. Final state: disarmed, 1000 µs command. Physical waveform
and powered ESC/motor behaviour remain unverified.

Wi-Fi milestone (2026-10-28):

- [x] Detect TP-Link USB adapter and start private Windows Mobile hotspot on 2.4 GHz.
- [x] Generate local credentials; add authenticated single-controller Wi-Fi transport.
- [x] Build and flash Wi-Fi firmware; verify upload hash.
- [x] Discover board IP and run command/timeout checks over Wi-Fi, battery disconnected.
- [x] Verify rejected unauthenticated commands, exclusive controller and disconnect stop.
- [x] Leave board disarmed; document demo setup and remaining limits.

Tested internet uplink is Ethernet. Concurrent internet Wi-Fi plus private
hotspot and powered motor behaviour remain to be verified.

LED milestone (2026-10-28):

- [x] Add non-blocking Wi-Fi status LED on GPIO2 and command activity LED on GPIO16.
- [x] Build/upload v3 and run Wi-Fi command checks with battery disconnected.
- [x] Verify reported command LED state follows accepted throttle and clears on STOP.
- [x] Fix a test timing race when the run-limit event arrives during a heartbeat reply.
- [ ] User to confirm physical LEDs match the common two-LED DevKit wiring.

Final state after checks: disarmed, pulse_us=1000, motor_led_active=0, wifi=1.
