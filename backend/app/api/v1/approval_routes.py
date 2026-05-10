from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.approval import ApprovalDecision
from app.models.reply import CustomerReply
from app.models.ticket import Ticket
from app.models.workflow import WorkflowRun

router = APIRouter()


class ApprovalDecisionRequest(BaseModel):
    workflow_run_id: int
    item_type: Literal["ticket", "reply"]
    item_id: int
    reviewer_note: str | None = None


@router.get("/")
def list_approvals():
    return {"message": "Approvals module coming soon"}


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
    else:
        item = (
            db.query(CustomerReply)
            .filter(
                CustomerReply.id == payload.item_id,
                CustomerReply.workflow_run_id == payload.workflow_run_id,
            )
            .first()
        )

    if not item:
        raise HTTPException(status_code=404, detail="Approval item not found")

    approval_decision = ApprovalDecision(
        workflow_run_id=payload.workflow_run_id,
        item_type=payload.item_type,
        item_id=payload.item_id,
        decision=decision,
        reviewer_note=payload.reviewer_note,
    )

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
