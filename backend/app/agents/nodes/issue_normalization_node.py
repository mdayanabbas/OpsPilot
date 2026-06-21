"""Deterministic normalization between issue extraction and planning."""

from __future__ import annotations

import re
from typing import Any


SUPPORTED_CATEGORIES = (
    "billing",
    "auth",
    "performance",
    "ui",
    "data",
    "integration",
    "notification",
    "security",
    "other",
)
SUPPORTED_SEVERITIES = {"low", "medium", "high"}

# Ordered rules make ties deterministic. More specific phrases come before broad ones.
CATEGORY_RULES: dict[str, tuple[str, ...]] = {
    "security": (
        "unauthorized access", "suspicious login", "permission issue",
        "permission denied", "data exposure", "exposed data",
    ),
    "billing": (
        "payment succeeded but", "payment successful but", "subscription inactive",
        "subscription not active", "subscription is not yet active", "invoice unpaid",
        "unpaid invoice", "duplicate charge", "charged twice", "refund pending",
        "payment failed", "billing issue",
    ),
    "auth": (
        "cannot login", "can't login", "unable to login", "login failed",
        "invalid credentials", "password reset", "session expired", "account locked",
        "locked out", "reset link expired",
    ),
    "performance": (
        "high latency", "slow page", "page is slow", "timeout", "times out",
        "freezing", "freezes", "export hangs", "exporting hangs", "hangs",
    ),
    "ui": (
        "button broken", "broken button", "modal issue", "modal not opening",
        "layout overlap", "layout overlaps", "dropdown issue", "dropdown broken",
    ),
    "data": (
        "missing records", "incorrect reports", "incorrect report", "wrong report",
        "stale dashboard data", "stale data",
    ),
    "integration": (
        "webhook failure", "webhook failed", "webhook is failing", "webhook sync",
        "api sync issue", "api sync", "crm sync issue", "crm sync", "sync is failing",
        "sync failed", "sync failure",
    ),
    "notification": (
        "email not received", "email never arrived", "otp not received",
        "otp never arrived", "delayed notification", "delayed notifications",
        "notification delayed", "notifications delayed",
    ),
}

NEGATIVE_SIGNALS = (
    "failed", "failing", "failure", "cannot", "can't", "unable", "not active",
    "not yet active", "inactive", "disabled", "unpaid", "duplicate", "charged twice", "pending", "expired",
    "locked", "invalid", "timeout", "slow", "latency", "freez", "hang", "broken",
    "overlap", "missing", "incorrect", "wrong", "stale", "not received", "delayed",
    "unauthorized", "suspicious", "denied", "exposure", "not opening",
    "billing issue", "modal issue", "dropdown issue", "api sync issue",
    "crm sync issue", "permission issue",
)

NO_CUSTOMER_IMPACT_SIGNALS = (
    "no customer impact", "no customers affected", "no users affected",
    "customers are unaffected", "users are unaffected", "internal test only",
)

PRAISE_OR_SUCCESS_PATTERNS = (
    r"\beverything works (?:perfectly|great|fine)\b",
    r"\bjust (?:saying )?thanks\b",
    r"\bthank you\b",
    r"\bgreat (?:product|app|service)\b",
    r"\blove (?:the )?(?:product|app|service)\b",
    r"\b(?:purchased|payment|purchase) (?:was )?(?:successfully|successful|succeeded|completed)\b",
)


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _issue_text(input_text: str, issue: dict[str, Any] | None = None) -> str:
    if not issue:
        return input_text.lower()
    values = [input_text, issue.get("title"), issue.get("description")]
    return " ".join(_text(value) for value in values if _text(value)).lower()


def _category_for(text: str, fallback: Any = None) -> str | None:
    fallback = _text(fallback).lower()
    scores = {
        category: sum(1 for phrase in phrases if phrase in text)
        for category, phrases in CATEGORY_RULES.items()
    }
    best = max(scores, key=scores.get)
    if scores[best]:
        return best
    if fallback in SUPPORTED_CATEGORIES:
        return fallback
    return None


def _has_problem(text: str) -> bool:
    return any(signal in text for signal in NEGATIVE_SIGNALS)


def _praise_or_success_only(text: str) -> bool:
    return any(re.search(pattern, text) for pattern in PRAISE_OR_SUCCESS_PATTERNS) and not _has_problem(text)


