from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.agents.nodes.evaluation_node import evaluate_workflow_output
from app.agents.nodes.intent_router_node import detect_workflow_intent
from app.agents.nodes.issue_extraction_node import extract_issues
from app.agents.nodes.reply_generation_node import generate_customer_reply
from app.agents.nodes.ticket_generation_node import generate_ticket
from app.database import get_db
from app.models.agent_step import AgentStep
from app.models.evaluation import EvaluationResult
from app.models.reply import CustomerReply
from app.models.summary import FounderSummary
from app.models.ticket import Ticket
from app.models.tool_call import ToolCall
from app.models.workflow import WorkflowRun
from app.schemas.agent_step_schema import AgentStepResponse
from app.schemas.evaluation_schema import EvaluationResultResponse
from app.schemas.reply_schema import CustomerReplyResponse
from app.schemas.summary_schema import FounderSummaryResponse
from app.schemas.ticket_schema import TicketResponse
from app.schemas.tool_call_schema import ToolCallResponse
from app.schemas.workflow_schema import WorkflowRunCreate, WorkflowRunResponse

router = APIRouter()

LOW_INTENT_CONFIDENCE_THRESHOLD = 0.60


@router.get("")
def list_workflow_runs(db: Session = Depends(get_db)):
    workflow_runs = (
        db.query(WorkflowRun)
        .order_by(WorkflowRun.created_at.desc())
        .all()
    )

    results = []
    for workflow_run in workflow_runs:
        ticket_count = (
            db.query(Ticket)
            .filter(Ticket.workflow_run_id == workflow_run.id)
            .count()
        )
        evaluation = (
            db.query(EvaluationResult)
            .filter(EvaluationResult.workflow_run_id == workflow_run.id)
            .first()
        )
        reply_requires_approval = (
            db.query(CustomerReply)
            .filter(
                CustomerReply.workflow_run_id == workflow_run.id,
                CustomerReply.requires_approval.is_(True),
            )
            .first()
            is not None
        )

        results.append(
            {
                "id": workflow_run.id,
                "input_text": workflow_run.input_text,
                "status": workflow_run.status,
                "workflow_type": workflow_run.workflow_type,
                "confidence": workflow_run.confidence,
                "created_at": workflow_run.created_at,
                "updated_at": workflow_run.updated_at,
                "ticket_count": ticket_count,
                "human_review_required": bool(
                    reply_requires_approval
                    or (
                        evaluation.requires_human_review
                        if evaluation
                        else False
                    )
                ),
            }
        )

    return results


