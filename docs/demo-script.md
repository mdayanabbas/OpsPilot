# OpsPilot Demo Script

Target length: 3-4 minutes.

## Goal

Show OpsPilot as a measured agentic AI workflow for customer feedback triage: not just generation, but evaluation, fallback observability, memory influence, approvals, and benchmark history.

## Demo Setup

Open these tabs before recording:

1. `http://localhost:3000/workflows/new`
2. `http://localhost:3000/runs`
3. `http://localhost:3000/benchmarks`
4. Optional: backend health at `http://localhost:8000/health`

Suggested prompt:

```text
Acme Corp says invoice still shows unpaid after successful payment. Support suspects billing sync failure and the customer is asking for an update.
```

## 3-4 Minute Script

### 0:00-0:25 - Opening Pitch

Show `/workflows/new`.

Say:

> This is OpsPilot, a measured agentic AI system for customer feedback triage. The goal is not just to generate text. OpsPilot turns raw feedback into tickets, customer replies, founder summaries, memory-backed context, benchmark evidence, and human approval decisions.

> I will run one customer complaint through the system and show how the workflow stays inspectable end to end.

### 0:25-0:55 - Start A Workflow Run

Paste the suggested prompt into the workflow input.

Click `Run OpsPilot Agent`.

Say:

> I am starting with messy customer feedback: an invoice still appears unpaid after successful payment. OpsPilot will classify the intent, extract the issue, generate a ticket, draft a reply, evaluate risk, check memory, and prepare everything for human review.

Wait for navigation to the run detail page.

### 0:55-1:35 - Timeline And Execution Insights

On `/runs/[runId]`, point to the top badges, metrics, Execution Insights, and Workflow Timeline.

Say:

> The run detail page is the control room. At the top we can see status, confidence, review state, and provider recovery information.

> Execution Insights are derived from tool calls. They show total tool calls, retries, fallback activation, failed calls, successful recoveries, and the primary provider. OpsPilot separates logical tool names from provider names, so the UI does not claim Groq was used when LM Studio or fallback handled the request.

> The timeline shows the workflow as stages instead of hiding everything inside one prompt.

### 1:35-2:15 - Generated Outputs And Approval Gate

Scroll to Generated Ticket and Customer Reply.

Say:

> OpsPilot generates a Linear-style engineering ticket with priority, category, team, description, acceptance criteria, and source evidence.

> It also drafts a customer reply. Because this is a customer-facing billing issue, the reply stays behind a human approval gate.

Click one approval action if safe for the demo.

Say:

> Approval decisions are stored separately, and approving or rejecting updates the ticket or reply status. There is no auth yet in this MVP, but the approval workflow is already modeled.

### 2:15-2:50 - Founder Summary And Memory Influence

Scroll to Founder Summary and Memory.

Say:

> The founder summary is deterministic. It mentions the issue category, affected customer, priority, review requirement, provider fallback, and memory context.

> Memory v1 searches similar past issues using category and keyword matching. When memory finds related issues, it can influence the output, not just display context. It raises priority by one level and adds source evidence like: similar past issue found in workflow number X.

> This is intentionally simple and transparent. No vector database yet, just deterministic memory influence that is easy to inspect.

### 2:50-3:35 - Benchmarks And History

Open `/benchmarks`.

Click `Run Benchmark` or show existing history.

Say:

> OpsPilot also includes a benchmark suite. These cases cover billing, refunds, prompt injection, duplicate complaints, UI bugs, auth issues, vague feedback, payment risk, and performance issues.

> Each benchmark run is persisted. The dashboard shows latest pass rate, improvement from the previous run, average quality trend, and previous benchmark runs.

> This turns product changes into measurable regressions or improvements instead of vibes.

### 3:35-4:00 - Close

Return to the run detail or benchmark history.

Say:

> OpsPilot is a compact example of production-minded agent design: staged workflow, provider fallback, memory, evaluation, approvals, and benchmark history.

> The roadmap is to add semantic memory, real ticketing and helpdesk integrations, reviewer auth, richer provider cost and latency tracking, and more workflow templates beyond customer feedback triage.

## Exact Demo Sequence

1. Open `/workflows/new`.
2. Paste the billing prompt.
3. Click `Run OpsPilot Agent`.
4. On run detail, show:
   - top status badges
   - Execution Insights
   - Workflow Timeline
   - Tool Calls provider badges
5. Scroll to:
   - Generated Ticket
   - Customer Reply
   - Approve/Reject controls
6. Show:
   - Founder Summary
   - Memory section
   - Evaluation metrics
7. Open `/benchmarks`.
8. Click `Run Benchmark`.
9. Show:
   - Benchmark History
   - Latest Pass Rate
   - Improvement
   - Avg Quality Trend
   - Case Outcomes

## Notes For Recording

- Keep the camera on the UI, not terminal logs.
- Avoid claiming integrations exist before they do.
- Emphasize that memory and founder summary are deterministic in this MVP.
- Mention that human approval is intentionally required before customer-facing action.
- If local provider is used, point out that the UI correctly says `LM Studio`.
