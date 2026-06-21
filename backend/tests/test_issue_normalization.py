import sys
import unittest


sys.path.insert(0, "backend")

from app.agents.nodes.issue_normalization_node import normalize_issue_result  # noqa: E402


class IssueNormalizationTests(unittest.TestCase):
    def _normalize(self, text: str, extracted_result: dict | None = None) -> dict:
        return normalize_issue_result(text, extracted_result or {"issues": []})

    def test_payment_successful_but_subscription_inactive(self):
        result = self._normalize(
            "A customer made the payment successfully but the subscription is not yet active."
        )

        self.assertFalse(result["requires_clarification"])
        self.assertTrue(result["normalization_applied"])
        self.assertEqual(result["issues"][0]["category"], "billing")
        self.assertEqual(result["issues"][0]["severity"], "high")

    def test_payment_succeeded_but_subscription_disabled(self):
        result = self._normalize("Payment succeeded but subscription remains disabled.")

        self.assertFalse(result["requires_clarification"])
        self.assertEqual(result["issues"][0]["category"], "billing")

    def test_password_reset_login_failure(self):
        result = self._normalize("Users cannot login after password reset.")

        self.assertFalse(result["requires_clarification"])
        self.assertEqual(result["issues"][0]["category"], "auth")

    def test_dashboard_freezes_while_exporting_reports(self):
        result = self._normalize("Dashboard freezes while exporting reports.")

        self.assertFalse(result["requires_clarification"])
        self.assertEqual(result["issues"][0]["category"], "performance")

    def test_webhook_sync_failed_between_stripe_and_billing(self):
        result = self._normalize("Webhook sync between Stripe and CRM is failing.")

        self.assertFalse(result["requires_clarification"])
        self.assertEqual(result["issues"][0]["category"], "integration")

    def test_success_only_feedback_requires_clarification(self):
        result = self._normalize("Everything works perfectly.")

        self.assertTrue(result["requires_clarification"])
        self.assertEqual(result["issues"], [])

    def test_extracted_clarification_is_overridden_for_actionable_input(self):
        result = self._normalize(
            "Payment succeeded but subscription remains disabled.",
            {"issues": [], "requires_clarification": True},
        )

        self.assertFalse(result["requires_clarification"])
        self.assertTrue(result["normalization_applied"])
        self.assertIn("overrode clarification", result["normalization_reason"])

    def test_successful_purchase_requires_clarification(self):
        result = self._normalize("John purchased successfully.")

        self.assertTrue(result["requires_clarification"])
        self.assertEqual(result["issues"], [])

    def test_result_has_documented_contract(self):
        result = self._normalize("Dashboard freezes when exporting reports.")

        self.assertEqual(
            set(result),
            {
                "issues",
                "requires_clarification",
                "normalization_applied",
                "normalization_reason",
                "confidence",
            },
        )

    def test_explicitly_no_customer_impact_requires_clarification(self):
        result = self._normalize("Webhook failed in an internal test only; no customers affected.")

        self.assertTrue(result["requires_clarification"])
        self.assertEqual(result["issues"], [])


if __name__ == "__main__":
    unittest.main()
