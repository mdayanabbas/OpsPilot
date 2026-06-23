"""Guards for mutation endpoints exposed by an OpsPilot demo deployment."""

from collections import deque
from secrets import compare_digest
from threading import Lock
from time import monotonic

from fastapi import HTTPException, Request, status

from app.config import DEMO_API_KEY, DEMO_MODE, MAX_WORKFLOWS_PER_HOUR


_RATE_LIMIT_WINDOW_SECONDS = 60 * 60
_workflow_creation_timestamps: deque[float] = deque()
_workflow_rate_limit_lock = Lock()


def require_demo_api_key(request: Request) -> None:
    """Require the configured demo key when demo mode is enabled."""
    if not DEMO_MODE:
        return

    supplied_key = request.headers.get("X-Demo-Api-Key")
    if not supplied_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-Demo-Api-Key header is required.",
        )

    # A blank configured key must never make a public mutation endpoint usable.
    if not DEMO_API_KEY or not compare_digest(supplied_key, DEMO_API_KEY):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid demo API key.",
        )


def require_workflow_creation_allowed(request: Request) -> None:
    """Authenticate and rate-limit workflow creation in demo mode."""
    require_demo_api_key(request)
    if not DEMO_MODE:
        return

    now = monotonic()
    cutoff = now - _RATE_LIMIT_WINDOW_SECONDS

    with _workflow_rate_limit_lock:
        while (
            _workflow_creation_timestamps
            and _workflow_creation_timestamps[0] <= cutoff
        ):
            _workflow_creation_timestamps.popleft()

        if len(_workflow_creation_timestamps) >= MAX_WORKFLOWS_PER_HOUR:
            retry_after = max(
                1,
                int(
                    _RATE_LIMIT_WINDOW_SECONDS
                    - (now - _workflow_creation_timestamps[0])
                ),
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Workflow creation rate limit exceeded.",
                headers={"Retry-After": str(retry_after)},
            )

        _workflow_creation_timestamps.append(now)
