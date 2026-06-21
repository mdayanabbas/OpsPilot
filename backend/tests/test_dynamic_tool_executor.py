import json
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch


sys.path.insert(0, "backend")

from app.agents.executor import execute_planned_tools  # noqa: E402


class DynamicToolExecutorTests(unittest.TestCase):
    def test_v2_generates_outputs_sequentially_and_persists_traces(self):
        db = MagicMock()
        planner_decision = SimpleNamespace(
            id=42,
            next_tools=json.dumps([
                {"tool_name": "generate_ticket"},
                {"tool_name": "generate_customer_reply"},
                {"tool_name": "evaluate_workflow_output"},
                {"tool_name": "generate_founder_summary"},
                {"tool_name": "send_incident_alert"},
            ]),
        )
        context = {
            "issue": {"title": "Export freezes"},
        }

        def fake_execute(tool_name, payload):
            if tool_name == "generate_ticket":
                return {"ok": True, "result": {"title": "Fix export"}}
            if tool_name == "generate_customer_reply":
                return {"ok": True, "result": {"risk_level": "medium"}}
            if tool_name == "evaluate_workflow_output":
                self.assertEqual(payload["ticket"]["title"], "Fix export")
                self.assertEqual(payload["reply"]["risk_level"], "medium")
                return {"ok": True, "result": {"quality_score": 0.91}}
            self.assertEqual(payload["evaluation"]["quality_score"], 0.91)
            return {"ok": True, "result": {"summary": "Workflow handled safely."}}

        with patch("app.agents.executor.execute_tool", side_effect=fake_execute):
            summary = execute_planned_tools(db, 7, planner_decision, context)

        self.assertEqual(summary["executed_count"], 4)
        self.assertEqual(summary["skipped_count"], 1)
        self.assertEqual(summary["error_count"], 0)
        self.assertEqual(summary["results"][0]["status"], "executed")
        self.assertEqual(context["ticket"]["title"], "Fix export")
        self.assertEqual(context["reply"]["risk_level"], "medium")
        self.assertEqual(summary["results"][-1]["status"], "skipped")
        self.assertEqual(
            summary["results"][-1]["result_summary"],
            "Tool is not allowlisted for dynamic execution v2.",
        )
        self.assertEqual(db.add.call_count, 5)
        self.assertTrue(all(call.args[0].planner_decision_id == 42 for call in db.add.call_args_list))
        db.commit.assert_called_once()

    def test_failed_dynamic_ticket_is_available_for_legacy_fallback(self):
        db = MagicMock()
        planner_decision = {"id": 9, "next_tools": [{"tool_name": "generate_ticket"}]}
        context = {"issue": {"title": "Export freezes"}}

        with patch(
            "app.agents.executor.execute_tool",
            return_value={"ok": False, "error": {"message": "Ticket generation unavailable."}},
        ):
            summary = execute_planned_tools(db, 3, planner_decision, context)

        self.assertEqual(summary["error_count"], 1)
        self.assertEqual(summary["results"][0]["status"], "error")
        self.assertEqual(summary["results"][0]["error_message"], "Ticket generation unavailable.")
        self.assertNotIn("ticket", context)


if __name__ == "__main__":
    unittest.main()