@router.post("/run", response_model=WorkflowRunResponse)
def create_workflow_run(payload: WorkflowRunCreate, db: Session = Depends(get_db)):
    try:
        print("[workflow_routes] calling detect_workflow_intent")
        intent_result = detect_workflow_intent(payload.input_text)
        print(f"[workflow_routes] intent_result={intent_result}")
    except Exception as exc:
        print(f"[workflow_routes] intent_router exception={exc!r}")
        workflow_run = WorkflowRun(
            input_text=payload.input_text,
            status="failed",
            workflow_type="customer_feedback_triage",
            confidence=0.0,
        )
        db.add(workflow_run)
        db.commit()
        db.refresh(workflow_run)

        db.add(
            AgentStep(
                workflow_run_id=workflow_run.id,
                step_name="intent_router",
                status="failed",
                input_summary="Received customer feedback text.",
                output_summary="Intent detection failed.",
                confidence=0.0,
                error_message=str(exc),
            )
        )
        db.add(
            ToolCall(
                workflow_run_id=workflow_run.id,
                step_name="intent_router",
                tool_name="gemini_intent_router",
                status="failed",
                attempt=1,
                fallback_used=False,
                error_message=str(exc),
            )
        )
        db.commit()
        db.refresh(workflow_run)

        return workflow_run

    intent_confidence = float(intent_result["confidence"])
    needs_intent_clarification = (
        intent_result["requires_clarification"]
        or intent_confidence < LOW_INTENT_CONFIDENCE_THRESHOLD
    )

    workflow_status = (
        "needs_clarification"
        if needs_intent_clarification
        else "running"
    )

    workflow_run = WorkflowRun(
        input_text=payload.input_text,
        status=workflow_status,
        workflow_type=intent_result["workflow_type"],
        confidence=intent_confidence,
    )

    db.add(workflow_run)
    db.commit()
    db.refresh(workflow_run)

    intent_step = AgentStep(
        workflow_run_id=workflow_run.id,
        step_name="intent_router",
        status=(
            "needs_clarification"
            if needs_intent_clarification
            else "completed"
        ),
        input_summary="Received customer feedback text.",
        output_summary=intent_result["reason"],
        confidence=intent_confidence,
        latency_ms=None,
    )

    intent_tool_call = ToolCall(
        workflow_run_id=workflow_run.id,
        step_name="intent_router",
        tool_name="gemini_intent_router",
        status="success",
        attempt=1,
        fallback_used=False,
        error_message=None,
    )

    if needs_intent_clarification:
        db.add_all([intent_step, intent_tool_call])
        db.commit()
        db.refresh(workflow_run)

        return workflow_run

    planner_step = AgentStep(
        workflow_run_id=workflow_run.id,
        step_name="planner",
        status="completed",
        input_summary="Workflow type confirmed.",
        output_summary="Generated initial triage plan.",
        confidence=0.88,
        latency_ms=180,
    )

    try:
        issue_result = extract_issues(payload.input_text)
        issues = issue_result.get("issues", [])
        if not isinstance(issues, list):
            issues = []
    except Exception as exc:
        db.add_all(
            [
                intent_step,
                planner_step,
                intent_tool_call,
                AgentStep(
                    workflow_run_id=workflow_run.id,
                    step_name="issue_extraction",
                    status="failed",
                    input_summary="Raw customer feedback text.",
                    output_summary="Issue extraction failed.",
                    confidence=0.0,
                    error_message=str(exc),
                ),
                ToolCall(
                    workflow_run_id=workflow_run.id,
                    step_name="issue_extraction",
                    tool_name="gemini_issue_extractor",
                    status="failed",
                    attempt=1,
                    fallback_used=False,
                    error_message=str(exc),
                ),
            ]
        )
        workflow_run.status = "failed"
        db.commit()
        db.refresh(workflow_run)

        return workflow_run

    issue_extraction_step = AgentStep(
        workflow_run_id=workflow_run.id,
        step_name="issue_extraction",
        status="completed",
        input_summary="Raw customer feedback text.",
        output_summary=(
            f"Extracted {len(issues)} issue(s)."
            if issues
            else "No actionable customer issues extracted."
        ),
        confidence=0.85,
    )

    issue_extraction_tool_call = ToolCall(
        workflow_run_id=workflow_run.id,
        step_name="issue_extraction",
        tool_name="gemini_issue_extractor",
        status="success",
        attempt=1,
        fallback_used=False,
        error_message=None,
    )

    starter_steps = [
        intent_step,
        planner_step,
        issue_extraction_step,
        AgentStep(
            workflow_run_id=workflow_run.id,
            step_name="ticket_generation",
            status="completed",
            input_summary="Detected billing-related customer complaint.",
            output_summary="Created one engineering ticket.",
            confidence=0.86,
            latency_ms=260,
        ),
        AgentStep(
            workflow_run_id=workflow_run.id,
            step_name="reply_generation",
            status="completed",
            input_summary="Generated support reply draft.",
            output_summary="Reply requires human approval before sending.",
            confidence=0.84,
            latency_ms=210,
        ),
        AgentStep(
            workflow_run_id=workflow_run.id,
            step_name="evaluation",
            status="completed",
            input_summary="Checked ticket and reply quality.",
            output_summary="Workflow output passed initial evaluation.",
            confidence=0.89,
            latency_ms=150,
        ),
    ]

    if not issues:
        db.add_all(starter_steps[:3])
        db.add_all([intent_tool_call, issue_extraction_tool_call])
        workflow_run.status = "needs_clarification"
        db.commit()
        db.refresh(workflow_run)

        return workflow_run

    first_issue = issues[0]
    generated_ticket = generate_ticket(first_issue)
    reply_result = generate_customer_reply(first_issue)
    evaluation_result = evaluate_workflow_output(
        issue=first_issue,
        ticket=generated_ticket,
        reply=reply_result,
        fallback_used=reply_result.get("fallback_used", False),
    )

    ticket_tool_call = ToolCall(
        workflow_run_id=workflow_run.id,
        step_name="ticket_generation",
        tool_name="gemini_ticket_generator",
        status="success",
        attempt=1,
        fallback_used=False,
        error_message=None,
    )
    reply_tool_call = ToolCall(
        workflow_run_id=workflow_run.id,
        step_name="reply_generation",
        tool_name="gemini_reply_generator",
        status="success",
        attempt=reply_result.get("attempts", 1),
        fallback_used=reply_result.get("fallback_used", False),
        error_message=None,
    )

    starter_tool_calls = [
        intent_tool_call,
        issue_extraction_tool_call,
        ticket_tool_call,
        reply_tool_call,
    ]

    ticket = Ticket(
        workflow_run_id=workflow_run.id,
        title=generated_ticket["title"],
        priority=generated_ticket["priority"],
        team=generated_ticket["team"],
        category=generated_ticket["category"],
        description=generated_ticket["description"],
        acceptance_criteria="\n".join(generated_ticket["acceptance_criteria"]),
        source_evidence=first_issue["description"],
        requires_approval=True,
        status="draft",
    )

    reply = CustomerReply(
        workflow_run_id=workflow_run.id,
        customer=reply_result["customer"],
        issue=reply_result["issue"],
        draft_reply=reply_result["draft_reply"],
        risk_level=reply_result["risk_level"],
        risk_reason=reply_result["risk_reason"],
        requires_approval=reply_result["requires_approval"],
        status="draft",
    )

    founder_summary = FounderSummary(
        workflow_run_id=workflow_run.id,
        summary=(
            "A billing-related customer issue was detected. The customer reports that an invoice "
            "still appears unpaid after payment. This may indicate a payment status synchronization problem."
        ),
        risks="Customer-facing billing issue may create trust risk if repeated.",
        recommended_actions=(
            "1. Review payment webhook/sync logs.\n"
            "2. Confirm whether invoice status updated internally.\n"
            "3. Approve customer reply before sending.\n"
            "4. Create backend investigation ticket."
        ),
    )

    evaluation = EvaluationResult(
        workflow_run_id=workflow_run.id,
        quality_score=evaluation_result["quality_score"],
        reply_policy_compliance=evaluation_result["reply_policy_compliance"],
        ticket_completeness=evaluation_result["ticket_completeness"],
        unsupported_claim_rate=evaluation_result["unsupported_claim_rate"],
        tool_recovery_success=evaluation_result["tool_recovery_success"],
        requires_human_review=evaluation_result["requires_human_review"],
        risks=evaluation_result["risks"],
    )

    db.add_all(starter_tool_calls)
    db.add_all(starter_steps)
    db.add(ticket)
    db.add(reply)
    db.add(founder_summary)
    db.add(evaluation)

    workflow_run.status = "completed"

    db.commit()
    db.refresh(workflow_run)

    return workflow_run


