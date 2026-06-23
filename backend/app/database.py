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
                    "ADD COLUMN provider VARCHAR(50) NOT NULL DEFAULT 'groq'"
                )
            )

    if "attempt" in tool_call_columns:
        with engine.begin() as connection:
            connection.execute(
                text("UPDATE tool_calls SET attempt = 1 WHERE attempt < 1")
            )

    # Normalize legacy primary-provider labels after the provider migration.
    with engine.begin() as connection:
        connection.execute(
            text(
                "UPDATE tool_calls SET provider = 'groq' "
                "WHERE provider = ('gem' || 'ini')"
            )
        )

    if "incidents" in inspector.get_table_names():
        incident_columns = {
            column["name"] for column in inspector.get_columns("incidents")
        }
        with engine.begin() as connection:
            if "root_cause_summary" not in incident_columns:
                connection.execute(text("ALTER TABLE incidents ADD COLUMN root_cause_summary TEXT"))
            if "operational_risks" not in incident_columns:
                connection.execute(text("ALTER TABLE incidents ADD COLUMN operational_risks TEXT"))
            if "recommended_actions" not in incident_columns:
                connection.execute(text("ALTER TABLE incidents ADD COLUMN recommended_actions TEXT"))

    if "planner_decisions" in inspector.get_table_names():
        planner_columns = {
            column["name"] for column in inspector.get_columns("planner_decisions")
        }
        with engine.begin() as connection:
            if "planner_provider" not in planner_columns:
                connection.execute(
                    text(
                        "ALTER TABLE planner_decisions "
                        "ADD COLUMN planner_provider VARCHAR(50) NOT NULL DEFAULT 'deterministic'"
                    )
                )
            if "used_fallback" not in planner_columns:
                connection.execute(
                    text(
                        "ALTER TABLE planner_decisions "
                        "ADD COLUMN used_fallback BOOLEAN NOT NULL DEFAULT 0"
                    )
                )
            if "raw_reasoning" not in planner_columns:
                connection.execute(
                    text(
                        "ALTER TABLE planner_decisions "
                        "ADD COLUMN raw_reasoning TEXT NOT NULL DEFAULT ''"
                    )
                )
            connection.execute(
                text(
                    "UPDATE planner_decisions SET planner_provider = 'groq' "
                    "WHERE planner_provider = ('gem' || 'ini')"
                )
            )

    if "benchmark_runs" in inspector.get_table_names():
        benchmark_columns = {
            column["name"] for column in inspector.get_columns("benchmark_runs")
        }
        regression_columns = {
            "suite_name": "VARCHAR(150) NOT NULL DEFAULT 'legacy'",
            "cases_run": "INTEGER NOT NULL DEFAULT 0",
            "avg_score": "FLOAT NOT NULL DEFAULT 0.0",
            "planner_accuracy": "FLOAT NOT NULL DEFAULT 0.0",
            "category_accuracy": "FLOAT NOT NULL DEFAULT 0.0",
            "priority_accuracy": "FLOAT NOT NULL DEFAULT 0.0",
            "critic_accuracy": "FLOAT NOT NULL DEFAULT 0.0",
        }
        with engine.begin() as connection:
            for column_name, definition in regression_columns.items():
                if column_name not in benchmark_columns:
                    connection.execute(
                        text(
                            f"ALTER TABLE benchmark_runs "
                            f"ADD COLUMN {column_name} {definition}"
                        )
                    )


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
