import re

from sqlalchemy.orm import Session

from app.models.memory import MemoryItem


def _clean_text(value: object, default: str = "") -> str:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return default


def _keywords(value: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9]+", value.lower())
        if len(token) >= 3
    }


def _memory_content(ticket: dict, reply: dict, evaluation: dict) -> str:
    parts = [
        f"Ticket: {_clean_text(ticket.get('description'))}",
        f"Reply issue: {_clean_text(reply.get('issue'))}",
        f"Reply risk: {_clean_text(reply.get('risk_level'), 'unknown')}",
        f"Evaluation risks: {_clean_text(evaluation.get('risks'), 'none recorded')}",
    ]
    return "\n".join(parts)


def save_memory_from_workflow(
    db: Session,
    workflow_run_id: int,
    ticket: dict,
    reply: dict,
    evaluation: dict,
) -> MemoryItem:
    existing = (
        db.query(MemoryItem)
        .filter(
            MemoryItem.workflow_run_id == workflow_run_id,
            MemoryItem.item_type == "workflow_summary",
        )
        .first()
    )

    title = _clean_text(ticket.get("title"), _clean_text(reply.get("issue"), "Workflow memory"))
    category = _clean_text(ticket.get("category"), None)
    content = _memory_content(ticket, reply, evaluation)

    if existing:
        existing.title = title
        existing.category = category
        existing.content = content
        return existing

    memory_item = MemoryItem(
        workflow_run_id=workflow_run_id,
        item_type="workflow_summary",
        title=title,
        category=category,
        content=content,
    )
    db.add(memory_item)
    return memory_item


def search_memory(
    db: Session,
    category: str,
    query: str,
    limit: int = 5,
) -> list[MemoryItem]:
    normalized_category = _clean_text(category).lower()
    query_keywords = _keywords(query)

    items = (
        db.query(MemoryItem)
        .order_by(MemoryItem.created_at.desc())
        .limit(100)
        .all()
    )

    scored_items = []
    for item in items:
        item_category = (item.category or "").lower()
        category_score = 3 if normalized_category and item_category == normalized_category else 0
        text_score = len(query_keywords & _keywords(f"{item.title} {item.content}"))
        score = category_score + text_score

        if score > 0:
            scored_items.append((score, item.created_at, item))

    scored_items.sort(key=lambda result: (result[0], result[1]), reverse=True)
    return [item for _, _, item in scored_items[:limit]]
