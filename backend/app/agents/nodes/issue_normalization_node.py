import re


SUPPORTED_CATEGORIES = {
    "billing",
    "auth",
    "performance",
    "ui",
    "data",
    "integration",
    "notification",
    "security",
    "other",
}

SEVERITIES = {"low", "medium", "high"}

CATEGORY_INDICATORS = {
    "billing": (
        "payment succeeded",
        "payment successful",
        "payment made",
        "paid",
        "subscription inactive",
        "subscription not active",
        "subscription remains disabled",
        "subscription disabled",
        "invoice unpaid",
        "duplicate charge",
        "refund pending",
        "checkout payment failed",
        "payment failed",
        "payment pending",
        "invoice",
        "refund",
        "charged",
        "billing",
    ),
    "auth": (
        "cannot login",
        "can't login",
        "login failed",
        "login fails",
        "password reset not working",
        "password reset",
        "session expires immediately",
        "session expired",
        "invalid credentials",
        "account locked",
        "cannot access account",
        "can't access account",
        "locked out",
    ),
    "performance": (
        "slow page",
        "slow",
        "timeout",
        "times out",
        "freezing",
        "freeze",
        "long load time",
        "load time",
        "export hangs",
        "hangs",
        "crash",
        "dashboard freezes",
    ),
    "ui": (
        "button broken",
        "broken button",
        "dropdown overlap",
        "dropdown overlaps",
        "modal not opening",
        "modal won't open",
        "page layout issue",
        "layout issue",
        "button",
        "dropdown",
        "modal",
        "layout",
    ),
    "data": (
        "missing records",
        "wrong report numbers",
        "wrong numbers",
        "stale dashboard data",
        "stale data",
        "missing data",
        "incorrect report",
    ),
    "integration": (
        "webhook failure",
        "webhook failed",
        "webhook sync failed",
        "crm sync failure",
        "crm sync failed",
        "third-party api failure",
        "third party api failure",
        "api failure",
        "sync failed",
        "sync failure",
        "stripe",
    ),
    "notification": (
        "email not sent",
        "email wasn't sent",
        "otp not received",
        "otp never arrived",
        "notification delayed",
        "notification not sent",
        "notification",
    ),
    "security": (
        "suspicious login",
        "unauthorized access",
        "permission issue",
        "data exposure",
        "exposed data",
        "access without permission",
        "permission denied",
    ),
}

FAILURE_INDICATORS = (
    "not active",
    "inactive",
    "disabled",
    "failed",
    "failure",
    "not working",
    "cannot",
    "can't",
    "unable",
    "broken",
    "pending",
    "unpaid",
    "duplicate",
    "wrong",
    "missing",
    "stale",
    "slow",
    "timeout",
    "freezing",
    "freeze",
    "hangs",
    "crash",
    "overlap",
    "not opening",
    "not sent",
    "not received",
    "delayed",
    "unauthorized",
    "suspicious",
    "exposure",
    "locked",
    "invalid",
    "expired",
    "expires",
)

SUCCESS_ONLY_PATTERNS = (
    r"\beverything works great\b",
    r"\bworks great\b",
    r"\blove(?:s|d)? (?:the )?(?:product|app|service)\b",
    r"\bgreat product\b",
    r"\bthank(?:s| you)\b",
    r"\bhello\b",
    r"\bhi\b",
    r"\bpayment (?:succeeded|successful|completed)\b",
)


