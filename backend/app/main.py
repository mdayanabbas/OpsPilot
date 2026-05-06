from fastapi import FastAPI

from app.database import Base, engine
from app.api.router import api_router

# Import models so SQLAlchemy registers them
from app import models  # noqa: F401

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="OpsPilot API",
    description="Measured agentic AI for customer feedback triage",
    version="0.1.0",
)

app.include_router(api_router)


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "opspilot-api"}