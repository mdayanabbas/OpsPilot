import json
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch


sys.path.insert(0, "backend")

from app.services.incident_response_executor import execute_incident_response_plan  # noqa: E402


class IncidentResponseExecutorTests(unittest.TestCase):
    def test_executes_read_only_tools_and_skips_alert(self):
        db = MagicMock()
        incident = SimpleNamespace(
            id=4,
            category="billing",
            title="Billing incident suspected",
            description="Five billing workflows are affected.",
            severity="high",
        )
        plan = SimpleNamespace(
            id=8,
            next_tools=json.dumps([
                "search_memory",
                "generate_founder_summary",
                "send_incident_alert",
            ]),
        )

        def fake_execute(tool_name, payload):
            if tool_name == "search_memory":
                return {
                    "ok": True,
                    "result": {"matches": [{"workflow_run_id": 12}]},
                }
            self.assertEqual(payload["memory_matches"][0]["workflow_run_id"], 12)
            return {"ok": True, "result": {"summary": "Billing incident summary."}}

        with patch(
            "app.services.incident_response_executor.execute_tool",
            side_effect=fake_execute,
        ) as execute_mock:
            summary = execute_incident_response_plan(db, incident, plan)

        self.assertEqual(summary["executed_count"], 2)
        self.assertEqual(summary["skipped_count"], 1)
        self.assertEqual(summary["error_count"], 0)
        self.assertEqual(execute_mock.call_count, 2)
        self.assertEqual(db.add.call_count, 3)
        self.assertEqual(db.add.call_args_list[-1].args[0].tool_name, "send_incident_alert")
        self.assertEqual(db.add.call_args_list[-1].args[0].status, "skipped")
        db.commit.assert_called_once()

    def test_tool_failure_still_persists_error_trace(self):
        db = MagicMock()
        incident = SimpleNamespace(
            id=5,
            category="performance",
            title="Performance incident",
            description="Exports time out.",
            severity="medium",
        )
        plan = SimpleNamespace(id=9, next_tools=json.dumps(["search_memory"]))

        with patch(
            "app.services.incident_response_executor.execute_tool",
            return_value={"ok": False, "error": {"message": "Memory unavailable."}},
        ):
            summary = execute_incident_response_plan(db, incident, plan)

        self.assertEqual(summary["error_count"], 1)
        trace = db.add.call_args.args[0]
        self.assertEqual(trace.status, "error")
        self.assertEqual(trace.error_message, "Memory unavailable.")


if __name__ == "__main__":
    unittest.main()
