import time
from typing import Any, Callable


def _safe_error_message(exc: Exception) -> str:
    message = str(exc).strip()
    return message or exc.__class__.__name__


def retry_with_fallback(
    operation: Callable[[], Any],
    fallback: Callable[[], Any],
    max_retries: int = 2,
) -> dict:
    attempts = 0
    last_error = None
    total_attempts = max(1, max_retries + 1)

    for attempt_index in range(total_attempts):
        attempts += 1
        try:
            return {
                "success": True,
                "result": operation(),
                "attempts": attempts,
                "fallback_used": False,
                "error": None,
            }
        except Exception as exc:
            last_error = _safe_error_message(exc)
            if attempt_index < total_attempts - 1:
                time.sleep(1)

    try:
        fallback_result = fallback()
        return {
            "success": True,
            "result": fallback_result,
            "attempts": attempts,
            "fallback_used": True,
            "error": last_error,
        }
    except Exception as exc:
        return {
            "success": False,
            "result": None,
            "attempts": attempts,
            "fallback_used": True,
            "error": _safe_error_message(exc),
        }
