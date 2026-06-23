# OpsPilot

OpsPilot is an operations control system for turning customer feedback into structured, reviewable work. It routes intent, normalizes issues, plans tool usage, generates ticket and reply drafts, evaluates quality, detects operational incidents, and preserves a trace of every decision.

The project combines LLM-assisted reasoning with deterministic policies. Groq is the primary hosted provider, LM Studio is the optional local fallback, and safety-sensitive decisions remain governed by explicit normalization, priority, critic, approval, and tool-allowlist rules.

## What Is Implemented

- Customer-feedback workflow execution
- Deterministic issue normalization and taxonomy
- Groq-first planning with optional LM Studio fallback
- Central tool registry and dynamic tool execution
- Durable agent steps, tool calls, and execution traces
- Ticket and customer-reply generation with duplicate prevention
- Priority policy, output evaluation, and critic review
- Human approval queue, decisions, comments, filters, and timeline
- Workflow replay with persisted output diffs
- React Flow agent trace graph
- Incident detection, response planning, and read-only execution
- Deterministic benchmark regression engine and historical results
- Executive and operational monitoring dashboards
- Optional IMAP email ingestion and incident email alerts
- Demo API-key protection and workflow rate limiting
- SQLite local development and PostgreSQL/Neon production configuration
- Backend Docker deployment support

## System Architecture

```text
Customer input
    |
    v
Intent Router
    |
    v
Issue Extraction
    |
    v
Issue Normalization
    |
    v
Memory Search
    |
    v
Planner
    |
    v
Dynamic Tool Executor
    |-- Ticket Generation
    |-- Customer Reply
    |-- Evaluation
    |-- Founder Summary
    |-- Incident Detection
    v
Critic Review
    |
    v
Human Approval / Operational Monitoring
```

Every workflow persists its major decisions and outputs so the run can be inspected, replayed, compared, benchmarked, and represented as a trace graph.

## Workflow Pipeline

### Intent routing

The router classifies incoming text and decides whether it belongs to the customer-feedback workflow. Provider errors are recorded and can fall back to safe deterministic behavior.

### Issue extraction and normalization

Extraction creates structured issue candidates. The normalization node then applies a deterministic taxonomy:

- `billing`
- `auth`
- `performance`
- `ui`
- `data`
- `integration`
- `notification`
- `security`
- `other`

Normalization can create an actionable issue even when extraction missed one. It can also override an unnecessary clarification decision. Praise-only, success-only, non-actionable, or uncategorizable messages remain clarification cases.

Priority normalization raises sensitive billing, authentication, security, and severe performance issues according to deterministic rules before ticket persistence.

### Planning

The planner selects a plan type and `next_tools`. Groq is the primary provider. LM Studio can be enabled as a local fallback, followed by a deterministic planner when provider execution or validation fails.

Planner output is validated against known tools and safety requirements. Billing, authentication, security, refund, payment, and subscription cases preserve human-review requirements.

### Dynamic tool execution

Planner-selected tools execute through the centralized registry. Dynamic executor v2 currently allows:

- `search_memory`
- `generate_ticket`
- `generate_customer_reply`
- `evaluate_workflow_output`
- `generate_founder_summary`
- `detect_incident`

Every selected tool receives an `executed`, `skipped`, or `error` trace. Existing workflow generation remains available as fallback, and ticket/reply duplicate prevention ensures each output is persisted once.

### Evaluation and critic

Evaluation measures output quality and review requirements. The deterministic critic warns on sensitive billing, authentication, and security cases, or when provider/fallback failures increase operational risk. Straightforward performance cases can pass unless execution quality requires review.

### Approval center

Tickets and replies that require human review appear in a centralized approval workspace. Reviewers can approve, reject, and comment without changing the underlying agent workflow contract.

### Incident response

Incident detection groups operational issue spikes. Each incident can receive a read-only response plan:

- `billing_incident`
- `auth_incident`
- `performance_incident`
- `general_incident`

