"""Repeat short piezo tones until interrupted."""
import json
import time
from pathlib import Path
from bench import Board

config = json.loads((Path(__file__).resolve().parents[1] / '.local/wifi.json')
                    .read_text(encoding='utf-8-sig'))
board = Board(None, config['host'], config['token'])
try:
    while True:
        for frequency in (440, 880, 1500):
            board.send(f'BEEP {frequency} 400', f'OK BEEP {frequency} 400')
            time.sleep(0.5)
except KeyboardInterrupt:
    pass
finally:
    board.close()
