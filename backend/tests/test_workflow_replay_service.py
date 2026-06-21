import sys
import unittest
from unittest.mock import patch


sys.path.insert(0, "backend")

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import models  # noqa: F401,E402
from app.database import Base  # noqa: E402
from app.models.critic_result import CriticResult  # noqa: E402
from app.models.evaluation import EvaluationResult  # noqa: E402
from app.models.planner_decision import PlannerDecision  # noqa: E402
from app.models.reply import CustomerReply  # noqa: E402
from app.models.ticket import Ticket  # noqa: E402
from app.models.workflow import WorkflowRun  # noqa: E402
from app.models.tool_call import ToolCall  # noqa: E402
from app.models.workflow_replay import WorkflowReplay  # noqa: E402
from app.services.workflow_replay_service import (  # noqa: E402
    compare_workflow_runs,
    replay_workflow_run,
)


class WorkflowReplayComparisonTests(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        self.db = sessionmaker(bind=engine)()

    def tearDown(self):
        self.db.close()

    def _create_run(self, *, priority: str, risk_level: str) -> WorkflowRun:
        run = WorkflowRun(
            input_text="Dashboard freezes when exporting reports.",
            status="completed",
            workflow_type="customer_feedback_triage",
            confidence=0.9,
        )
        self.db.add(run)
        self.db.flush()
        self.db.add_all([
            Ticket(
                workflow_run_id=run.id,
                title="Export freezes",
                priority=priority,
                category="performance",
                description="Export freezes.",
                requires_approval=False,
            ),
            CustomerReply(
                workflow_run_id=run.id,
                issue="Export freezes.",
                risk_level=risk_level,
                requires_approval=True,
            ),
            EvaluationResult(workflow_run_id=run.id, quality_score=0.9),
            CriticResult(
                workflow_run_id=run.id,
                critic_status="passed",
                risk_flags="[]",
                quality_notes="[]",
                recommended_action="Continue review.",
                requires_manual_review=False,
            ),
            PlannerDecision(
                workflow_run_id=run.id,
                plan_type="standard_triage",
                next_tools="[]",
                requires_human_approval=False,
                reasoning_summary="Actionable issue.",
            ),
        ])
        self.db.commit()
        return run

    def test_compare_reports_changed_fields(self):
        source = self._create_run(priority="medium", risk_level="low")
        replay = self._create_run(priority="high", risk_level="medium")

        diff = compare_workflow_runs(self.db, source.id, replay.id)

        self.assertTrue(diff["changed"])
        self.assertEqual(
            {change["field"] for change in diff["changes"]},
            {"ticket.priority", "reply.risk_level"},
        )

    def test_compare_reports_unchanged_runs(self):
        source = self._create_run(priority="medium", risk_level="low")
        replay = self._create_run(priority="medium", risk_level="low")

        diff = compare_workflow_runs(self.db, source.id, replay.id)

        self.assertFalse(diff["changed"])
        self.assertEqual(diff["changes"], [])

    def test_replay_reuses_input_and_records_link_and_tool_call(self):
        source = WorkflowRun(
            input_text="Payment succeeded but subscription is inactive.",
            status="completed",
            workflow_type="customer_feedback_triage",
            confidence=0.9,
        )
        self.db.add(source)
        self.db.commit()

        def fake_runner(*, payload, db, workflow_run_id):
            replay_run = db.query(WorkflowRun).filter(WorkflowRun.id == workflow_run_id).first()
            self.assertEqual(payload.input_text, source.input_text)
            replay_run.status = "completed"
            replay_run.workflow_type = source.workflow_type
            replay_run.confidence = source.confidence
            db.commit()
            return replay_run

        with patch(
            "app.api.v1.workflow_routes._execute_workflow_run_sync",
            side_effect=fake_runner,
        ):
            result = replay_workflow_run(self.db, source.id)

        replay = self.db.query(WorkflowReplay).filter(WorkflowReplay.id == result["replay_id"]).first()
        replay_run = self.db.query(WorkflowRun).filter(WorkflowRun.id == replay.replay_workflow_run_id).first()
        tool_call = (
            self.db.query(ToolCall)
            .filter(ToolCall.workflow_run_id == replay_run.id)
            .first()
        )
        self.assertEqual(replay_run.input_text, source.input_text)
        self.assertEqual(replay.status, "completed")
        self.assertFalse(result["changed"])
        self.assertEqual(tool_call.step_name, "workflow_replay")
        self.assertEqual(tool_call.provider, "deterministic")


if __name__ == "__main__":
    unittest.main()