Incident execution v1 allows only `search_memory` and `generate_founder_summary`. It does not send email automatically and does not change incident status.

### Workflow replay

Replay is observational rather than deterministic. It reruns the original input against the current prompts, providers, memory, and policies, then compares workflow status, type, confidence, ticket fields, reply risk, evaluation score, critic status, and planner plan type.

### Benchmark regression

The regression engine executes reusable benchmark cases and deterministically compares actual workflow outputs with expectations for category, plan type, priority, approval, workflow status, and critic status. Historical runs preserve average score and per-policy accuracy.

## Technology Stack

### Backend

- Python 3.12
- FastAPI
- SQLAlchemy
- SQLite for local development
- PostgreSQL/Neon for production
- Psycopg 2 (`psycopg2-binary`)
- Groq through an OpenAI-compatible client
- LM Studio as an optional local OpenAI-compatible provider
- ChromaDB-backed memory components

### Frontend

- Next.js 16
- React 19
- TypeScript
- Tailwind CSS 4
- React Flow

## Repository Structure

```text
OpsPilot/
|-- backend/
|   |-- app/
|   |   |-- agents/              # nodes, planner, executor, tools
|   |   |-- api/v1/              # FastAPI route modules
|   |   |-- models/              # SQLAlchemy persistence models
|   |   |-- schemas/             # API schemas
|   |   `-- services/            # replay, incidents, approvals, benchmarks
|   |-- tests/                    # deterministic regression tests
|   |-- Dockerfile
|   |-- .dockerignore
|   |-- .env.example
|   `-- requirements.txt
|-- frontend/
|   |-- app/                      # App Router pages
|   |-- components/               # dashboards, trace graph, approvals
|   |-- lib/                      # shared frontend API configuration
|   |-- .env.example
|   `-- package.json
|-- benchmarks/                   # benchmark and regression datasets
|-- docs/
|-- .env.example
`-- README.md
```

## Local Development

### Prerequisites

- Python 3.11 or newer
- Node.js 20 or newer
- npm
- A Groq API key, LM Studio, or both

### Backend setup

From the repository root:

```powershell
Copy-Item backend\.env.example backend\.env
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Configure `backend/.env`:

```env
DATABASE_URL=sqlite:///./opspilot.db

LLM_PROVIDER=groq
GROQ_API_KEY=your-groq-api-key
GROQ_BASE_URL=https://api.groq.com/openai/v1
GROQ_MODEL=llama-3.3-70b-versatile

LOCAL_LLM_ENABLED=true
LOCAL_LLM_BASE_URL=http://localhost:1234/v1
LOCAL_LLM_API_KEY=lm-studio
LOCAL_LLM_MODEL=your-loaded-lm-studio-model-id

DEMO_MODE=false
DEMO_API_KEY=
MAX_WORKFLOWS_PER_HOUR=20

EMAIL_INGESTION_ENABLED=false
EMAIL_IMAP_HOST=imap.gmail.com
EMAIL_IMAP_PORT=993
EMAIL_USERNAME=
EMAIL_APP_PASSWORD=
EMAIL_MARK_AS_READ=false

ALERT_EMAIL_ENABLED=false
ALERT_EMAIL_FROM=
ALERT_EMAIL_TO=
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
```

Start FastAPI from `backend/`:

```powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Useful URLs:

- Health: `http://localhost:8000/health`
- Swagger: `http://localhost:8000/docs`
- OpenAPI: `http://localhost:8000/openapi.json`

### Frontend setup

Open another terminal from the repository root:

```powershell
cd frontend
npm install
Copy-Item .env.example .env.local
```

Configure `frontend/.env.local`:

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
NEXT_PUBLIC_DEMO_API_KEY=
```

When backend demo mode is enabled, `NEXT_PUBLIC_DEMO_API_KEY` must match `DEMO_API_KEY`. Restart or rebuild Next.js after changing public environment variables.

Start the frontend:

```powershell
npm run dev
```

Open `http://localhost:3000`.

