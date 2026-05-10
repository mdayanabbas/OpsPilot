from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = "sqlite:///./opspilot.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

Base = declarative_base()


def ensure_database_schema():
    inspector = inspect(engine)
    if "tool_calls" not in inspector.get_table_names():
        return

    tool_call_columns = {
        column["name"] for column in inspector.get_columns("tool_calls")
    }

    if "provider" not in tool_call_columns:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "ALTER TABLE tool_calls "
                    "ADD COLUMN provider VARCHAR(50) NOT NULL DEFAULT 'gemini'"
                )
            )

    if "attempt" in tool_call_columns:
        with engine.begin() as connection:
            connection.execute(
                text("UPDATE tool_calls SET attempt = 1 WHERE attempt < 1")
            )


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
