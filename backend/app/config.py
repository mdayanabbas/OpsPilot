import os
from pathlib import Path

from dotenv import load_dotenv


BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_DIR.parent

load_dotenv(PROJECT_ROOT / ".env")
load_dotenv(BACKEND_DIR / ".env", override=True)

DATABASE_URL = (
    os.getenv("DATABASE_URL", "sqlite:///./opspilot.db").strip()
    or "sqlite:///./opspilot.db"
)


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


DEMO_MODE = _get_bool("DEMO_MODE", False)
DEMO_API_KEY = os.getenv("DEMO_API_KEY", "").strip()
MAX_WORKFLOWS_PER_HOUR = max(1, _get_int("MAX_WORKFLOWS_PER_HOUR", 20))


GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_BASE_URL = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq").strip().lower()

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

_DEFAULT_CORS_ORIGINS = (
    "http://localhost:3000",
    "http://127.0.0.1:3000",
)
CORS_ORIGINS = tuple(
    origin.strip().rstrip("/")
    for origin in os.getenv(
        "CORS_ORIGINS",
        ",".join(_DEFAULT_CORS_ORIGINS),
    ).split(",")
    if origin.strip()
)
