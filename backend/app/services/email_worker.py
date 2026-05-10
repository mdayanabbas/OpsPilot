import asyncio
from datetime import datetime

from sqlalchemy.orm import Session

from app.config import EMAIL_INGESTION_ENABLED
from app.database import SessionLocal
from app.models.processed_email import ProcessedEmail
from app.services.email_ingestion_service import EmailIngestionError, ingest_unread_emails

POLL_INTERVAL_SECONDS = 30

_worker_task: asyncio.Task | None = None
_last_check_at: datetime | None = None


def _run_ingestion_cycle():
    db = SessionLocal()
    try:
        result = ingest_unread_emails(db=db, limit=10)
        for email_item in result.get("emails", []):
            print(
                "[email_worker] processed email "
                f"subject={email_item.get('subject')} "
                f"workflow_run_id={email_item.get('workflow_run_id')}"
            )

        for skipped_item in result.get("skipped_emails", []):
            if "duplicate" in (skipped_item.get("skip_reason") or "").lower():
                print(
                    "[email_worker] skipped duplicate "
                    f"subject={skipped_item.get('subject')}"
                )
    finally:
        db.close()


async def _email_worker_loop():
    global _last_check_at

    while True:
        _last_check_at = datetime.utcnow()
        print("[email_worker] checking inbox")

        if EMAIL_INGESTION_ENABLED:
            try:
                await asyncio.to_thread(_run_ingestion_cycle)
            except EmailIngestionError as exc:
                print(f"[email_worker] ingestion error: {type(exc).__name__}: {exc}")
            except Exception as exc:
                print(f"[email_worker] unexpected error: {type(exc).__name__}: {exc}")

        await asyncio.sleep(POLL_INTERVAL_SECONDS)


def start_email_worker():
    global _worker_task

    if _worker_task and not _worker_task.done():
        return

    _worker_task = asyncio.create_task(_email_worker_loop())


def get_email_worker_status(db: Session) -> dict:
    return {
        "worker_running": bool(_worker_task and not _worker_task.done()),
        "poll_interval_seconds": POLL_INTERVAL_SECONDS,
        "processed_email_count": db.query(ProcessedEmail).count(),
        "last_check_at": _last_check_at,
    }
