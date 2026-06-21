import json
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch


sys.path.insert(0, "backend")

from app.agents.executor import execute_planned_tools  # noqa: E402


class DynamicToolExecutorTests(unittest.TestCase):
    def test_executes_allowlisted_tools_skips_unsafe_tools_and_persists_traces(self):
        db = MagicMock()
        planner_decision = SimpleNamespace(
            id=42,
            next_tools=json.dumps([
                {"tool_name": "generate_ticket"},
                {"tool_name": "evaluate_workflow_output"},
                {"tool_name": "generate_founder_summary"},
            ]),
        )
        context = {
            "issue": {"title": "Export freezes"},
            "ticket": {"title": "Fix export"},
            "reply": {"draft_reply": "We are investigating."},
        }

        def fake_execute(tool_name, payload):
            if tool_name == "evaluate_workflow_output":
                return {"ok": True, "result": {"quality_score": 0.91}}
            self.assertEqual(payload["evaluation"]["quality_score"], 0.91)
            return {"ok": True, "result": {"summary": "Workflow handled safely."}}

        with patch("app.agents.executor.execute_tool", side_effect=fake_execute):
            summary = execute_planned_tools(db, 7, planner_decision, context)

        self.assertEqual(summary["executed_count"], 2)
        self.assertEqual(summary["skipped_count"], 1)
        self.assertEqual(summary["error_count"], 0)
        self.assertEqual(summary["results"][0]["status"], "skipped")
        self.assertEqual(
            summary["results"][0]["result_summary"],
            "Tool is not allowlisted for dynamic execution v1.",
        )
        self.assertEqual(db.add.call_count, 3)
        self.assertTrue(all(call.args[0].planner_decision_id == 42 for call in db.add.call_args_list))
        db.commit.assert_called_once()

    def test_collects_registry_errors(self):
        db = MagicMock()
        planner_decision = {"id": 9, "next_tools": [{"tool_name": "detect_incident"}]}

        with patch(
            "app.agents.executor.execute_tool",
            return_value={"ok": False, "error": {"message": "Detection unavailable."}},
        ):
            summary = execute_planned_tools(db, 3, planner_decision, {})

        self.assertEqual(summary["error_count"], 1)
        self.assertEqual(summary["results"][0]["status"], "error")
        self.assertEqual(summary["results"][0]["error_message"], "Detection unavailable.")


if __name__ == "__main__":
    unittest.main()
