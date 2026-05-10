from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine, ensure_database_schema
from app.api.router import api_router

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
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "opspilot-api"}
