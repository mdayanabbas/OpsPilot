from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.approval import ApprovalDecision
from app.models.approval_comment import ApprovalComment
from app.models.reply import CustomerReply
from app.models.ticket import Ticket
from app.models.workflow import WorkflowRun
from app.services.approval_queue_service import (
    get_approval_queue,
    get_approval_stats,
)

router = APIRouter()


class ApprovalDecisionRequest(BaseModel):
    workflow_run_id: int
    item_type: Literal["ticket", "reply", "incident_action"]
    item_id: int
    reviewer_note: str | None = None


class ApprovalCommentRequest(BaseModel):
    approval_id: int
    reviewer: str = Field(min_length=1, max_length=150)
    comment: str = Field(min_length=1, max_length=5000)


@router.get("/")
def list_approvals():
    return {"message": "Approvals module coming soon"}


@router.get("/queue")
def approval_queue(db: Session = Depends(get_db)):
    return get_approval_queue(db)


@router.get("/stats")
def approval_stats(db: Session = Depends(get_db)):
    return get_approval_stats(db)


@router.post("/comment")
def add_approval_comment(
    payload: ApprovalCommentRequest,
    db: Session = Depends(get_db),
):
    approval = (
        db.query(ApprovalDecision)
        .filter(ApprovalDecision.id == payload.approval_id)
        .first()
    )
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")

    comment = ApprovalComment(
        approval_id=approval.id,
        reviewer=payload.reviewer.strip(),
        comment=payload.comment.strip(),
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return {
        "id": comment.id,
        "approval_id": comment.approval_id,
        "reviewer": comment.reviewer,
        "comment": comment.comment,
        "created_at": comment.created_at,
    }


@router.get("/{approval_id}/comments")
def list_approval_comments(approval_id: int, db: Session = Depends(get_db)):
    approval = (
        db.query(ApprovalDecision)
        .filter(ApprovalDecision.id == approval_id)
        .first()
    )
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")

    return (
        db.query(ApprovalComment)
        .filter(ApprovalComment.approval_id == approval_id)
        .order_by(ApprovalComment.created_at.asc(), ApprovalComment.id.asc())
        .all()
    )


def create_approval_decision(
    payload: ApprovalDecisionRequest,
    decision: Literal["approved", "rejected"],
    db: Session,
):
    workflow_run = (
        db.query(WorkflowRun)
        .filter(WorkflowRun.id == payload.workflow_run_id)
        .first()
    )

    if not workflow_run:
        raise HTTPException(status_code=404, detail="Workflow run not found")

    if payload.item_type == "ticket":
        item = (
            db.query(Ticket)
            .filter(
                Ticket.id == payload.item_id,
                Ticket.workflow_run_id == payload.workflow_run_id,
            )
            .first()
        )
    elif payload.item_type == "reply":
        item = (
            db.query(CustomerReply)
            .filter(
                CustomerReply.id == payload.item_id,
                CustomerReply.workflow_run_id == payload.workflow_run_id,
            )
            .first()
        )
    else:
        # Incident actions remain management-only: record the human decision
        # without executing the action or changing incident state.
        existing_incident_approval = (
            db.query(ApprovalDecision)
            .filter(
                ApprovalDecision.workflow_run_id == payload.workflow_run_id,
                ApprovalDecision.item_type == "incident_action",
                ApprovalDecision.item_id == payload.item_id,
                ApprovalDecision.decision == "pending",
            )
            .first()
        )
        item = None

    if payload.item_type == "incident_action" and not existing_incident_approval:
        raise HTTPException(status_code=404, detail="Approval item not found")
    if payload.item_type != "incident_action" and not item:
        raise HTTPException(status_code=404, detail="Approval item not found")

    approval_decision = (
        db.query(ApprovalDecision)
        .filter(
            ApprovalDecision.workflow_run_id == payload.workflow_run_id,
            ApprovalDecision.item_type == payload.item_type,
            ApprovalDecision.item_id == payload.item_id,
            ApprovalDecision.decision == "pending",
        )
        .order_by(ApprovalDecision.id.desc())
        .first()
    )
    if approval_decision:
        approval_decision.decision = decision
        approval_decision.reviewer_note = payload.reviewer_note
        approval_decision.created_at = datetime.utcnow()
    else:
        approval_decision = ApprovalDecision(
            workflow_run_id=payload.workflow_run_id,
            item_type=payload.item_type,
            item_id=payload.item_id,
            decision=decision,
            reviewer_note=payload.reviewer_note,
        )

    if item is not None:
        item.status = decision
    db.add(approval_decision)
    db.commit()
    db.refresh(approval_decision)

    return {
        "id": approval_decision.id,
        "workflow_run_id": approval_decision.workflow_run_id,
        "item_type": approval_decision.item_type,
        "item_id": approval_decision.item_id,
        "decision": approval_decision.decision,
        "reviewer_note": approval_decision.reviewer_note,
        "created_at": approval_decision.created_at,
    }


@router.post("/approve")
def approve_item(
    payload: ApprovalDecisionRequest,
    db: Session = Depends(get_db),
):
    return create_approval_decision(payload, "approved", db)


@router.post("/reject")
def reject_item(
    payload: ApprovalDecisionRequest,
    db: Session = Depends(get_db),
):
    return create_approval_decision(payload, "rejected", db)