def _has_no_customer_impact(text: str) -> bool:
    return any(signal in text for signal in NO_CUSTOMER_IMPACT_SIGNALS)


def _severity_for(text: str, fallback: Any = None) -> str:
    fallback = _text(fallback).lower()
    if fallback in SUPPORTED_SEVERITIES:
        return fallback
    payment_without_subscription = (
        any(term in text for term in ("payment succeeded", "payment successful", "payment successfully"))
        and any(term in text for term in ("subscription inactive", "subscription not active", "subscription is not yet active", "subscription remains disabled"))
    )
    if payment_without_subscription or any(term in text for term in (
        "unauthorized access", "data exposure", "suspicious login", "cannot login",
        "can't login", "account locked", "duplicate charge", "charged twice",
        "payment succeeded but", "payment successful but",
    )):
        return "high"
    return "medium"


def _title_for(source: str, category: str) -> str:
    compact = " ".join(source.split()).rstrip(" .")
    if not compact:
        return f"{category.title()} issue"
    compact = compact[:100].rstrip()
    return compact[0].upper() + compact[1:]


def _normalize_one(input_text: str, raw_issue: Any = None) -> dict[str, Any] | None:
    raw = raw_issue if isinstance(raw_issue, dict) else {}
    combined = _issue_text(input_text, raw)
    if (
        not combined
        or _praise_or_success_only(combined)
        or _has_no_customer_impact(combined)
        or not _has_problem(combined)
    ):
        return None
    category = _category_for(combined, raw.get("category"))
    if category is None:
        return None

    description = _text(raw.get("description")) or _text(raw.get("title")) or input_text
    title = _text(raw.get("title")) or _title_for(description, category)
    customer = _text(raw.get("customer")) or None
    return {
        "title": title,
        "category": category,
        "severity": _severity_for(combined, raw.get("severity")),
        "customer": customer,
        "description": description,
    }


def normalize_issue_result(input_text: str, extracted_result: dict) -> dict:
    """Return a stable, planner-ready issue result using deterministic taxonomy rules."""
    input_text = _text(input_text)
    extracted = extracted_result if isinstance(extracted_result, dict) else {}
    raw_issues = extracted.get("issues")
    raw_issues = raw_issues if isinstance(raw_issues, list) else []

    issues: list[dict[str, Any]] = []
    changed = False
    for raw_issue in raw_issues:
        issue = _normalize_one(input_text, raw_issue)
        if issue is not None:
            issues.append(issue)
            changed = changed or issue != raw_issue
        else:
            changed = True

    synthesized = False
    if not issues:
        issue = _normalize_one(input_text)
        if issue is not None:
            issues.append(issue)
            synthesized = True

    extracted_clarification = extracted.get("requires_clarification") is True
    requires_clarification = not issues
    clarification_overridden = extracted_clarification and bool(issues)

    reasons: list[str] = []
    if synthesized:
        reasons.append("created issue from actionable input")
    elif changed:
        reasons.append("normalized extracted issue taxonomy")
    if clarification_overridden:
        reasons.append("overrode clarification because an actionable issue was found")
        print("[issue_normalizer] clarification_overridden=true")
    if requires_clarification:
        if _praise_or_success_only(input_text.lower()):
            reasons.append("input contains praise or success only")
        elif _has_no_customer_impact(input_text.lower()):
            reasons.append("no customer impact exists")
        elif _category_for(input_text.lower()) is None:
            reasons.append("category cannot be inferred")
        else:
            reasons.append("no concrete customer issue exists")

    clarification_changed = extracted.get("requires_clarification") is not requires_clarification
    normalization_applied = synthesized or changed or clarification_changed
    reason = "; ".join(dict.fromkeys(reasons)) or "no normalization needed"
    confidence = 0.9 if issues else (0.2 if _praise_or_success_only(input_text.lower()) else 0.35)

    for issue in issues:
        print(f"[issue_normalizer] category={issue['category']}")
    print(f"[issue_normalizer] normalization_applied={str(normalization_applied).lower()}")

    return {
        "issues": issues,
        "requires_clarification": requires_clarification,
        "normalization_applied": normalization_applied,
        "normalization_reason": reason,
        "confidence": confidence,
    }
