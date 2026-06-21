import sys
import unittest
from types import SimpleNamespace


sys.path.insert(0, "backend")

from app.services.incident_planner import create_incident_response_plan  # noqa: E402


class IncidentPlannerTests(unittest.TestCase):
    def test_billing_plan_includes_alert_without_executing_it(self):
        plan = create_incident_response_plan(
            SimpleNamespace(
                category="billing",
                severity="high",
                workflow_count=5,
            ),
            {"operational_risks": ["payment sync issue"]},
        )

        self.assertEqual(plan["plan_type"], "billing_incident")
        self.assertEqual(
            plan["next_tools"],
            ["search_memory", "generate_founder_summary", "send_incident_alert"],
        )
        self.assertIn("does not execute", plan["reasoning"])

    def test_performance_plan_remains_read_only(self):
        plan = create_incident_response_plan(
            {"category": "performance", "severity": "medium", "workflow_count": 3},
            {"root_cause_clusters": [{"theme": "timeout"}]},
        )

        self.assertEqual(plan["plan_type"], "performance_incident")
        self.assertEqual(
            plan["next_tools"],
            ["search_memory", "generate_founder_summary"],
        )

    def test_unknown_category_uses_general_plan(self):
        plan = create_incident_response_plan(
            {"category": "integration", "severity": "high", "workflow_count": 4},
            {},
        )

        self.assertEqual(plan["plan_type"], "general_incident")


if __name__ == "__main__":
    unittest.main()
