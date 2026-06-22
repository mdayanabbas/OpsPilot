import sys
import unittest


sys.path.insert(0, "backend")

from app.agents.nodes.critic_node import critique_workflow_output  # noqa: E402


def _context(category: str, fallback_used: bool = False) -> dict:
    return {
        "issue": {
            "category": category,
            "title": "Customer issue",
            "description": "Customer reports a problem.",
        },
        "ticket": {
            "title": "Investigate issue",
            "requires_approval": category in {"billing", "auth", "security"},
            "acceptance_criteria": ["Confirm the issue is resolved."],
        },
        "reply": {"requires_approval": category in {"billing", "auth", "security"}},
        "evaluation": {"quality_score": 0.95, "unsupported_claim_rate": 0.0},
        "tool_calls": [{"status": "success", "fallback_used": fallback_used}],
    }


class CriticPolicyTests(unittest.TestCase):
    def test_clean_performance_issue_can_pass(self):
        result = critique_workflow_output(_context("performance"))

        self.assertEqual(result["critic_status"], "passed")
        self.assertFalse(result["requires_manual_review"])

    def test_provider_fallback_warns_for_performance(self):
        result = critique_workflow_output(_context("performance", fallback_used=True))

        self.assertEqual(result["critic_status"], "warning")
        self.assertTrue(result["requires_manual_review"])

    def test_sensitive_categories_warn(self):
        for category in ("billing", "auth", "security"):
            with self.subTest(category=category):
                result = critique_workflow_output(_context(category))
                self.assertEqual(result["critic_status"], "warning")
                self.assertIn(f"{category}_risk", result["risk_flags"])


if __name__ == "__main__":
    unittest.main()
