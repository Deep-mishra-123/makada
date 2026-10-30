"""Play a short melody on the NodeMCU piezo."""
import json
import sys
import time
from pathlib import Path
from bench import Board

notes = [(523, 180), (659, 180), (784, 240), (659, 160),
         (698, 180), (880, 180), (784, 300), (659, 160),
         (523, 180), (587, 180), (659, 200), (784, 200),
         (1047, 400)]
config = json.loads((Path(__file__).resolve().parents[1] / '.local/wifi.json')
                    .read_text(encoding='utf-8-sig'))
board = Board(None, config['host'], config['token'])
try:
    while True:
        for frequency, duration in notes:
            board.send(f'BEEP {frequency} {duration}', f'OK BEEP {frequency} {duration}')
            time.sleep((duration + 35) / 1000)
        if '--repeat' not in sys.argv:
            break
        time.sleep(0.6)
except KeyboardInterrupt:
    pass
finally:
    board.close()