@router.get("/run")
def workflow_run_endpoint_hint():
    raise HTTPException(
        status_code=405,
        detail="Use POST /api/v1/workflows/run with JSON body: {'input_text': '...'}",
    )


@router.get("/{workflow_run_id}", response_model=WorkflowRunResponse)
def get_workflow_run(workflow_run_id: int, db: Session = Depends(get_db)):
    workflow_run = db.query(WorkflowRun).filter(WorkflowRun.id == workflow_run_id).first()

    if not workflow_run:
        raise HTTPException(status_code=404, detail="Workflow run not found")

    return workflow_run


@router.get("/{workflow_run_id}/steps", response_model=list[AgentStepResponse])
def get_workflow_steps(workflow_run_id: int, db: Session = Depends(get_db)):
    workflow_run = db.query(WorkflowRun).filter(WorkflowRun.id == workflow_run_id).first()

    if not workflow_run:
        raise HTTPException(status_code=404, detail="Workflow run not found")

    return (
        db.query(AgentStep)
        .filter(AgentStep.workflow_run_id == workflow_run_id)
        .order_by(AgentStep.id.asc())
        .all()
    )


@router.get("/{workflow_run_id}/tool-calls", response_model=list[ToolCallResponse])
def get_workflow_tool_calls(workflow_run_id: int, db: Session = Depends(get_db)):
    workflow_run = db.query(WorkflowRun).filter(WorkflowRun.id == workflow_run_id).first()

    if not workflow_run:
        raise HTTPException(status_code=404, detail="Workflow run not found")

    return (
        db.query(ToolCall)
        .filter(ToolCall.workflow_run_id == workflow_run_id)
        .order_by(ToolCall.id.asc())
        .all()
    )


@router.get("/{workflow_run_id}/outputs")
def get_workflow_outputs(workflow_run_id: int, db: Session = Depends(get_db)):
    workflow_run = db.query(WorkflowRun).filter(WorkflowRun.id == workflow_run_id).first()

    if not workflow_run:
        raise HTTPException(status_code=404, detail="Workflow run not found")

    tickets = db.query(Ticket).filter(Ticket.workflow_run_id == workflow_run_id).all()
    replies = db.query(CustomerReply).filter(CustomerReply.workflow_run_id == workflow_run_id).all()
    founder_summary = (
        db.query(FounderSummary)
        .filter(FounderSummary.workflow_run_id == workflow_run_id)
        .first()
    )
    evaluation = (
        db.query(EvaluationResult)
        .filter(EvaluationResult.workflow_run_id == workflow_run_id)
        .first()
    )

    return {
        "workflow_run": WorkflowRunResponse.model_validate(workflow_run),
        "tickets": [TicketResponse.model_validate(ticket) for ticket in tickets],
        "customer_replies": [CustomerReplyResponse.model_validate(reply) for reply in replies],
        "founder_summary": (
            FounderSummaryResponse.model_validate(founder_summary)
            if founder_summary
            else None
        ),
        "evaluation": (
            EvaluationResultResponse.model_validate(evaluation)
            if evaluation
            else None
        ),
    }
