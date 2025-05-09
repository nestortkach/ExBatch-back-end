import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
STORAGE_DIR = BASE_DIR / "storage"
DB_FILE = BASE_DIR / "batcher.db"

STORAGE_DIR.mkdir(parents=True, exist_ok=True)