## Running a Workflow

### From the UI

1. Open `http://localhost:3000/workflows/new`.
2. Enter customer feedback.
3. Select **Run OpsPilot Agent**.
4. Watch the live run page.
5. Open run details for the graph, tools, outputs, critic, approvals, and replay.

Example input:

```text
A customer made the payment successfully but the subscription is not yet active.
```

### From the API

With demo mode disabled:

```powershell
$body = @{ input_text = "Customer was charged twice." } | ConvertTo-Json

Invoke-RestMethod `
  -Method Post `
  -Uri http://localhost:8000/api/v1/workflows/run `
  -ContentType "application/json" `
  -Body $body
```

With demo mode enabled:

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri http://localhost:8000/api/v1/workflows/run `
  -Headers @{ "X-Demo-Api-Key" = "your-demo-key" } `
  -ContentType "application/json" `
  -Body $body
```

## Demo API Protection

Demo mode protects expensive or state-changing public operations while keeping read-only GET endpoints public.

```env
DEMO_MODE=true
DEMO_API_KEY=use-a-long-random-value
MAX_WORKFLOWS_PER_HOUR=20
```

Protected mutations include workflow creation, email ingestion, benchmark execution, regression execution, workflow replay, approval decisions, and incident-plan execution. Workflow creation is limited by an in-memory hourly rate limiter.

Requests must send:

```http
X-Demo-Api-Key: your-demo-key
```

Important: a `NEXT_PUBLIC_*` frontend variable is visible in the browser bundle. The demo key prevents casual or accidental abuse; it is not a substitute for user authentication, authorization, a gateway-level rate limiter, or a server-side proxy.

Check runtime status at:

```text
GET /api/v1/demo/status
```

## Docker

Build from the repository root:

```powershell
docker build -t opspilot-backend ./backend
```

Run using the complete backend environment file:

```powershell
docker run --rm --name opspilot-backend `
  --env-file backend/.env `
  -p 8000:8000 `
  opspilot-backend
```

Docker receives only variables supplied through `--env-file` or `-e`. It does not automatically inherit repository environment files.

### Docker with local SQLite persistence

```powershell
docker run --rm --name opspilot-backend `
  --env-file backend/.env `
  -e DATABASE_URL=sqlite:////data/opspilot.db `
  -v opspilot-data:/data `
  -p 8000:8000 `
  opspilot-backend
```

Without the named volume, SQLite data stored inside a removed container is lost.

### Docker with LM Studio on the host

`localhost` inside Docker refers to the container. Use Docker's host alias:

```powershell
docker run --rm --name opspilot-backend `
  --env-file backend/.env `
  -e LOCAL_LLM_BASE_URL=http://host.docker.internal:1234/v1 `
  -p 8000:8000 `
  opspilot-backend
```

## Neon PostgreSQL

Create a Neon project and copy its pooled connection string. Use the SQLAlchemy Psycopg 2 scheme:

```env
DATABASE_URL=postgresql+psycopg2://USER:PASSWORD@YOUR-NEON-POOLER-HOST/neondb?sslmode=require
```

Keep this value in `backend/.env` locally and in the deployment platform's secret manager in production. Do not commit it.

Run Docker with Neon:

```powershell
docker run --rm --name opspilot-backend `
  --env-file backend/.env `
  -p 8000:8000 `
  opspilot-backend
