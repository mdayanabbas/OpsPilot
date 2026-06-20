# OpsPilot

OpsPilot is a measured agentic AI system for customer-feedback triage. It turns unstructured customer reports into normalized issues, engineering tickets, customer-reply drafts, evaluation results, founder summaries, incident signals, and human-review decisions.

The project combines LLM-assisted reasoning with deterministic normalization, validation, allowlists, fallbacks, evaluation, and approval gates. Gemini and a local LM Studio-compatible endpoint are supported through one provider abstraction.

## Architecture Diagram

<img width="1724" height="7228" alt="fiaa" src="https://github.com/user-attachments/assets/76b8846d-c409-4eb3-bbdf-eb71ca26cc5f" />


## What OpsPilot Does

OpsPilot currently supports one primary workflow: `customer_feedback_triage`.

Given input such as:

> A customer made the payment successfully but the subscription is not yet active.

OpsPilot can:

1. Detect the workflow intent.
2. Extract one or more customer issues.
3. Normalize and validate the issue against a deterministic taxonomy.
4. Search memory for similar historical issues.
5. Ask the hybrid planner to select a safe plan.
6. Validate the LLM plan against deterministic plan and tool allowlists.
7. Fall back to deterministic planning if the provider, JSON parsing, or validation fails.
8. Generate a draft engineering ticket and customer reply.
9. Evaluate output quality and policy compliance.
10. Run a deterministic critic over the generated artifacts.
11. Generate a founder-facing summary, risks, and recommended actions.
12. Require human approval for sensitive workflows.
13. Persist workflow state, planner metadata, tool calls, memory, evaluations, and incidents.

## Core Principles

- **LLM-assisted, deterministically controlled:** LLMs may propose structured decisions, but deterministic code validates categories, plans, tools, and approval requirements.
- **Safe fallback:** Invalid JSON, unavailable providers, unknown tools, unsafe plans, and policy violations fall back to deterministic behavior.
- **No autonomous side effects:** Dynamic execution is restricted to a small internal allowlist. Ticket and reply outputs are drafts; external Jira, Slack, and automatic customer sending are not enabled.
- **Human approval for sensitive work:** Billing, authentication, refunds, and security-related issues are routed through human review.
- **Observable execution:** Provider, retries, fallback usage, tool calls, evaluation scores, failures, and planner reasoning metadata are recorded.
- **Reusable issue understanding:** Issue extraction is followed by a deterministic normalization and validation layer rather than relying on one-off phrase patches.

## End-to-End Workflow

### 1. Intent Routing

The intent router classifies input into the supported `customer_feedback_triage` workflow and returns confidence, reasoning, and whether clarification appears necessary.

Low-confidence or invalid intent output uses a safe clarification fallback.

### 2. Issue Extraction

The issue extraction node asks the configured LLM provider for structured issues. Each issue contains:

```json
{
  "title": "string",
  "category": "string",
  "severity": "low | medium | high",
  "customer": "string | null",
  "description": "string"
}
```

Extraction uses structured JSON, retry/fallback metadata, category rules, and deterministic cleanup.

### 3. Issue Normalization and Validation

`issue_normalization_node.py` runs immediately after extraction through:

```python
normalize_issue_result(input_text: str, extracted_result: dict) -> dict
```

It returns:

```json
{
  "issues": [],
  "requires_clarification": false,
  "normalization_applied": true,
  "normalization_reason": "created normalized issue from actionable input",
  "confidence": 0.9
}
```

Provider, retry, and fallback metadata from extraction are preserved for compatibility and monitoring.

Supported normalized categories:

- `billing`
- `auth`
- `performance`
- `ui`
- `data`
- `integration`
- `notification`
- `security`
- `other`

The deterministic taxonomy classifies issues by the failing system and customer impact. Examples include:

| Category | Example signals |
| --- | --- |
| Billing | successful payment with inactive subscription, unpaid invoice after payment, duplicate charge, pending refund, checkout failure |
| Auth | login failure, broken password reset, immediately expired session, invalid credentials, locked account |
| Performance | slow pages, timeout, freezing, long load time, hanging export, crash |
| UI | broken button, overlapping dropdown, modal not opening, layout issue |
| Data | missing records, wrong report values, stale dashboard data |
| Integration | webhook failure, CRM synchronization failure, third-party API failure |
| Notification | email not sent, OTP not received, delayed notification |
| Security | suspicious login, unauthorized access, permission issue, data exposure |

