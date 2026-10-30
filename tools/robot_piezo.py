"""Approximate an audio clip using monophonic piezo tones."""
import json
import subprocess
import time
from pathlib import Path
import numpy as np
from bench import Board

source = Path('Z:/Downloads/freesound_community-robot-noises-70217.mp3')
raw = subprocess.check_output(['ffmpeg', '-v', 'error', '-i', str(source),
                               '-ac', '1', '-ar', '8000', '-f', 'f32le', '-'])
audio = np.frombuffer(raw, dtype='<f4')
frame_size = 800  # 100 ms
freqs = np.fft.rfftfreq(frame_size, 1 / 8000)
mask = (freqs >= 250) & (freqs <= 2000)
window = np.hanning(frame_size)
frames = []
for start in range(0, len(audio), frame_size):
    frame = audio[start:start + frame_size]
    if len(frame) < frame_size:
        frame = np.pad(frame, (0, frame_size - len(frame)))
    rms = np.sqrt(np.mean(frame * frame))
    if rms < 0.015:
        frames.append(None)
    else:
        spectrum = np.abs(np.fft.rfft(frame * window))
        frames.append(int(freqs[mask][np.argmax(spectrum[mask])]))

config = json.loads((Path(__file__).resolve().parents[1] / '.local/wifi.json')
                    .read_text(encoding='utf-8-sig'))
board = Board(None, config['host'], config['token'])
try:
    while True:
        next_frame = time.monotonic()
        for freq in frames:
            if freq is not None:
                board.send(f'BEEP {freq} 140', f'OK BEEP {freq} 140')
            next_frame += 0.14
            time.sleep(max(0, next_frame - time.monotonic()))
        time.sleep(0.5)
except KeyboardInterrupt:
    pass
finally:
    board.close()