```

No SQLite volume is needed when `DATABASE_URL` points to Neon. On first startup, SQLAlchemy creates missing tables. Existing local SQLite data is not automatically migrated to Neon.

Verify persistence:

1. Start the backend with the Neon URL.
2. Create a workflow.
3. Restart the container.
4. Confirm the workflow remains visible.
5. In Neon SQL Editor, run:

```sql
SELECT COUNT(*) FROM workflow_runs;
```

Production schema evolution should use formal migrations. Automatic additive schema guards are intended only for existing local SQLite databases.

## Deployment

### Render

1. Create a Docker Web Service from the repository.
2. Set the service root directory to `backend`.
3. Add `DATABASE_URL`, Groq variables, demo variables, and optional email settings.
4. Use `/health` as the health-check path.
5. Render supplies `PORT`; the Docker command reads it automatically.

### Railway

1. Create a service from the repository and set its root directory to `backend`.
2. Add Neon or Railway PostgreSQL and configure `DATABASE_URL`.
3. Add Groq, demo, and optional provider/email variables.
4. Generate a public domain.
5. Verify `/health` and `/docs`.

### Frontend deployment

Configure:

```env
NEXT_PUBLIC_API_BASE_URL=https://your-backend.example.com
NEXT_PUBLIC_DEMO_API_KEY=your-demo-key
```

Next.js public environment variables are embedded at build time. Rebuild the frontend after changing them. Add the deployed frontend origin to the backend CORS allowlist before production traffic.

## API Reference

All application endpoints use the `/api/v1` prefix.

### Workflows

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/workflows` | List workflow runs |
| `POST` | `/workflows/run` | Start a workflow |
| `GET` | `/workflows/{id}` | Get workflow metadata |
| `GET` | `/workflows/{id}/steps` | Get agent steps |
| `GET` | `/workflows/{id}/tool-calls` | Get provider/tool calls |
| `GET` | `/workflows/{id}/agent-executions` | Get dynamic executor traces |
| `GET` | `/workflows/{id}/memory` | Get related memory |
| `GET` | `/workflows/{id}/planner` | Get planner decision |
| `GET` | `/workflows/{id}/critic` | Get critic result |
| `GET` | `/workflows/{id}/outputs` | Get tickets, replies, summary, and evaluation |
| `POST` | `/workflows/{id}/replay` | Replay a workflow |
| `GET` | `/workflows/{id}/replays` | List replay history |
| `GET` | `/workflows/replays/{replay_id}` | Get one replay and diff |

### Approvals

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/approvals/queue` | Pending, approved, and rejected queue |
| `GET` | `/approvals/stats` | Approval counts |
| `POST` | `/approvals/approve` | Approve a ticket or reply |
| `POST` | `/approvals/reject` | Reject a ticket or reply |
| `POST` | `/approvals/comment` | Add a reviewer comment |
| `GET` | `/approvals/{id}/comments` | Get approval comments |

### Incidents

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/incidents` | List incidents |
| `GET` | `/incidents/alerts/status` | Inspect alert configuration |
| `GET` | `/incidents/{id}/response-plan` | Get or create response plan |
| `POST` | `/incidents/{id}/execute` | Execute allowlisted read-only tools |
| `GET` | `/incidents/{id}/executions` | List incident execution traces |

### Benchmarks

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/benchmarks/cases` | List legacy benchmark cases |
| `POST` | `/benchmarks/run` | Run benchmark suite |
| `GET` | `/benchmarks/history` | Get benchmark history |
| `GET` | `/benchmarks/regression-cases` | List deterministic regression cases |
| `POST` | `/benchmarks/run-regression` | Run regression suite |
| `GET` | `/benchmarks/regression-history` | Get historical regression runs |
| `GET` | `/benchmarks/results` | Get case-level regression results |

### Monitoring and demo

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/monitoring/summary` | Operational workflow metrics |
| `GET` | `/monitoring/executive-summary` | Executive control-center summary |
| `GET` | `/demo/status` | Demo protection status |