def _clean_text(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""


def _combined_text(input_text: str, issue: dict | None = None) -> str:
    parts = [_clean_text(input_text)]
    if isinstance(issue, dict):
        parts.extend(
            _clean_text(issue.get(key))
            for key in ("title", "description", "category", "severity", "customer")
        )

    return " ".join(part for part in parts if part).lower()


def _contains_any(text: str, indicators: tuple[str, ...]) -> bool:
    return any(indicator in text for indicator in indicators)


def _is_success_only(text: str) -> bool:
    lowered = text.lower().strip()
    if not lowered:
        return True

    matched_success = any(re.search(pattern, lowered) for pattern in SUCCESS_ONLY_PATTERNS)
    return matched_success and not _contains_any(lowered, FAILURE_INDICATORS)


def _has_concrete_failure(text: str) -> bool:
    return _contains_any(text.lower(), FAILURE_INDICATORS)


def _has_customer_impact(text: str) -> bool:
    lowered = text.lower()
    impact_terms = (
        "customer",
        "customers",
        "user",
        "users",
        "account",
        "subscription",
        "payment",
        "invoice",
        "dashboard",
        "report",
        "webhook",
        "email",
        "otp",
        "crm",
        "stripe",
        "billing",
    )
    return _contains_any(lowered, impact_terms)


def _classify_category(text: str, fallback: object = None) -> str:
    current = _clean_text(fallback).lower()
    if current in SUPPORTED_CATEGORIES and current != "other":
        return current

    lowered = text.lower()
    scores = {
        category: sum(1 for indicator in indicators if indicator in lowered)
        for category, indicators in CATEGORY_INDICATORS.items()
    }
    best_category = max(scores, key=scores.get)
    if scores[best_category] > 0:
        return best_category

    return "other"


def _severity_for(text: str, fallback: object = None) -> str:
    current = _clean_text(fallback).lower()
    if current in SEVERITIES:
        return current

    lowered = text.lower()
    if _contains_any(
        lowered,
        (
            "unauthorized",
            "data exposure",
            "suspicious login",
            "cannot login",
            "can't login",
            "duplicate charge",
            "payment succeeded",
            "payment successful",
            "subscription inactive",
            "subscription not active",
            "failed between",
        ),
    ):
        return "high"

    if _has_concrete_failure(lowered):
        return "medium"

    return "low"


def _title_for(text: str, category: str) -> str:
    cleaned = " ".join(text.strip().split())
    if not cleaned:
        return f"{category.title()} issue"

    title = cleaned[:90].rstrip(" .")
    return title[0].upper() + title[1:] if title else f"{category.title()} issue"


def _normalize_issue(input_text: str, raw_issue: dict | None = None) -> dict | None:
    text = _combined_text(input_text, raw_issue)
    if not text or _is_success_only(text):
        return None

    category = _classify_category(text, raw_issue.get("category") if isinstance(raw_issue, dict) else None)
    if category == "other" and not _has_concrete_failure(text):
        return None

    title = _clean_text(raw_issue.get("title")) if isinstance(raw_issue, dict) else ""
    description = _clean_text(raw_issue.get("description")) if isinstance(raw_issue, dict) else ""

    source_text = description or title or _clean_text(input_text)
    if not title:
        title = _title_for(source_text, category)
    if not description:
        description = source_text

    customer = _clean_text(raw_issue.get("customer")) if isinstance(raw_issue, dict) else ""

    return {
        "title": title,
        "category": category,
        "severity": _severity_for(text, raw_issue.get("severity") if isinstance(raw_issue, dict) else None),
        "customer": customer or None,
        "description": description,
    }


def _description_too_vague(input_text: str, issues: list[dict]) -> bool:
    if issues:
        text = " ".join(
            f"{issue.get('title', '')} {issue.get('description', '')}"
            for issue in issues
        ).strip()
    else:
        text = _clean_text(input_text)

    if len(text) < 18:
        return True

    return text.lower() in {
        "help",
        "issue",
        "problem",
        "not working",
        "customer issue",
        "something broke",
    }


def _confidence(issues: list[dict], input_text: str) -> float:
    if issues:
        category = issues[0].get("category")
        text = _combined_text(input_text, issues[0])
        if category != "other" and _has_concrete_failure(text) and _has_customer_impact(text):
            return 0.9
        if _has_concrete_failure(text):
            return 0.75
        return 0.6

    return 0.2 if _is_success_only(input_text) else 0.35


def normalize_issue_result(input_text: str, extracted_result: dict) -> dict:
    input_text = _clean_text(input_text)
    extracted_result = extracted_result if isinstance(extracted_result, dict) else {}
    raw_issues = extracted_result.get("issues")
    raw_issues = raw_issues if isinstance(raw_issues, list) else []

    normalized_issues = []
    normalization_reasons = []

    for raw_issue in raw_issues:
        normalized_issue = _normalize_issue(input_text, raw_issue)
        if not normalized_issue:
            continue

        normalized_issues.append(normalized_issue)
        if normalized_issue != raw_issue:
            normalization_reasons.append("normalized extracted issue taxonomy")

    if not normalized_issues:
        synthesized_issue = _normalize_issue(input_text)
        if synthesized_issue:
            normalized_issues.append(synthesized_issue)
            normalization_reasons.append("created normalized issue from actionable input")

    success_only = _is_success_only(input_text)
    concrete_failure = _has_concrete_failure(_combined_text(input_text))
    customer_impact = _has_customer_impact(_combined_text(input_text))
    inferred_category = normalized_issues[0]["category"] if normalized_issues else "other"
    description_too_vague = _description_too_vague(input_text, normalized_issues)

    requires_clarification = (
        not normalized_issues
        and (
            not concrete_failure
            or not customer_impact
            or success_only
            or (inferred_category == "other" and description_too_vague)
        )
    )

    extracted_requires_clarification = extracted_result.get("requires_clarification") is True
    clarification_overridden = extracted_requires_clarification and bool(normalized_issues)

    if clarification_overridden:
        requires_clarification = False
        normalization_reasons.append("overrode clarification because actionable issue was found")
        print("[issue_normalizer] clarification_overridden=true")

    normalization_applied = bool(normalization_reasons)
    normalization_reason = "; ".join(dict.fromkeys(normalization_reasons))
    if not normalization_reason:
        normalization_reason = "no normalization needed"

    print(
        "[issue_normalizer] "
        f"normalization_applied={str(normalization_applied).lower()} "
        f"reason={normalization_reason}"
    )

    return {
        "issues": normalized_issues,
        "requires_clarification": requires_clarification,
        "normalization_applied": normalization_applied,
        "normalization_reason": normalization_reason,
        "confidence": _confidence(normalized_issues, input_text),
        "attempts": extracted_result.get("attempts", 1),
        "fallback_used": extracted_result.get("fallback_used", False),
        "provider": extracted_result.get("provider", "gemini"),
    }
