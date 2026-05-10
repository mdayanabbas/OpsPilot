import re

from sqlalchemy.orm import Session

from app.models.memory import MemoryItem

GENERIC_STOPWORDS = {
    "issue",
    "page",
    "customer",
    "problem",
    "request",
    "dashboard",
    "reports",
}

PRIORITY_TERMS = {"low", "medium", "high"}
RISK_PATTERN = re.compile(r"\b(low|medium|high)\s+risk\b")
MIN_RELEVANCE_SCORE = 6


def _clean_text(value: object, default: str = "") -> str:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return default


def _keywords(value: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9]+", value.lower())
        if len(token) >= 3 and token not in GENERIC_STOPWORDS
    }


def _phrases(value: str) -> set[str]:
    tokens = [
        token
        for token in re.findall(r"[a-z0-9]+", value.lower())
        if token not in GENERIC_STOPWORDS
    ]
    phrases = set()

    for size in (2, 3):
        for index in range(0, len(tokens) - size + 1):
            phrases.add(" ".join(tokens[index : index + size]))

    return phrases


def _risk_level(value: str) -> str | None:
    match = RISK_PATTERN.search(value.lower())
    if match:
        return match.group(1)
    return None


def _priority(value: str) -> str | None:
    tokens = _keywords(value)
    for priority in ("high", "medium", "low"):
        if priority in tokens:
            return priority
    return None


def _memory_content(ticket: dict, reply: dict, evaluation: dict) -> str:
    parts = [
        f"Ticket: {_clean_text(ticket.get('description'))}",
        f"Ticket priority: {_clean_text(ticket.get('priority'), 'unknown')}",
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
    query_title = query.split("\n", 1)[0]
    query_title_keywords = _keywords(query_title)
    query_content_keywords = query_keywords
    query_phrases = _phrases(query)
    query_risk = _risk_level(query)
    query_priority = _priority(query)

    items = (
        db.query(MemoryItem)
        .order_by(MemoryItem.created_at.desc())
        .limit(100)
        .all()
    )

    scored_items = []
    for item in items:
        item_category = (item.category or "").lower()
        item_title_keywords = _keywords(item.title)
        item_content_keywords = _keywords(item.content)
        item_phrases = _phrases(f"{item.title}\n{item.content}")
        item_risk = _risk_level(item.content)
        item_priority = _priority(item.content)

        score = 0
        if normalized_category and item_category == normalized_category:
            score += 5

        score += len(query_title_keywords & item_title_keywords) * 3
        score += len(query_content_keywords & item_content_keywords) * 2

        if query_phrases & item_phrases:
            score += 4

        if query_risk and item_risk and query_risk == item_risk:
            score += 2

        if query_priority and item_priority and query_priority == item_priority:
            score += 1

        if score >= MIN_RELEVANCE_SCORE:
            item.relevance_score = score
            scored_items.append((score, item.created_at, item))

    scored_items.sort(key=lambda result: (result[0], result[1]), reverse=True)
    return [item for _, _, item in scored_items[: min(limit, 3)]]
