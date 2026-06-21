import sys
import types
import unittest


sys.path.insert(0, "backend")

config = types.ModuleType("app.config")
config.LLM_PROVIDER = "local"
sys.modules.setdefault("app.config", config)

gemini_service = types.ModuleType("app.services.gemini_service")


class GeminiServiceError(RuntimeError):
    pass


def generate_json(_prompt, _schema):
    raise GeminiServiceError("LLM disabled for deterministic planner tests.")


gemini_service.GeminiServiceError = GeminiServiceError
gemini_service.generate_json = generate_json
sys.modules.setdefault("app.services.gemini_service", gemini_service)

from app.agents.nodes.planner_node import plan_next_actions  # noqa: E402


class PlannerClarificationHeuristicTests(unittest.TestCase):
    def _plan_for(self, title: str, category: str = "unknown") -> dict:
        return plan_next_actions(
            {
                "workflow_type": "customer_feedback_triage",
                "issue": {
                    "category": category,
                    "title": title,
                    "description": title,
                },
                "requires_clarification": True,
                "incident_detected": False,
                "confidence": 0.82,
                "fallback_used": False,
            }
        )

    def test_successful_payment_but_inactive_subscription_needs_human_review(self):
        result = self._plan_for(
            "A customer made the payment successfully but the subscription is not yet active.",
            category="billing",
        )

        self.assertEqual(result["plan_type"], "human_review")
        self.assertTrue(result["requires_human_approval"])

    def test_duplicate_charge_needs_human_review(self):
        result = self._plan_for("Customer reports a duplicate charge.")

        self.assertEqual(result["plan_type"], "human_review")
        self.assertTrue(result["requires_human_approval"])

    def test_dashboard_freezing_is_standard_triage(self):
        result = self._plan_for("The dashboard keeps freezing for users.", category="performance")

        self.assertEqual(result["plan_type"], "standard_triage")
        self.assertFalse(result["requires_human_approval"])

    def test_login_failure_needs_human_review(self):
        result = self._plan_for("Login failed and the customer cannot access account.")

        self.assertEqual(result["plan_type"], "human_review")
        self.assertTrue(result["requires_human_approval"])


if __name__ == "__main__":
    unittest.main()
