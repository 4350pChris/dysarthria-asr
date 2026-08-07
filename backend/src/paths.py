from __future__ import annotations

from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
ROOT = BACKEND_DIR.parents[0]
STATIC_DIR = BACKEND_DIR / "static"
DATA_DIR = ROOT / "data"
AUDIO_DIR = DATA_DIR / "audio"
TATOEBA_PROMPTS_FILE = DATA_DIR / "tatoeba" / "deu-cc0-prompts.json"
PHRASES_FILE = DATA_DIR / "phrases.csv"
SEED_PHRASES_FILE = ROOT / "seed" / "phrases.csv"
DB_FILE = DATA_DIR / "app.sqlite"
