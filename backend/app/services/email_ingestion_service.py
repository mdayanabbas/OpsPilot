import email
import imaplib
import re
from contextlib import contextmanager
from email.header import decode_header
from email.message import Message
from email.utils import parsedate_to_datetime, parseaddr
from typing import Iterator

from sqlalchemy.orm import Session

from app.config import (
    EMAIL_APP_PASSWORD,
    EMAIL_IMAP_HOST,
    EMAIL_IMAP_PORT,
    EMAIL_INGESTION_ENABLED,
    EMAIL_MARK_AS_READ,
    EMAIL_USERNAME,
)
from app.models.processed_email import ProcessedEmail
from app.schemas.workflow_schema import WorkflowRunCreate

NOISY_SENDER_PATTERNS = (
    "no-reply",
    "noreply",
    "notifications",
    "accounts.google.com",
)
NOISY_SUBJECT_PATTERNS = (
    "security alert",
    "2-step verification",
    "passkey",
    "authenticator",
    "app password",
)


class EmailIngestionError(RuntimeError):
    pass


class EmailIngestionDisabled(EmailIngestionError):
    pass


class EmailIngestionConfigError(EmailIngestionError):
    pass


class EmailImapLoginError(EmailIngestionError):
    pass


def _ensure_enabled():
    if not EMAIL_INGESTION_ENABLED:
        raise EmailIngestionDisabled("Email ingestion is disabled.")

    if not EMAIL_USERNAME or not EMAIL_APP_PASSWORD:
        raise EmailIngestionConfigError("Email username or app password is not configured.")


@contextmanager
def _imap_connection() -> Iterator[imaplib.IMAP4_SSL]:
    _ensure_enabled()

    try:
        client = imaplib.IMAP4_SSL(EMAIL_IMAP_HOST, EMAIL_IMAP_PORT)
    except OSError as exc:
        raise EmailIngestionError(f"Unable to connect to IMAP server: {exc}") from exc

    try:
        try:
            client.login(EMAIL_USERNAME, EMAIL_APP_PASSWORD)
        except imaplib.IMAP4.error as exc:
            raise EmailImapLoginError("IMAP login failed. Check Gmail app password and mailbox access.") from exc

        status, _ = client.select("INBOX")
        if status != "OK":
            raise EmailIngestionError("Unable to select INBOX.")

        yield client
    finally:
        try:
            client.close()
        except imaplib.IMAP4.error:
            pass
        client.logout()


def _decode_header_value(value: str | None) -> str:
    if not value:
        return ""

    parts = []
    for payload, encoding in decode_header(value):
        if isinstance(payload, bytes):
            parts.append(payload.decode(encoding or "utf-8", errors="replace"))
        else:
            parts.append(payload)

    return "".join(parts).strip()


def _message_date(message: Message) -> str | None:
    raw_date = message.get("Date")
    if not raw_date:
        return None

    try:
        return parsedate_to_datetime(raw_date).isoformat()
    except (TypeError, ValueError, IndexError, OverflowError):
        return None


def _decode_part_payload(part: Message) -> str:
    payload = part.get_payload(decode=True)
    if payload is None:
        raw_payload = part.get_payload()
        return raw_payload if isinstance(raw_payload, str) else ""

    charset = part.get_content_charset() or "utf-8"
    return payload.decode(charset, errors="replace")


def _plain_text_body(message: Message) -> str:
    if message.is_multipart():
        fallback_text = ""
        for part in message.walk():
            content_disposition = (part.get("Content-Disposition") or "").lower()
            content_type = part.get_content_type()

            if "attachment" in content_disposition:
                continue

            if content_type == "text/plain":
                return _decode_part_payload(part).strip()

            if content_type == "text/html" and not fallback_text:
                fallback_text = _decode_part_payload(part)

        return _html_to_text(fallback_text).strip()

    if message.get_content_type() in {"text/plain", "text/html"}:
        payload = _decode_part_payload(message)
        if message.get_content_type() == "text/html":
            return _html_to_text(payload).strip()
        return payload.strip()

    return ""


def _html_to_text(value: str) -> str:
    without_scripts = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", value)
    without_tags = re.sub(r"(?s)<[^>]+>", " ", without_scripts)
    return re.sub(r"\s+", " ", without_tags)


def _email_dict(uid: bytes, raw_message: bytes) -> dict:
    message = email.message_from_bytes(raw_message)
    _, from_email = parseaddr(_decode_header_value(message.get("From")))
    subject = _decode_header_value(message.get("Subject")) or "(no subject)"
    message_id = _decode_header_value(message.get("Message-ID")) or uid.decode("utf-8", errors="replace")

    return {
        "_uid": uid.decode("utf-8", errors="replace"),
        "message_id": message_id,
        "from_email": from_email or "unknown",
        "subject": subject,
        "body": _plain_text_body(message),
        "received_at": _message_date(message),
    }


