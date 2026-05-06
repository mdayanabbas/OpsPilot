from fastapi import APIRouter

from app.api.v1 import workflow_routes, benchmark_routes, approval_routes

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(workflow_routes.router, prefix="/workflows", tags=["workflows"])
api_router.include_router(benchmark_routes.router, prefix="/benchmarks", tags=["benchmarks"])
api_router.include_router(approval_routes.router, prefix="/approvals", tags=["approvals"])