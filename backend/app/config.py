import os
from pathlib import Path

from dotenv import load_dotenv


BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_DIR.parent

load_dotenv(PROJECT_ROOT / ".env")
load_dotenv(BACKEND_DIR / ".env", override=True)


def _get_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)

    if value is None:
        return default

    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _get_int(name: str, default: int) -> int:
    value = os.getenv(name)

    if value is None:
        return default

    try:
        return int(value)
    except ValueError:
        return default


GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "local").strip().lower()

LOCAL_LLM_ENABLED = _get_bool("LOCAL_LLM_ENABLED", False)
LOCAL_LLM_BASE_URL = os.getenv("LOCAL_LLM_BASE_URL", "http://localhost:1234/v1")
LOCAL_LLM_API_KEY = os.getenv("LOCAL_LLM_API_KEY", "lm-studio")
LOCAL_LLM_MODEL = os.getenv("LOCAL_LLM_MODEL", "llama-2-7b-chat")

EMAIL_INGESTION_ENABLED = _get_bool("EMAIL_INGESTION_ENABLED", False)
EMAIL_IMAP_HOST = os.getenv("EMAIL_IMAP_HOST", "imap.gmail.com")
EMAIL_IMAP_PORT = _get_int("EMAIL_IMAP_PORT", 993)
EMAIL_USERNAME = os.getenv("EMAIL_USERNAME")
EMAIL_APP_PASSWORD = os.getenv("EMAIL_APP_PASSWORD")
EMAIL_MARK_AS_READ = _get_bool("EMAIL_MARK_AS_READ", False)

ALERT_EMAIL_ENABLED = _get_bool("ALERT_EMAIL_ENABLED", False)
ALERT_EMAIL_FROM = os.getenv("ALERT_EMAIL_FROM") or EMAIL_USERNAME
ALERT_EMAIL_TO = os.getenv("ALERT_EMAIL_TO")
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = _get_int("SMTP_PORT", 587)
