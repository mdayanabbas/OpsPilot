from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.demo_guard import require_demo_api_key
from app.services.email_ingestion_service import (
    EmailImapLoginError,
    EmailIngestionConfigError,
    EmailIngestionDisabled,
    EmailIngestionError,
    fetch_unread_emails,
    ingest_unread_emails,
)
from app.services.email_worker import get_email_worker_status

router = APIRouter()


class EmailIngestionRequest(BaseModel):
    limit: int = Field(10, ge=1, le=50)


def _raise_email_error(exc: EmailIngestionError):
    if isinstance(exc, EmailIngestionDisabled):
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if isinstance(exc, EmailIngestionConfigError):
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if isinstance(exc, EmailImapLoginError):
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/preview")
def preview_unread_emails(limit: int = 10):
    try:
        return fetch_unread_emails(limit=limit)
    except EmailIngestionError as exc:
        _raise_email_error(exc)


@router.post("/run", dependencies=[Depends(require_demo_api_key)])
def run_email_ingestion(
    payload: EmailIngestionRequest,
    db: Session = Depends(get_db),
):
    try:
        return ingest_unread_emails(db=db, limit=payload.limit)
    except EmailIngestionError as exc:
        _raise_email_error(exc)


@router.get("/status")
def get_email_ingestion_status(db: Session = Depends(get_db)):
    return get_email_worker_status(db)
