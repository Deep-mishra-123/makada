"""Loop the embedded test clip until interrupted."""
import json
import time
from pathlib import Path
from bench import Board

config = json.loads((Path(__file__).resolve().parents[1] / '.local/wifi.json')
                    .read_text(encoding='utf-8-sig'))
board = Board(None, config['host'], config['token'])
try:
    while True:
        board.link.write(b'CLIP\n')
        board.wait('OK CLIP', timeout=30)
        time.sleep(0.15)
except KeyboardInterrupt:
    pass
finally:
    board.close()