The normalizer can synthesize an issue from raw input when LLM extraction returns no issues but the text contains a concrete failure. It also overrides an extraction-level clarification decision when an actionable issue is present.

Clarification is reserved for inputs where no useful action can safely be inferred, including:

- no concrete failure;
- no customer impact;
- praise, greeting, or success-only feedback;
- an unknown category combined with a vague description.

Relevant logs:

```text
[issue_normalizer] normalization_applied=true reason=...
[issue_normalizer] clarification_overridden=true
```

### 4. Memory Search

Before planning, OpsPilot searches persisted workflow memory for related issues using category and issue text. Matches can:

- inform prioritization;
- increase ticket priority;
- appear as source evidence;
- inform founder summaries and critic decisions.

Completed workflows save ticket, reply, and evaluation context back into memory.

### 5. Hybrid LLM Planner

The planner combines LLM reasoning with deterministic safety validation.

Allowed plan types:

- `standard_triage`
- `clarification`
- `human_review`
- `incident_response`

Allowed planner tools:

- `search_memory`
- `generate_ticket`
- `generate_customer_reply`
- `evaluate_workflow_output`
- `generate_founder_summary`
- `detect_incident`

The planner prompt considers:

- issue category;
- memory matches;
- evaluation output;
- incident signals;
- customer impact;
- workflow confidence;
- upstream provider fallback risk.

Expected LLM response:

```json
{
  "plan_type": "human_review",
  "next_tools": [
    "generate_ticket",
    "generate_customer_reply",
    "evaluate_workflow_output",
    "generate_founder_summary"
  ],
  "reasoning": "The billing failure is actionable and requires approval.",
  "requires_human_approval": true
}
```

The JSON parser tolerates:

- markdown code fences;
- text before or after JSON;
- stringified JSON;
- multiple objects by selecting the first valid JSON object.

String tool names are repaired into the internal planner-tool shape:

```json
{
  "tool_name": "generate_ticket",
  "reason": "Selected by planner",
  "priority": "medium"
}
```

### 6. Deterministic Planner Validation

The validator rejects:

- unknown plan types;
- unknown tools;
- malformed tool entries;
- clarification plans that include tools;
- clarification for actionable issues;
- plans that ignore confirmed incident signals;
- plans that bypass mandatory human approval;
- missing or invalid reasoning and approval fields.

Actionable billing, authentication, and performance indicators prevent accidental clarification routing. Billing and authentication indicators also trigger human approval even if upstream categorization is weak.

On any provider, parsing, or validation failure, OpsPilot uses its deterministic planner. Planner logs include:

```text
[planner] selected provider=...
[planner] raw LLM planner response=...
[planner] JSON parse error=...
[planner] llm plan generated
[planner] validation passed
[planner] validation failure reason=...
[planner] fallback reason=...
[planner] fallback to deterministic planner: ...
[planner] clarification rejected due to actionable indicators
```

Planner decisions persist:

- `planner_provider`
- `used_fallback`
- `raw_reasoning`
- `plan_type`
- `next_tools`
- `requires_human_approval`
- `reasoning_summary`

### 7. Ticket and Reply Generation

For actionable workflows, OpsPilot creates:

- an engineering ticket draft with title, priority, team, category, description, acceptance criteria, source evidence, approval requirement, and status;
- a customer-reply draft with customer, issue, response, risk level, risk reason, approval requirement, and status.

These are internal drafts. OpsPilot does not create real Jira tickets or automatically send customer replies.

### 8. Evaluation and Critic

The evaluation layer records:

- quality score;
- reply policy compliance;
- ticket completeness;
- unsupported claim rate;
- tool recovery success;
- human-review requirement;
- detected risks.

The deterministic critic then inspects issue, ticket, reply, evaluation, planner decision, memory, tool calls, and fallback state. It records status, risk flags, quality notes, recommended action, and manual-review requirement.

### 9. Founder Summary

OpsPilot produces a founder-facing summary that includes the issue, customer impact, ticket and reply outcome, evaluation signals, provider recovery, memory context, risks, and recommended actions.

### 10. Incident Detection

Completed workflows are checked for repeated incident patterns. Active incidents expose:

- category and severity;
- affected workflow count and related workflow IDs;
- root-cause clusters;
- operational risks;
- recommended actions;
- first and last detection timestamps.

Email alerts are optional and disabled by default.

### 11. Human Approval

Tickets and replies can be approved or rejected through the approval API. The decision and reviewer note are persisted, and the selected draft status is updated.

