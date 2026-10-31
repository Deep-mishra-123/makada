"""Sarvam AI Text-to-Speech integration with local caching and async Windows playback."""
import base64
import hashlib
import json
import os
import subprocess
import sys
import winsound
from pathlib import Path
import requests

if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')


ROOT = Path(__file__).resolve().parents[1]
CACHE_DIR = ROOT / '.local' / 'voice_cache'
CONFIG_FILE = ROOT / '.local' / 'sarvam.json'


def get_api_key(override_key=None):
    if override_key:
        return override_key.strip()
    env_key = os.environ.get('SARVAM_API_KEY', '').strip()
    if env_key:
        return env_key
    if CONFIG_FILE.exists():
        try:
            data = json.loads(CONFIG_FILE.read_text(encoding='utf-8'))
            key = data.get('api_key', '').strip()
            if key:
                return key
        except Exception:
            pass
    return None


def save_api_key(key):
    CONFIG_FILE.parent.mkdir(exist_ok=True)
    CONFIG_FILE.write_text(json.dumps({'api_key': key.strip()}, indent=2) + '\n', encoding='utf-8')


class SarvamSpeaker:
    def __init__(self, api_key=None, lang='en-IN', speaker='ritu', pace=1.1, model='bulbul:v4-flash'):
        self.api_key = get_api_key(api_key)
        self.lang = lang
        self.model = model
        self.speaker = self._resolve_speaker(speaker, lang, model)
        self.pace = pace
        CACHE_DIR.mkdir(parents=True, exist_ok=True)

    def _resolve_speaker(self, speaker, lang, model):
        if model == 'bulbul:v4-flash':
            # Map friendly short names to bulbul:v4-flash personas
            base = speaker.lower().strip()
            if base in ('ritu', 'ritu_en', 'ritu_hi'):
                return 'ritu_hi_reels' if lang.startswith('hi') else 'ritu_en_reels'
            elif base in ('shubh', 'shubh_en', 'shubh_hi'):
                return 'shubh_hi_ads' if lang.startswith('hi') else 'shubh_en_ads'
            elif base in ('simran', 'simran_en', 'simran_hi'):
                return 'simran_hi_social_energetic' if lang.startswith('hi') else 'simran_en_conversation'
        return speaker

    def cache_path_for(self, text):
        identifier = f"{text}_{self.lang}_{self.speaker}_{self.pace}_{self.model}"
        digest = hashlib.md5(identifier.encode('utf-8')).hexdigest()
        return CACHE_DIR / f"{digest}.wav"

    def prefetch(self, text_list):
        """Pre-generate and cache audio clips before motion starts."""
        for text in text_list:
            if not text:
                continue
            try:
                self.synthesize(text)
            except Exception as e:
                print(f"[Speaker Warning] Failed to prefetch '{text}': {e}")

    def synthesize(self, text):
        target_path = self.cache_path_for(text)
        if target_path.exists() and target_path.stat().st_size > 100:
            return target_path

        if not self.api_key:
            raise ValueError(
                "Sarvam API key not found. Set SARVAM_API_KEY env var or save it in .local/sarvam.json"
            )

        url = "https://api.sarvam.ai/text-to-speech"
        payload = {
            "text": text,
            "model": self.model,
            "language_code": self.lang,
            "speaker": self.speaker,
            "pace": self.pace,
            "speech_sample_rate": 24000,
            "output_audio_codec": "wav"
        }
        headers = {
            "api-subscription-key": self.api_key,
            "Content-Type": "application/json"
        }

        resp = requests.post(url, json=payload, headers=headers, timeout=12)
        if resp.status_code != 200:
            raise RuntimeError(f"Sarvam API error ({resp.status_code}): {resp.text}")

        res_data = resp.json()
        if "audios" not in res_data or not res_data["audios"]:
            raise RuntimeError(f"Unexpected response from Sarvam API: {res_data}")

        audio_bytes = base64.b64decode(res_data["audios"][0])
        target_path.write_bytes(audio_bytes)
        return target_path

    def speak(self, text, block=False):
        """Speak the text asynchronously using winsound, or fallback to Windows SAPI."""
        print(f"🕷️ Spidey: \"{text}\"")
        try:
            wav_file = self.synthesize(text)
            flags = winsound.SND_FILENAME
            if not block:
                flags |= winsound.SND_ASYNC
            winsound.PlaySound(str(wav_file), flags)
        except Exception as e:
            print(f"[Speaker Error] {e} -> Falling back to Windows SAPI TTS")
            # PowerShell SAPI fallback
            escaped = text.replace('"', '`"')
            cmd = f'Add-Type -AssemblyName System.Speech; (New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak("{escaped}")'
            subprocess.Popen(["powershell", "-NoProfile", "-Command", cmd])


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description="Test Sarvam Voice Output")
    parser.add_argument('text', nargs='?', default="Hello human, I am Spidey the walking hexapod!")
    parser.add_argument('--key', help="Sarvam API key")
    parser.add_argument('--speaker', default='ritu')
    parser.add_argument('--model', default='bulbul:v4-flash')
    parser.add_argument('--lang', default='en-IN')
    args = parser.parse_args()

    spk = SarvamSpeaker(api_key=args.key, lang=args.lang, speaker=args.speaker, model=args.model)
    spk.speak(args.text, block=True)

