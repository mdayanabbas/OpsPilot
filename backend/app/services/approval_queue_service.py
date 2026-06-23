"""Read models requiring human approval as one management queue."""

from __future__ import annotations

from datetime import datetime, time

from app.models.approval import ApprovalDecision
from app.models.reply import CustomerReply
from app.models.ticket import Ticket


FINAL_DECISIONS = {"approved", "rejected"}


def _item_key(record: ApprovalDecision) -> tuple[int, str, int]:
    return record.workflow_run_id, record.item_type, record.item_id


def _latest_records(db) -> dict[tuple[int, str, int], ApprovalDecision]:
    records = db.query(ApprovalDecision).order_by(ApprovalDecision.id.asc()).all()
    return {_item_key(record): record for record in records}


def _ensure_pending_records(db) -> None:
    """Give every approval-required item a stable queue/comment identifier."""
    latest = _latest_records(db)
    created = False

    sources = (
        ("ticket", Ticket, Ticket.requires_approval),
        ("reply", CustomerReply, CustomerReply.requires_approval),
    )
    for item_type, model, approval_column in sources:
        items = db.query(model).filter(approval_column.is_(True)).all()
        for item in items:
            key = (item.workflow_run_id, item_type, item.id)
            if key in latest:
                continue
            record = ApprovalDecision(
                workflow_run_id=item.workflow_run_id,
                item_type=item_type,
                item_id=item.id,
                decision=(
                    item.status if item.status in FINAL_DECISIONS else "pending"
                ),
            )
            db.add(record)
            latest[key] = record
            created = True

    if created:
        db.commit()


def _item_lookup(db, record: ApprovalDecision):
    if record.item_type == "ticket":
        return db.query(Ticket).filter(Ticket.id == record.item_id).first()
    if record.item_type == "reply":
        return db.query(CustomerReply).filter(CustomerReply.id == record.item_id).first()
    return None


def _risk(record: ApprovalDecision, item) -> str:
    if record.item_type == "reply" and item:
        risk = (item.risk_level or "medium").lower()
        return risk if risk in {"low", "medium", "high"} else "medium"
    if record.item_type == "ticket" and item:
        priority = (item.priority or "medium").lower()
        return priority if priority in {"low", "medium", "high"} else "medium"
    return "high" if record.item_type == "incident_action" else "medium"


def _serialize(db, record: ApprovalDecision) -> dict:
    item = _item_lookup(db, record)
    comments = sorted(record.comments, key=lambda value: (value.created_at, value.id))
    title = f"{record.item_type.replace('_', ' ').title()} #{record.item_id}"
    summary = None
    if record.item_type == "ticket" and item:
        title = item.title
        summary = item.description
    elif record.item_type == "reply" and item:
        title = item.issue
        summary = item.draft_reply

    reviewed_at = comments[-1].created_at if comments else None
    return {
        "id": record.id,
        "approval_id": record.id,
        "workflow_run_id": record.workflow_run_id,
        "item_type": record.item_type,
        "item_id": record.item_id,
        "status": record.decision,
        "decision": record.decision,
        "risk": _risk(record, item),
        "title": title,
        "summary": summary,
        "reviewer_note": record.reviewer_note,
        "created_at": record.created_at,
        "reviewed_at": reviewed_at,
        "decided_at": record.created_at if record.decision in FINAL_DECISIONS else None,
        "comments": [
            {
                "id": comment.id,
                "approval_id": comment.approval_id,
                "reviewer": comment.reviewer,
                "comment": comment.comment,
                "created_at": comment.created_at,
            }
            for comment in comments
        ],
    }


def get_pending_approvals(db) -> list[dict]:
    _ensure_pending_records(db)
    latest = _latest_records(db)
    pending = [record for record in latest.values() if record.decision == "pending"]
    pending.sort(key=lambda value: (value.created_at, value.id), reverse=True)
    return [_serialize(db, record) for record in pending]


def get_recent_decisions(db, limit: int = 100) -> list[dict]:
    _ensure_pending_records(db)
    latest = _latest_records(db)
    decisions = [
        record for record in latest.values() if record.decision in FINAL_DECISIONS
    ]
    decisions.sort(key=lambda value: (value.created_at, value.id), reverse=True)
    return [_serialize(db, record) for record in decisions[:limit]]


def get_approval_stats(db) -> dict:
    _ensure_pending_records(db)
    latest = list(_latest_records(db).values())
    today_start = datetime.combine(datetime.utcnow().date(), time.min)
    return {
        "pending_count": sum(record.decision == "pending" for record in latest),
        "approved_today": sum(
            record.decision == "approved" and record.created_at >= today_start
            for record in latest
        ),
        "rejected_today": sum(
            record.decision == "rejected" and record.created_at >= today_start
            for record in latest
        ),
    }


def get_approval_queue(db) -> dict[str, list[dict]]:
    pending = get_pending_approvals(db)
    recent = get_recent_decisions(db)
    return {
        "pending": pending,
        "approved": [item for item in recent if item["status"] == "approved"],
        "rejected": [item for item in recent if item["status"] == "rejected"],
    }
