from fastapi import APIRouter

router = APIRouter()


@router.get("/")
def list_benchmarks():
    return {"message": "Benchmarks module coming soon"}