## Provider Strategy

### Gemini

Gemini uses the Google Gen AI SDK with structured JSON response schemas.

```env
LLM_PROVIDER=gemini
GEMINI_API_KEY=your_api_key
GEMINI_MODEL=gemini-2.5-flash
```

### Local LM Studio

The local provider uses an OpenAI-compatible endpoint.

```env
LLM_PROVIDER=local
LOCAL_LLM_ENABLED=true
LOCAL_LLM_BASE_URL=http://localhost:1234/v1
LOCAL_LLM_API_KEY=lm-studio
LOCAL_LLM_MODEL=your-loaded-model-id
```

### Automatic Provider Fallback

Use `auto` to try Gemini first and then LM Studio:

```env
LLM_PROVIDER=auto
GEMINI_API_KEY=your_api_key
LOCAL_LLM_ENABLED=true
LOCAL_LLM_BASE_URL=http://localhost:1234/v1
LOCAL_LLM_API_KEY=lm-studio
LOCAL_LLM_MODEL=your-loaded-model-id
```

If both providers fail, nodes use their deterministic safe fallback where available.

## Safety Model

OpsPilot currently uses several complementary controls:

1. Structured response schemas for LLM nodes.
2. Tolerant but bounded JSON extraction.
3. Deterministic issue normalization and taxonomy classification.
4. Plan-type and tool allowlists.
5. Mandatory human approval for sensitive categories.
6. Clarification rejection for known actionable failures.
7. A restricted dynamic executor allowlist.
8. Output evaluation and deterministic criticism.
9. Draft-only ticket and reply persistence.
10. Provider, fallback, retry, and error observability.

The dynamic executor currently permits only:

- `search_memory`
- `evaluate_workflow_output`
- `generate_founder_summary`

Other planned tools are skipped by dynamic execution v1. The main workflow still invokes its established internal generation stages directly.

## Technology Stack

### Backend

- Python
- FastAPI
- SQLAlchemy
- SQLite
- Pydantic
- Google Gen AI SDK
- OpenAI-compatible local LLM client
- ChromaDB and sentence-transformer dependencies for memory-related capabilities
- Pytest and `unittest`-compatible regression tests

### Frontend

- Next.js 16
- React 19
- TypeScript
- Tailwind CSS 4

## Repository Structure

```text
OpsPilot/
|-- backend/
|   |-- app/
|   |   |-- agents/
|   |   |   |-- nodes/          # intent, extraction, normalization, planner, generators, evaluation, critic
|   |   |   |-- tools/          # tool registry
|   |   |   `-- executor.py     # restricted dynamic tool execution
|   |   |-- api/v1/             # workflow, approval, benchmark, monitoring, email, incident routes
|   |   |-- models/             # SQLAlchemy persistence models
|   |   |-- schemas/            # Pydantic API schemas
|   |   |-- services/           # providers, memory, incidents, email, benchmarks
|   |   |-- config.py
|   |   |-- database.py
|   |   `-- main.py
|   |-- tests/                   # planner and normalization regression tests
|   |-- debug_llm_planner.py     # direct planner debug entrypoint
|   `-- requirements.txt
|-- frontend/
|   |-- app/                     # Next.js routes
|   |-- components/              # workflow, output, approval, benchmark UI
|   `-- package.json
|-- benchmarks/                  # benchmark cases/data
|-- docs/                        # demo and supporting documentation
|-- .env.example
`-- README.md
```

## Local Setup

### Prerequisites

- Python 3.11 or newer recommended
- Node.js 20 or newer recommended
- npm
- One of:
  - a Gemini API key; or
  - LM Studio running an OpenAI-compatible local server

### 1. Clone and Enter the Repository

```powershell
git clone <repository-url>
cd OpsPilot
```

### 2. Configure the Backend Environment

Create `backend/.env` from the example:

```powershell
Copy-Item backend\.env.example backend\.env
```

Add the provider settings described in [Provider Strategy](#provider-strategy). Configuration is loaded from the repository `.env` first and `backend/.env` second; backend values override root values.

### 3. Install Backend Dependencies

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Start the Backend

Run from `backend/` so the SQLite database is created at `backend/opspilot.db`:

```powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Useful backend URLs:

- API health: `http://localhost:8000/health`
- Swagger UI: `http://localhost:8000/docs`
- OpenAPI JSON: `http://localhost:8000/openapi.json`

