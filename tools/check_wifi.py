"""Extra physical-board Wi-Fi checks. Motor battery MUST be disconnected."""
import argparse
import json
from pathlib import Path
import socket

from bench import Board


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--battery-disconnected", action="store_true", required=True)
    args = parser.parse_args()
    config = json.loads((Path(__file__).resolve().parents[1] / ".local/wifi.json")
                        .read_text(encoding="utf-8-sig"))
    host = config["host"]
    for command in (b"ARM\n", b"AUTH incorrect\n"):
        with socket.create_connection((host, 8266), timeout=2) as connection:
            connection.sendall(command)
            assert connection.recv(100).strip() == b"ERR AUTH"
    print("PASS: unauthenticated commands and incorrect credentials rejected")
    usb = Board("COM18")
    wifi = None
    try:
        wifi = Board(None, host, config["token"])
        usb.wait("STOP network_session")
        with socket.create_connection((host, 8266), timeout=2) as extra:
            assert extra.recv(100) == b""
        print("PASS: second connection cannot replace active controller")
        wifi.send("ARM", "OK ARM")
        wifi.send("SET 1020", "OK SET 1020")
        # Deliberately omit STOP to verify unexpected connection loss.
        wifi.link.close()
        usb.wait("STOP controller_lost")
        assert "armed=0 pulse_us=1000" in usb.send("STATUS", "STATUS")
        print("PASS: controller disconnect disarms and commands minimum throttle")
    finally:
        if wifi is not None and wifi.link.is_open:
            wifi.close()
        usb.close()


if __name__ == "__main__":
    main()
