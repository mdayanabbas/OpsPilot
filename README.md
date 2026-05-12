# OpsPilot

OpsPilot is a measured agentic AI system for customer feedback triage. It turns messy customer feedback into structured product signals: issues, engineering tickets, customer replies, founder summaries, benchmark evidence, memory-backed context, and human approval decisions.

It is built to show what a practical AI operations copilot looks like when reliability matters as much as generation quality.

## What OpsPilot Does

OpsPilot accepts raw customer feedback and runs a deterministic, inspectable workflow:

1. Detect workflow intent.
2. Extract actionable issues.
3. Generate an engineering ticket.
4. Draft a safe customer reply.
5. Evaluate output quality and risk.
6. Search memory for similar past issues.
7. Generate a founder-level summary.
8. Require human approval before final action.

The app is intentionally opinionated: every run has traceable steps, tool-call logs, provider/fallback metadata, benchmark coverage, and approval controls.

## Key Features

- Agent workflow timeline for each run.
- Generated ticket and customer reply cards.
- Human approval gate for ticket/reply approval or rejection.
- Provider tracking for Gemini, LM Studio/local, and fallback recovery.
- Execution insights: retries, failed calls, fallback activation, health state.
- Memory v1: deterministic memory search from past workflows.
- Memory influence: similar past issues can raise ticket priority and appear in source evidence.
- Founder summary generation with risk and action recommendations.
- Benchmark suite with persisted run history and trend cards.
- Premium dark dashboard UI built for demos and operational review.

## Architecture

```text
frontend/ Next.js app
  /workflows/new       submit customer feedback
  /runs                browse workflow runs
  /runs/[runId]        inspect timeline, outputs, approvals, memory, execution
  /benchmarks          run benchmark suite and inspect history

backend/ FastAPI app
  api/v1/workflow_routes.py     workflow execution and run inspection
  api/v1/approval_routes.py     approve/reject actions
  api/v1/benchmark_routes.py    benchmark execution/history
  agents/nodes/                 deterministic and LLM-backed workflow nodes
  services/                     Gemini/local provider, memory, benchmark logic
  models/                       SQLAlchemy persistence models

SQLite
  workflow runs, tickets, replies, evaluations, approvals,
  memory items, tool calls, benchmark runs, benchmark case results
```

## Tech Stack

- Backend: FastAPI, SQLAlchemy, SQLite, Pydantic.
- Frontend: Next.js, React, TypeScript, Tailwind CSS.
- AI providers: Gemini and LM Studio-compatible local OpenAI API.
- Evaluation: deterministic checks plus benchmark cases.
- Persistence: local SQLite database for fast iteration.

## AI Workflow

OpsPilot uses a staged workflow rather than one large prompt:

1. Intent routing classifies whether the input is customer feedback triage.
2. Issue extraction identifies actionable product/customer problems.
3. Ticket generation creates a Linear-style engineering ticket.
4. Reply generation drafts a customer-safe response.
5. Evaluation scores quality, completeness, policy compliance, unsupported claims, and tool recovery.
6. Founder summary converts operational details into an executive readout.

The workflow is designed so every stage can be tested, logged, benchmarked, and improved independently.

## Evaluation And Benchmarks

The benchmark suite lives in `benchmarks/cases` and covers billing, refunds, prompt injection, duplicate complaints, UI bugs, auth issues, vague feedback, payment risk, and performance complaints.

Each benchmark run records:

- total cases
- passed cases
- failed cases
- pass rate
- average quality score
- case-level failures
- linked workflow run IDs

The Benchmarks page shows persisted run history with trend cards for latest pass rate, improvement from the previous run, and average quality trend.

## Provider Fallback System

OpsPilot separates logical tool names from provider names.

- Logical tools: `intent_router`, `issue_extraction`, `ticket_generation`, `reply_generation`.
- Providers: `gemini`, `local`, `fallback`.
- UI labels local/fallback execution as `LM Studio`.

If fallback is used, the run detail page shows `Recovered via fallback` and includes fallback status in Execution Insights and founder risk notes.

## Memory Influence

Memory v1 stores workflow summaries from completed runs. Before generating a new ticket, OpsPilot searches memory by category and keyword overlap.

When similar past issues are found:

- ticket priority is increased by one level (`low -> medium`, `medium -> high`)
- ticket source evidence includes the similar workflow ID and title
- founder summary mentions the similar issue count and source workflow IDs
- the Memory section labels the run as `Memory influenced this run`

This is deterministic for now. No ChromaDB or embeddings are used yet.

## Human Approval Gate

Generated tickets and customer replies remain drafts until reviewed. The run detail page provides Approve and Reject actions for both item types.

Approval decisions are stored in `approval_decisions`, and the target ticket/reply status updates to `approved` or `rejected`.

## Screenshots

Add screenshots here before publishing:

- `[Screenshot placeholder: New workflow page]`
- `[Screenshot placeholder: Run detail timeline and execution insights]`
- `[Screenshot placeholder: Ticket/reply approval controls]`
- `[Screenshot placeholder: Memory influenced this run]`
- `[Screenshot placeholder: Benchmark history dashboard]`

## Local Setup

### Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

For local LM Studio mode, create `backend/.env`:

```env
LOCAL_LLM_ENABLED=true
LOCAL_LLM_BASE_URL=http://localhost:1234/v1
LOCAL_LLM_API_KEY=lm-studio
LOCAL_LLM_MODEL=llama-2-7b-chat
LLM_PROVIDER=local
```

For Gemini mode, add:

```env
GEMINI_API_KEY=your_key_here
LLM_PROVIDER=gemini
```

For automatic Gemini-to-local fallback:

```env
LLM_PROVIDER=auto
```

### Frontend

```powershell
cd frontend
npm install
npm run dev
```

Open:

- Frontend: `http://localhost:3000`
- Backend health: `http://localhost:8000/health`

## Demo Flow

1. Start the backend and frontend.
2. Open `/workflows/new`.
3. Submit a customer complaint such as:
   `Acme Corp says invoice still shows unpaid after successful payment. Support suspects billing sync failure.`
4. Open the generated run detail page.
5. Show timeline, execution insights, generated ticket, customer reply, founder summary, memory, and approvals.
6. Approve or reject the ticket/reply.
7. Open `/benchmarks`.
8. Run the benchmark suite and show history/trends.

## Future Roadmap

- ChromaDB/embedding-backed semantic memory.
- Real Jira/Linear ticket creation.
- Real helpdesk reply handoff.
- Slack alerting for high-risk runs.
- Multi-user auth and reviewer attribution.
- More benchmark dimensions and regression thresholds.
- Richer provider latency/cost tracking.
- Workflow templates beyond customer feedback triage.