SQLAlchemy creates missing tables at startup. `ensure_database_schema()` applies the small additive SQLite migrations currently required by the project.

### 5. Install Frontend Dependencies

Open a second terminal:

```powershell
cd frontend
npm install
```

The frontend defaults to `http://localhost:8000`. To override it, create `frontend/.env.local`:

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

### 6. Start the Frontend

```powershell
npm run dev
```

Open `http://localhost:3000`.

## Running a Workflow

### Through the UI

1. Open `http://localhost:3000/workflows/new`.
2. Enter customer feedback.
3. Submit the workflow.
4. Open the run detail page to inspect timeline, planner decision, provider, fallback state, reasoning source, tools, drafts, evaluation, critic output, and approvals.

### Through the API

```powershell
$body = @{
  input_text = "A customer made the payment successfully but the subscription is not yet active."
} | ConvertTo-Json

Invoke-RestMethod `
  -Method Post `
  -Uri http://localhost:8000/api/v1/workflows/run `
  -ContentType "application/json" `
  -Body $body
```

The input must contain at least 10 characters.

## API Overview

All application APIs are prefixed with `/api/v1`.

### Workflows

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/workflows` | List workflow runs and summarized status |
| `POST` | `/workflows/run` | Create and execute a customer-feedback workflow |
| `GET` | `/workflows/{id}` | Retrieve one workflow run |
| `GET` | `/workflows/{id}/steps` | Retrieve agent-step timeline |
| `GET` | `/workflows/{id}/tool-calls` | Retrieve provider and tool-call records |
| `GET` | `/workflows/{id}/memory` | Retrieve related or saved memory |
| `GET` | `/workflows/{id}/planner` | Retrieve the latest planner decision |
| `GET` | `/workflows/{id}/critic` | Retrieve the latest critic result |
| `GET` | `/workflows/{id}/outputs` | Retrieve tickets, replies, summary, and evaluation |

### Approvals

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `POST` | `/approvals/approve` | Approve a draft ticket or reply |
| `POST` | `/approvals/reject` | Reject a draft ticket or reply |

Approval request shape:

```json
{
  "workflow_run_id": 1,
  "item_type": "ticket",
  "item_id": 1,
  "reviewer_note": "Reviewed and approved."
}
```

### Monitoring

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/monitoring/summary` | Workflow counts, tool success/failure, fallback rate, quality, recovery, and provider breakdown |

### Benchmarks

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/benchmarks/cases` | List benchmark cases |
| `POST` | `/benchmarks/run` | Run the benchmark suite |
| `GET` | `/benchmarks/history` | Retrieve benchmark history |

### Email Ingestion

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/email-ingestion/preview` | Preview unread emails without processing |
| `POST` | `/email-ingestion/run` | Ingest a bounded number of unread emails |
| `GET` | `/email-ingestion/status` | Inspect background worker status |