### Email ingestion

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/email-ingestion/preview` | Preview unread messages |
| `POST` | `/email-ingestion/run` | Ingest unread messages |
| `GET` | `/email-ingestion/status` | Get worker status |

## Frontend Areas

- `/` — overview dashboard
- `/dashboard` — executive operations control center
- `/workflows/new` — workflow launcher
- `/runs` — workflow history
- `/runs/live/{id}` — live execution view
- `/runs/{id}` — complete run details, React Flow trace, outputs, execution, and replay
- `/approvals` — human approval center
- `/benchmarks` — benchmark and regression dashboard
- `/monitoring` — provider and operational health
- `/incidents` — incident intelligence, plans, and execution traces

## Testing

Run the backend test suite from the repository root with an active Python environment:

```powershell
python -m unittest discover -s backend/tests -p "test_*.py"
```

Important deterministic suites cover:

- issue normalization and priority policy
- planner heuristics and safety validation
- critic policy
- dynamic tool execution
- incident response planning and execution
- workflow replay comparison
- benchmark evaluation
- demo guard authentication and rate limiting

Validate the frontend:

```powershell
cd frontend
npx tsc --noEmit
npm run build
```

## Production Smoke Test

1. Check `GET /health`.
2. Check `GET /api/v1/demo/status`.
3. Create a workflow using the demo header.
4. Confirm intent, planner, tool calls, agent executions, outputs, evaluation, and critic appear.
5. Confirm sensitive ticket/reply outputs appear in the approval queue.
6. Replay the workflow and inspect the diff.
7. Execute a regression run and inspect accuracy metrics.
8. Open an incident, inspect its response plan, and execute read-only tools.
9. Restart the backend and confirm workflow history persists in Neon.

## Troubleshooting

### `X-Demo-Api-Key header is required`

- Confirm backend `DEMO_MODE` and `DEMO_API_KEY`.
- Confirm frontend `NEXT_PUBLIC_DEMO_API_KEY` matches.
- Restart the frontend after changing `.env.local`.
- Recreate Docker containers after changing `backend/.env`.

### `GROQ_API_KEY is not configured`

Docker does not automatically load host `.env` files. Confirm the file passed to `--env-file` contains a non-empty `GROQ_API_KEY`, then recreate the container.

### LM Studio works on the host but not in Docker

Use:

```env
LOCAL_LLM_BASE_URL=http://host.docker.internal:1234/v1
```

Ensure LM Studio has a model loaded and its API server is running.

### Run details return 404 after replacing a container

The old workflow was stored in ephemeral container SQLite. Use Neon or mount a persistent SQLite volume. Missing run-detail records render as not found rather than crashing the frontend.

### Neon connection failure

- Confirm the full connection URL is present in the container.
- Use `postgresql+psycopg2://`.
- Preserve `sslmode=require`.
- URL-encode special characters in manually created passwords.
- Confirm `psycopg2-binary` is installed.

### Planner always falls back

Inspect backend logs for provider selection, validation errors, and fallback reasons. Confirm Groq credentials, LM Studio availability, loaded model ID, and tool names.

### Frontend cannot reach the backend

Confirm `NEXT_PUBLIC_API_BASE_URL`, backend port exposure, CORS configuration, and whether the frontend was rebuilt after environment changes.

## Safety and Limitations

- Customer replies and tickets are drafts, not direct external actions.
- Incident response execution is read-only in v1.
- Incident status is not changed automatically.
- Email/alert sending remains opt-in.
- Replay is observational, not exactly deterministic.
- In-memory demo rate limiting resets on process restart and is per backend process.
- A browser-visible demo key is not real user authentication.
- PostgreSQL schema evolution needs formal migrations before frequent production changes.
- Multi-user authentication, tenant isolation, and role-based authorization are not yet implemented.
- Real Jira/helpdesk, Slack, and PagerDuty delivery are not yet implemented.

## Recommended Next Steps

1. Complete Neon production verification.
2. Add Alembic database migrations.
3. Add configurable production CORS origins.
4. Replace browser-visible demo-key access with authenticated server-side sessions or a backend-for-frontend proxy.
5. Add gateway/distributed rate limiting.
6. Add CI for backend tests, frontend type checking, and Docker builds.
7. Add database backups and restore testing.
8. Add provider cost, token, and latency accounting.

## License

See [LICENSE](LICENSE).
