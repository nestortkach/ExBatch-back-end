import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

STORAGE_DIR = BASE_DIR / "storage"
JSON_STORAGE_DIR = STORAGE_DIR / "json_results"
CSV_STORAGE_DIR = STORAGE_DIR / "csv_results"
TEMPLATES_STORAGE_DIR = STORAGE_DIR / "templates"

ENV_PATH = BASE_DIR / '.env'

STORAGE_DIR.mkdir(parents=True, exist_ok=True)
JSON_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
CSV_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
TEMPLATES_STORAGE_DIR.mkdir(parents=True, exist_ok=True)

load_dotenv(dotenv_path=ENV_PATH)

DATABASES = {
        'NAME': os.environ.get('POSTGRES_DB'),
        'USER': os.environ.get('POSTGRES_USER'),
        'PASSWORD': os.environ.get('POSTGRES_PASSWORD'),
        'HOST': os.environ.get('POSTGRES_HOST'),
        'PORT': os.environ.get('POSTGRES_PORT'),
}
