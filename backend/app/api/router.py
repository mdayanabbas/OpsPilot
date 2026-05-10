from fastapi import APIRouter

from app.api.v1 import approval_routes, benchmark_routes, email_routes, incident_routes, monitoring_routes, workflow_routes

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(workflow_routes.router, prefix="/workflows", tags=["workflows"])
api_router.include_router(benchmark_routes.router, prefix="/benchmarks", tags=["benchmarks"])
api_router.include_router(approval_routes.router, prefix="/approvals", tags=["approvals"])
api_router.include_router(monitoring_routes.router, prefix="/monitoring", tags=["monitoring"])
api_router.include_router(email_routes.router, prefix="/email-ingestion", tags=["email-ingestion"])
api_router.include_router(incident_routes.router, prefix="/incidents", tags=["incidents"])
