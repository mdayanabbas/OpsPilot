from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import CORS_ORIGINS
from app.database import Base, engine, ensure_database_schema
from app.api.router import api_router
from app.services.email_worker import start_email_worker

# Import models so SQLAlchemy registers them
from app import models  # noqa: F401

Base.metadata.create_all(bind=engine)
ensure_database_schema()

app = FastAPI(
    title="OpsPilot API",
    description="Measured agentic AI for customer feedback triage",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(CORS_ORIGINS),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.on_event("startup")
async def start_background_workers():
    start_email_worker()


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "opspilot-api"}
