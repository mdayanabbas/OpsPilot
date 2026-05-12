# OpsPilot Project Spec

## Problem

Customer feedback arrives as unstructured text across support channels, founder notes, sales calls, and bug reports. Teams often lose time deciding whether the feedback is actionable, what team owns it, how risky the customer response is, and whether similar issues have happened before.

OpsPilot solves this by turning raw feedback into a measured, reviewable workflow with generated outputs, memory, evaluation, provider observability, and human approval.

## Users

- Founders who need an executive summary of customer issues and operational risk.
- Support leads who need safe customer replies and escalation guidance.
- Product managers who need repeatable issue triage and prioritization.
- Engineers who need clear tickets with source evidence and acceptance criteria.
- AI builders who need a concrete example of measured agentic workflows.

## Core Workflow

```text
Customer feedback
  -> intent routing
  -> issue extraction
  -> memory search
  -> ticket generation
  -> customer reply generation
  -> evaluation
  -> founder summary
  -> human approval
  -> benchmark and memory persistence
```

## MVP Scope

The MVP supports one workflow: Customer Feedback Triage.

Included:

- Create workflow run from free-form customer feedback.
- Classify intent and detect low-confidence inputs.
- Extract actionable issue category, severity, customer, and description.
- Search deterministic memory for similar past issues.
- Influence ticket priority when memory finds similar past issues.
- Generate ticket and customer reply drafts.
- Evaluate output quality, risk, policy compliance, and tool recovery.
- Generate deterministic founder summary.
- Record tool calls with logical tool name, provider, attempts, and fallback usage.
- Approve or reject generated tickets and replies.
- Persist benchmark run history and case results.
- Display workflow details, memory, execution insights, approvals, and benchmarks in the frontend.

## Non-Goals

- No production authentication or authorization yet.
- No real Jira, Linear, Slack, or email sending yet.
- No automatic customer communication.
- No ChromaDB/vector memory yet.
- No billing, tenancy, or multi-workspace permissions.
- No claim that generated output is final without human review.

## Backend Modules

- `backend/app/api/v1/workflow_routes.py`
  - Run creation, run details, outputs, tool calls, memory endpoint.

- `backend/app/api/v1/approval_routes.py`
  - Approve/reject generated tickets and replies.

- `backend/app/api/v1/benchmark_routes.py`
  - Benchmark cases, run execution, run history.

- `backend/app/agents/nodes/intent_router_node.py`
  - Intent classification and clarification handling.

- `backend/app/agents/nodes/issue_extraction_node.py`
  - Deterministic guards plus structured issue extraction.

- `backend/app/agents/nodes/ticket_generation_node.py`
  - Ticket generation and deterministic fallback.

- `backend/app/agents/nodes/reply_generation_node.py`
  - Customer reply draft generation and fallback.

- `backend/app/agents/nodes/evaluation_node.py`
  - Quality, compliance, completeness, unsupported claim, and recovery scoring.

- `backend/app/agents/nodes/founder_summary_node.py`
  - Deterministic executive summary, risks, and recommended actions.

- `backend/app/services/gemini_service.py`
  - Provider selection across Gemini, local LM Studio, and auto fallback.

- `backend/app/services/memory_service.py`
  - Memory save/search with deterministic category and keyword matching.

- `backend/app/services/benchmark_service.py`
  - Benchmark case execution and persisted run history.

- `backend/app/models/`
  - Workflow runs, agent steps, tool calls, tickets, replies, evaluations, founder summaries, approvals, memory, benchmarks.

## Frontend Pages

- `/`
  - Main dashboard entry point.

- `/workflows/new`
  - Submit customer feedback and start a run.

- `/runs`
  - Browse workflow runs.

- `/runs/[runId]`
  - Inspect run details: timeline, execution insights, tool calls, ticket, reply, approvals, founder summary, memory, evaluation.

- `/benchmarks`
  - View benchmark case coverage, run the suite, inspect current results, and review historical benchmark trends.

## Benchmark Strategy

Benchmark cases are stored as JSON files under `benchmarks/cases`.

The suite checks expected behavior such as:

- whether a ticket should be created
- whether a reply should be created
- whether human review is required
- minimum quality score
- expected issue category

Each benchmark execution persists:

- a `BenchmarkRun` row with aggregate metrics
- one `BenchmarkCaseResult` row per case
- linked workflow run IDs for traceability

The frontend displays:

- latest pass rate
- improvement from previous run
- average quality trend
- previous benchmark runs
- case-level pass/fail output

This makes quality visible over time and gives future changes a regression harness.
