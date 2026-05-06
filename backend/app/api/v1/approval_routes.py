from fastapi import APIRouter

router = APIRouter()


@router.get("/")
def list_approvals():
    return {"message": "Approvals module coming soon"}