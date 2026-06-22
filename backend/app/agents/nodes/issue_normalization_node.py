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
        "account accessed without permission", "privilege escalation",
    ),
    "notification": (
        "password reset email not received", "verification code missing",
        "verification code is missing", "otp not received", "otp is not received",
        "otp never arrived", "email not received", "email is not received",
        "email never arrived", "notification delayed", "notifications delayed",
        "delayed notification", "delayed notifications", "alert not sent",
    ),
    "integration": (
        "third-party integration broken", "third party integration broken",
        "external service sync issue", "webhook not delivered", "webhook failure",
        "webhook failed", "webhook is failing", "api sync failed", "api sync issue",
        "crm sync failed", "crm sync issue", "stripe sync failed", "payment sync failure",
        "webhook sync", "api sync", "crm sync", "sync is failing", "sync failed", "sync failure",
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
        "request timed out", "page timed out", "dashboard freezes", "export hangs",
        "export stuck", "slow response", "high latency", "slow page", "page is slow",
        "timeout", "times out", "timed out", "freezing", "freezes", "exporting hangs", "hangs",
    ),
    "ui": (
        "button broken", "broken button", "modal issue", "modal not opening",
        "layout overlap", "layout overlaps", "dropdown issue", "dropdown broken",
    ),
    "data": (
        "missing records", "incorrect reports", "incorrect report", "wrong report",
        "stale dashboard data", "stale data",
    ),
}

NEGATIVE_SIGNALS = (
    "failed", "failing", "failure", "cannot", "can't", "unable", "not active",
    "not yet active", "inactive", "disabled", "unpaid", "duplicate", "charged twice", "pending", "expired",
    "locked", "invalid", "timeout", "times out", "timed out", "slow", "latency", "freez", "hang", "stuck", "broken",
    "overlap", "missing", "incorrect", "wrong", "stale", "not received", "delayed",
    "unauthorized", "suspicious", "denied", "exposure", "not opening",
    "billing issue", "modal issue", "dropdown issue", "api sync issue",
    "crm sync issue", "permission issue", "not delivered", "not sent",
    "without permission", "privilege escalation",
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


def normalize_priority(category: str, input_text: str, current_priority: Any) -> str:
    """Apply deterministic business priority policy to a generated priority."""
    category = _text(category).lower()
    text = _text(input_text).lower()
    current = _text(current_priority).lower()
    if current not in SUPPORTED_SEVERITIES:
        current = "medium"

    high_signals = {
        "billing": (
            "refund", "duplicate charge", "charged twice", "subscription inactive",
            "subscription not active", "subscription is not yet active", "payment failed",
        ),
        "auth": (
            "login failure", "login failed", "cannot login", "can't login",
            "session expiration", "session expired", "password reset failure",
            "password reset failed", "password reset fails",
        ),
        "performance": (
            "timeout", "times out", "timed out", "export hangs", "export stuck",
            "dashboard freeze", "dashboard freezes",
        ),
        "security": (
            "unauthorized", "data exposure", "exposed data", "permission issue",
            "without permission", "privilege escalation",
        ),
    }
    normalized = current
    if any(signal in text for signal in high_signals.get(category, ())):
        normalized = "high"
    elif category == "integration":
        normalized = "high" if "payment sync failure" in text else "medium"
    elif category == "notification" and any(
        signal in text
        for signal in (
            "otp not received", "otp is not received", "verification code missing",
            "verification code is missing", "email not received", "email is not received",
        )
    ):
        normalized = "medium"

    if normalized != current:
        print(f"[priority_policy] normalized priority from {current} to {normalized}")
    return normalized


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
    current_category = _text(raw.get("category")).lower() or "unknown"
    if current_category != category:
        print(
            f"[issue_normalizer] normalized category from {current_category} to {category}"
        )

    description = _text(raw.get("description")) or _text(raw.get("title")) or input_text
    title = _text(raw.get("title")) or _title_for(description, category)
    customer = _text(raw.get("customer")) or None
    return {
        "title": title,
        "category": category,
        "severity": normalize_priority(category, combined, raw.get("severity")),
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