### Incidents

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/incidents` | List active detected incidents |
| `GET` | `/incidents/alerts/status` | Inspect incident-alert configuration |

## Email Ingestion Configuration

Email ingestion is optional.

```env
EMAIL_INGESTION_ENABLED=false
EMAIL_IMAP_HOST=imap.gmail.com
EMAIL_IMAP_PORT=993
EMAIL_USERNAME=
EMAIL_APP_PASSWORD=
EMAIL_MARK_AS_READ=false
```

When enabled, the background email worker starts with the FastAPI application. Use an application-specific password rather than a primary account password.

## Incident Alert Configuration

Incident email alerts are also optional and disabled by default:

```env
ALERT_EMAIL_ENABLED=false
ALERT_EMAIL_FROM=
ALERT_EMAIL_TO=
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
```

## Frontend Areas

- **Home:** project entry surface.
- **New Workflow:** submit customer feedback.
- **Runs:** browse workflow history.
- **Run Detail:** inspect workflow status, planner decision, provider recovery, planned tools, timeline, generated outputs, evaluation, memory, critic result, and approvals.
- **Live Run:** focused live workflow status and provider activity.
- **Monitoring:** workflow health, fallback usage, provider breakdown, and failures.
- **Incidents:** active incident clusters and recommended actions.
- **Benchmarks:** benchmark cases, execution, metrics, and history.

The Planner Decision section displays:

- plan type;
- human-approval requirement;
- planned tool count;
- planner provider;
- fallback usage;
- reasoning source;
- reasoning summary;
- normalized planner tools.

## Persistence

OpsPilot uses SQLite through SQLAlchemy. The main persisted entities include:

- workflow runs;
- agent steps;
- tool calls;
- planner decisions;
- tickets;
- customer replies;
- founder summaries;
- evaluations;
- critic results;
- memory items;
- approval decisions;
- incidents;
- processed emails;
- benchmark runs;
- agent execution traces.

The database URL is currently fixed as:

```text
sqlite:///./opspilot.db
```

Because this path is relative, start the backend from the `backend` directory for consistent database placement.

## Testing

Run the regression tests from the repository root:

```powershell
python -m unittest backend.tests.test_issue_normalization backend.tests.test_planner_heuristics
```

The normalization suite covers:

- successful payment with inactive subscription;
- successful payment with disabled subscription;
- login failure after password reset;
- dashboard freezing during export;
- Stripe-to-billing webhook synchronization failure;
- success-only praise;
- clarification override for actionable input.

The planner suite covers:

- sensitive actionable billing routing;
- duplicate charge routing;
- performance routing without unnecessary approval;
- authentication routing with approval.

Run all backend tests discoverable by `unittest`:

```powershell
python -m unittest discover -s backend/tests -p "test_*.py"
```

Build the frontend:

```powershell
cd frontend
npm run build
```

## Planner Debug Script

Use the direct planner script to inspect provider output, parsing, validation, and fallback without running a complete workflow:

```powershell
cd backend
python debug_llm_planner.py
```

The script calls both `generate_llm_plan()` and `plan_next_actions()` with a representative context.

## Monitoring and Troubleshooting

### Planner Always Uses Deterministic Fallback

Check backend logs for:

- selected provider;
- raw provider response;
- JSON parse errors;
- validation failure reason;
- fallback reason.

Common causes:

- `GEMINI_API_KEY` is missing;
- `LOCAL_LLM_ENABLED` is false;
- LM Studio is not running;
- `LOCAL_LLM_MODEL` does not match the loaded model ID;
- Gemini or the local model returned an unknown tool or invalid plan type;
- the LLM attempted to bypass required human approval.

### LM Studio Connection Failure

Confirm:

1. LM Studio has a model loaded.
2. Its local server is running.
3. The endpoint matches `LOCAL_LLM_BASE_URL`.
4. The model ID matches `LOCAL_LLM_MODEL`.
5. `LOCAL_LLM_ENABLED=true`.

### Actionable Issue Goes to Clarification

Inspect issue-normalizer logs first. The normalizer should create or normalize a concrete issue and set `requires_clarification=false`. Then inspect planner logs to confirm whether an LLM clarification plan was rejected or deterministic fallback was activated.

### Frontend Cannot Reach Backend

Confirm:

- FastAPI is running on port `8000`;
- Next.js is running on port `3000`;
- `NEXT_PUBLIC_API_BASE_URL` is correct;
- requests originate from `localhost:3000` or `127.0.0.1:3000`, which are enabled by backend CORS.

### Database Appears Empty or Duplicated

Ensure the backend is always started from the same directory. The SQLite path is relative to the process working directory.

## Current Scope and Limitations

Implemented:

- customer-feedback workflow intent routing;
- structured issue extraction;
- deterministic issue normalization and taxonomy validation;
- hybrid Gemini/LM Studio planner;
- deterministic planner validation and fallback;
- memory search and persistence;
- ticket and reply draft generation;
- evaluation and deterministic critic;
- founder summary generation;
- human approval endpoints;
- provider and fallback monitoring;
- incident clustering and optional alerts;
- optional IMAP email ingestion;
- benchmark cases, execution, and history;
- workflow timeline and run-detail UI.

Not currently implemented as production integrations:

- real Jira or helpdesk ticket creation;
- automatic customer email delivery;
- Slack or PagerDuty delivery;
- multi-user authentication and authorization;
- organization-level tenant isolation;
- production database migrations;
- production secrets management;
- billing or payment processing;
- unrestricted autonomous tool execution.

## Roadmap

Potential next steps:

- semantic memory retrieval and stronger relevance scoring;
- production PostgreSQL and formal migration tooling;
- authenticated reviewer accounts and audit trails;
- real Jira/helpdesk integrations behind approval gates;
- richer incident clustering and escalation policies;
- provider cost, token, and latency accounting;
- additional workflow templates;
- expanded benchmark datasets for normalization and planner safety;
- configurable taxonomies per organization;
- deployment, container, and CI/CD configuration.

## License

See [LICENSE](LICENSE).
