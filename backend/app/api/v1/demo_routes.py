from fastapi import APIRouter

from app.config import DEMO_MODE, MAX_WORKFLOWS_PER_HOUR


router = APIRouter()


@router.get("/status")
def get_demo_status():
    return {
        "demo_mode": DEMO_MODE,
        "protected_mutations": DEMO_MODE,
        "max_workflows_per_hour": MAX_WORKFLOWS_PER_HOUR,
    }
