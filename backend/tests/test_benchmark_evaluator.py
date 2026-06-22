import sys
import unittest
from unittest.mock import patch


sys.path.insert(0, "backend")

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import models  # noqa: F401,E402
from app.database import Base  # noqa: E402
from app.models.benchmark_expectation import BenchmarkExpectation  # noqa: E402
from app.models.critic_result import CriticResult  # noqa: E402
from app.models.planner_decision import PlannerDecision  # noqa: E402
from app.models.ticket import Ticket  # noqa: E402
from app.models.workflow import WorkflowRun  # noqa: E402
from app.services.benchmark_evaluator import (  # noqa: E402
    evaluate_benchmark_case,
    load_regression_cases,
    run_benchmark_suite,
)


class BenchmarkRegressionEvaluatorTests(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        self.db = sessionmaker(bind=engine)()

    def tearDown(self):
        self.db.close()

    def _persist_actual(self, benchmark_case: dict) -> WorkflowRun:
        expected = benchmark_case["expectation"]
        run = WorkflowRun(
            input_text=benchmark_case["input_text"],
            status=expected["expected_workflow_status"],
            workflow_type="customer_feedback_triage",
            confidence=0.9,
        )
        self.db.add(run)
        self.db.flush()
        self.db.add_all([
            Ticket(
                workflow_run_id=run.id,
                title="Regression ticket",
                priority=expected["expected_priority"],
                category=expected["expected_category"],
                description="Regression output.",
                requires_approval=expected["expected_requires_approval"],
            ),
            PlannerDecision(
                workflow_run_id=run.id,
                plan_type=expected["expected_plan_type"],
                next_tools="[]",
                requires_human_approval=expected["expected_requires_approval"],
                reasoning_summary="Regression plan.",
            ),
            CriticResult(
                workflow_run_id=run.id,
                critic_status=expected["expected_critic_status"],
                risk_flags="[]",
                quality_notes="[]",
                recommended_action="Review result.",
                requires_manual_review=False,
            ),
        ])
        self.db.commit()
        return run

    def test_dataset_contains_exact_requested_15_cases(self):
        cases = load_regression_cases()
        self.assertEqual(len(cases), 15)
        self.assertEqual(
            {case["category"] for case in cases},
            {"billing", "auth", "performance", "notification", "integration", "security"},
        )

    def test_evaluator_scores_six_persisted_outputs(self):
        benchmark_case = load_regression_cases()[0]
        expectation = BenchmarkExpectation(
            benchmark_case_id=benchmark_case["id"],
            **benchmark_case["expectation"],
        )
        self.db.add(expectation)
        run = self._persist_actual(benchmark_case)

        result = evaluate_benchmark_case(self.db, benchmark_case, run)

        self.assertEqual(result["total_score"], 1.0)
        self.assertTrue(result["passed"])
        self.assertEqual(result["mismatches"], [])

    def test_full_suite_aggregates_deterministically(self):
        cases_by_input = {case["input_text"]: case for case in load_regression_cases()}

        def fake_runner(*, payload, db):
            return self._persist_actual(cases_by_input[payload.input_text])

        with patch(
            "app.api.v1.workflow_routes._execute_workflow_run_sync",
            side_effect=fake_runner,
        ):
            summary = run_benchmark_suite(self.db)

        self.assertEqual(summary["cases_run"], 15)
        self.assertEqual(summary["avg_score"], 1.0)
        self.assertEqual(summary["planner_accuracy"], 1.0)
        self.assertEqual(summary["category_accuracy"], 1.0)
        self.assertEqual(summary["priority_accuracy"], 1.0)
        self.assertEqual(summary["critic_accuracy"], 1.0)


if __name__ == "__main__":
    unittest.main()