def _skip_reason(email_item: dict) -> str | None:
    sender = str(email_item.get("from_email", "")).lower()
    subject = str(email_item.get("subject", "")).lower()

    for pattern in NOISY_SENDER_PATTERNS:
        if pattern in sender:
            return f"Skipped system sender: {pattern}"

    for pattern in NOISY_SUBJECT_PATTERNS:
        if pattern in subject:
            return f"Skipped system subject: {pattern}"

    return None


def is_support_candidate(email_dict: dict) -> bool:
    return _skip_reason(email_dict) is None


def _preview_email(email_item: dict) -> dict:
    skip_reason = _skip_reason(email_item)
    return {
        "message_id": email_item["message_id"],
        "from_email": email_item["from_email"],
        "subject": email_item["subject"],
        "body": email_item["body"],
        "received_at": email_item["received_at"],
        "is_support_candidate": skip_reason is None,
        "skip_reason": skip_reason,
    }


def _fetch_unread_email_records(limit: int = 10) -> list[dict]:
    safe_limit = max(1, min(limit, 50))

    with _imap_connection() as client:
        status, data = client.uid("search", None, "UNSEEN")
        if status != "OK" or not data or not data[0]:
            return []

        uids = data[0].split()[:safe_limit]
        emails = []
        for uid in uids:
            try:
                fetch_status, message_data = client.uid("fetch", uid, "(RFC822)")
                if fetch_status != "OK":
                    continue

                raw_message = next(
                    (
                        item[1]
                        for item in message_data
                        if isinstance(item, tuple) and isinstance(item[1], bytes)
                    ),
                    None,
                )
                if not raw_message:
                    continue

                emails.append(_email_dict(uid, raw_message))
            except Exception:
                continue

        return emails


def fetch_unread_emails(limit: int = 10) -> list[dict]:
    return [_preview_email(item) for item in _fetch_unread_email_records(limit=limit)]


def _mark_email_as_read(uid: str):
    with _imap_connection() as client:
        client.uid("store", uid, "+FLAGS", "\\Seen")


def _email_input_text(email_item: dict) -> str:
    return (
        f"Email from: {email_item['from_email']}\n"
        f"Subject: {email_item['subject']}\n\n"
        f"{email_item['body']}"
    ).strip()


def _already_processed(db: Session, message_id: str) -> bool:
    return (
        db.query(ProcessedEmail)
        .filter(ProcessedEmail.message_id == message_id)
        .first()
        is not None
    )


def _save_processed_email(db: Session, email_item: dict, workflow_run_id: int):
    processed_email = ProcessedEmail(
        message_id=email_item["message_id"],
        from_email=email_item["from_email"],
        subject=email_item["subject"],
        workflow_run_id=workflow_run_id,
    )
    db.add(processed_email)
    db.commit()


def ingest_unread_emails(db: Session, limit: int = 10) -> dict:
    from app.api.v1.workflow_routes import _execute_workflow_run_sync

    emails = _fetch_unread_email_records(limit=limit)
    processed = []
    skipped = []
    workflow_run_ids = []

    for email_item in emails:
        if _already_processed(db, email_item["message_id"]):
            skipped.append(
                {
                    "from_email": email_item["from_email"],
                    "subject": email_item["subject"],
                    "skip_reason": "Skipped duplicate: message already processed",
                }
            )
            continue

        skip_reason = _skip_reason(email_item)
        if skip_reason:
            skipped.append(
                {
                    "from_email": email_item["from_email"],
                    "subject": email_item["subject"],
                    "skip_reason": skip_reason,
                }
            )
            continue

        input_text = _email_input_text(email_item)
        if len(input_text) < 10:
            skipped.append(
                {
                    "from_email": email_item["from_email"],
                    "subject": email_item["subject"],
                    "skip_reason": "Skipped malformed email: body too short",
                }
            )
            continue

        try:
            workflow_run = _execute_workflow_run_sync(
                payload=WorkflowRunCreate(input_text=input_text),
                db=db,
            )
        except Exception as exc:
            skipped.append(
                {
                    "from_email": email_item["from_email"],
                    "subject": email_item["subject"],
                    "skip_reason": f"Workflow creation failed: {type(exc).__name__}",
                }
            )
            continue

        workflow_run_ids.append(workflow_run.id)
        _save_processed_email(db, email_item, workflow_run.id)
        processed.append(
            {
                "from_email": email_item["from_email"],
                "subject": email_item["subject"],
                "workflow_run_id": workflow_run.id,
            }
        )

        if EMAIL_MARK_AS_READ:
            try:
                _mark_email_as_read(email_item["_uid"])
            except EmailIngestionError:
                pass

    return {
        "processed": len(processed),
        "skipped_count": len(skipped),
        "workflow_run_ids": workflow_run_ids,
        "emails": processed,
        "skipped_emails": skipped,
    }
