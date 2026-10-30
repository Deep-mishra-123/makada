"""Continuously sweep one unloaded servo. Ctrl+C stops the test."""
import json
import time
from pathlib import Path
from bench import Board

config = json.loads((Path(__file__).resolve().parents[1] / '.local/wifi.json')
                    .read_text(encoding='utf-8-sig'))
board = Board(None, config['host'], config['token'])
try:
    board.send('STOP', 'STOP requested')
    board.send('LIMIT 2000', 'OK LIMIT 2000')
    board.send('ARM', 'OK ARM')
    board.send('SET 1500', 'OK SET 1500')
    board.hold(0.8)
    board.send('STOP', 'STOP requested')
    while True:
        board.send('ARM', 'OK ARM')
        board.send('SET 2000', 'OK SET 2000')
        board.hold(0.45)
        board.send('SET 1000', 'OK SET 1000')
        board.hold(0.45)
        board.send('STOP', 'STOP requested')
except KeyboardInterrupt:
    print('Sweep interrupted')
finally:
    board.close()
