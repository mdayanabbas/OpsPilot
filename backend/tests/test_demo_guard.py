import sys
import unittest
from unittest.mock import patch

from fastapi import HTTPException
from starlette.requests import Request


sys.path.insert(0, "backend")

from app.services import demo_guard  # noqa: E402


def _request(api_key: str | None = None) -> Request:
    headers = []
    if api_key is not None:
        headers.append((b"x-demo-api-key", api_key.encode("utf-8")))
    return Request({"type": "http", "headers": headers})


class DemoGuardTests(unittest.TestCase):
    def setUp(self):
        with demo_guard._workflow_rate_limit_lock:
            demo_guard._workflow_creation_timestamps.clear()

    def test_demo_mode_disabled_allows_request_without_key(self):
        with patch.object(demo_guard, "DEMO_MODE", False):
            demo_guard.require_demo_api_key(_request())

    def test_missing_key_is_unauthorized(self):
        with patch.object(demo_guard, "DEMO_MODE", True), patch.object(
            demo_guard, "DEMO_API_KEY", "secret"
        ):
            with self.assertRaises(HTTPException) as raised:
                demo_guard.require_demo_api_key(_request())
        self.assertEqual(raised.exception.status_code, 401)

    def test_invalid_key_is_forbidden(self):
        with patch.object(demo_guard, "DEMO_MODE", True), patch.object(
            demo_guard, "DEMO_API_KEY", "secret"
        ):
            with self.assertRaises(HTTPException) as raised:
                demo_guard.require_demo_api_key(_request("wrong"))
        self.assertEqual(raised.exception.status_code, 403)

    def test_workflow_limit_returns_too_many_requests(self):
        with patch.object(demo_guard, "DEMO_MODE", True), patch.object(
            demo_guard, "DEMO_API_KEY", "secret"
        ), patch.object(demo_guard, "MAX_WORKFLOWS_PER_HOUR", 2):
            request = _request("secret")
            demo_guard.require_workflow_creation_allowed(request)
            demo_guard.require_workflow_creation_allowed(request)
            with self.assertRaises(HTTPException) as raised:
                demo_guard.require_workflow_creation_allowed(request)
        self.assertEqual(raised.exception.status_code, 429)
        self.assertIn("Retry-After", raised.exception.headers)


if __name__ == "__main__":
    unittest.main()
