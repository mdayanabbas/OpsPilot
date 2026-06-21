# OpsPilot Product and Engineering Specification

- **Product:** OpsPilot
- **Current release:** Hybrid Planner and Issue Normalization v1
- **Primary workflow:** Customer Feedback Triage
- **Document status:** Active specification
- **Last updated:** June 2026

## 1. Purpose

OpsPilot is a measured agentic AI system that converts unstructured customer feedback into safe, reviewable operational outputs.

The system is designed to help a startup or operations team consistently:

- identify concrete customer failures;
- normalize issues into a stable taxonomy;
- select an appropriate response plan;
- create engineering ticket drafts;
- create customer-reply drafts;
- evaluate output quality and risk;
- surface business context to founders;
- detect recurring incident patterns;
- require human approval for sensitive actions;
- record provider behavior, fallback usage, and execution outcomes.

OpsPilot is not intended to act as an unrestricted autonomous operator. LLM reasoning is advisory and is constrained by deterministic validation, tool allowlists, draft-only outputs, and human-review gates.

## 2. Specification Language

The terms below define requirement priority:

- **MUST:** Required for correct system behavior.
- **MUST NOT:** Prohibited behavior.
- **SHOULD:** Strongly recommended behavior; deviations require a documented reason.
- **SHOULD NOT:** Behavior that should generally be avoided.
- **MAY:** Optional or implementation-dependent behavior.

## 3. Product Goals

### 3.1 Primary Goals

OpsPilot MUST:

1. Accept raw customer-feedback text.
2. Distinguish actionable failures from praise, greetings, and vague input.
3. Normalize extracted issues into a stable supported taxonomy.
4. Recover actionable issues when LLM extraction returns no issues.
5. Use LLM assistance for planning when a configured provider is available.
6. Validate all LLM plans deterministically before accepting them.
7. Fall back to deterministic planning when provider execution, JSON parsing, or validation fails.
8. Require human review for sensitive issue categories and risk conditions.
9. Persist workflow decisions and generated artifacts for inspection.
10. Expose workflow behavior through UI and API surfaces.
11. Provide observable provider, fallback, retry, quality, and error information.
12. Prevent unapproved autonomous external side effects.

### 3.2 Secondary Goals

OpsPilot SHOULD:

- improve prioritization using memory from previous workflows;
- detect repeated issue clusters as incidents;
- produce concise founder-facing summaries;
- support cloud and local LLM providers through one abstraction;
- support repeatable benchmark evaluation;
- remain usable when all LLM providers are unavailable.

### 3.3 Non-Goals

The current release does not provide:

- production Jira, Linear, Zendesk, or other helpdesk mutations;
- automatic sending of customer replies;
- Slack, PagerDuty, or production incident escalation;
- unrestricted autonomous tool execution;
- payment processing;
- multi-tenant organization isolation;
- multi-user authentication and role-based access control;
- production secrets management;
- a production-grade migration framework;
- guaranteed semantic retrieval at production scale;
- general-purpose workflows outside customer-feedback triage.

## 4. Users and Roles

### 4.1 Operations User

An operations user submits feedback, observes workflow progress, reviews generated outputs, and checks provider recovery or failures.

### 4.2 Engineering or Support Reviewer

A reviewer inspects ticket and reply drafts and approves or rejects sensitive outputs.

### 4.3 Founder or Team Lead

A founder consumes summaries, risks, incident clusters, customer impact, and recommended actions.

### 4.4 Developer or Evaluator

A developer configures providers, runs benchmarks and tests, inspects logs, and extends nodes, taxonomies, or integrations.

## 5. System Boundaries

### 5.1 Inputs

The primary input is UTF-8 customer-feedback text submitted through:

- the workflow UI;
- `POST /api/v1/workflows/run`;
- optional IMAP email ingestion;
- benchmark cases.

The workflow API MUST reject input shorter than 10 characters through schema validation.

### 5.2 Outputs

Depending on workflow outcome, OpsPilot produces:

- normalized issue records;
- a planner decision;
- zero or more ticket drafts;
- zero or more customer-reply drafts;
- an evaluation result;
- a critic result;
- a founder summary;
- memory records;
- incident updates;
- approval records;
- execution and monitoring metadata.

### 5.3 External Dependencies

OpsPilot MAY depend on:

- Gemini through the Google Gen AI SDK;
- LM Studio through an OpenAI-compatible local endpoint;
- IMAP for optional email ingestion;
- SMTP for optional incident alerts.

Provider outages MUST NOT disable deterministic fallback behavior where such fallback is defined.

## 6. Primary Workflow

The current workflow type is:

```text
customer_feedback_triage
```

The logical processing sequence is:

```text
Input
-> Intent Routing
-> Issue Extraction
-> Issue Normalization and Validation
-> Memory Search
-> Hybrid Planning
-> Deterministic Plan Validation
-> Ticket and Reply Draft Generation
-> Evaluation
-> Founder Summary
-> Critic
-> Memory Persistence
-> Incident Detection
-> Human Approval where required
```

The implementation MAY persist steps at different points for observability, but accepted workflow behavior MUST conform to the contracts in this specification.

## 7. Workflow State Model

Supported workflow states are:

- `running`
- `needs_clarification`
- `completed`
- `failed`

### 7.1 Running

A newly submitted workflow MUST enter `running` before background processing completes.

### 7.2 Needs Clarification

A workflow MAY enter `needs_clarification` only when the system cannot safely infer a concrete actionable issue or the intent gate is extremely uncertain.

Actionable failures MUST NOT be routed to clarification solely because an upstream LLM requested clarification.

### 7.3 Completed

A workflow enters `completed` after required internal generation, evaluation, critic, memory, and incident-detection stages finish successfully.

`completed` does not mean a draft was externally delivered or approved.

### 7.4 Failed

A workflow enters `failed` when a required stage raises an unrecoverable error and no safe fallback can complete the stage.

Failure records SHOULD include an agent-step or tool-call error message.

## 8. Intent Routing Requirements

The intent router MUST return:

```json
{
  "workflow_type": "customer_feedback_triage",
  "confidence": 0.0,
  "reason": "string",
  "requires_clarification": false
}
```

Requirements:

1. `workflow_type` MUST resolve to `customer_feedback_triage` in the current release.
2. `confidence` MUST be normalized to the range `0.0` through `1.0`.
3. Empty or invalid input MUST produce a safe fallback result.
4. Provider and fallback metadata SHOULD be attached to the result.
5. Intent confidence below the configured threshold of `0.60` MAY trigger early clarification.
6. Intent output MUST NOT directly execute tools or external actions.

## 9. Issue Extraction Requirements

The extraction node MUST return a dictionary containing an `issues` list.

Each valid extracted issue SHOULD contain:

```json
{
  "title": "string",
  "category": "string",
  "severity": "low | medium | high",
  "customer": "string | null",
  "description": "string"
}
```

Requirements:

1. Extraction MUST ignore malformed non-dictionary issue entries.
2. Missing or blank title and description values MUST NOT become accepted normalized issues without repair.
3. Extraction SHOULD use provider structured JSON when available.
4. Provider, attempt, and fallback metadata SHOULD be preserved.
5. Extraction MAY return zero issues; the normalizer is responsible for determining whether this is correct.
6. Prompt-injection text MUST NOT grant new tools, change safety policy, or bypass downstream validation.

## 10. Issue Normalization and Validation

The normalizer is the authoritative boundary between probabilistic extraction and planning.

Required function:

```python
normalize_issue_result(input_text: str, extracted_result: dict) -> dict
```

Required result contract:

```json
{
  "issues": [],
  "requires_clarification": false,
  "normalization_applied": false,
  "normalization_reason": "string",
  "confidence": 0.0
}
```

Provider, attempt, and fallback metadata MAY also be returned for compatibility and observability.

### 10.1 Normalized Issue Contract

Every normalized issue MUST contain:

```json
{
  "title": "string",
  "category": "billing | auth | performance | ui | data | integration | notification | security | other",
  "severity": "low | medium | high",
  "customer": "string | null",
  "description": "string"
}
```

Title and description MUST be non-empty after normalization.

### 10.2 Supported Taxonomy

#### Billing

Billing includes failures involving:

- payment success without subscription activation;
- invoice state after payment;
- duplicate charges;
- pending refunds;
- checkout payment failures;
- pending or failed payments;
- subscription billing state.

#### Authentication

Authentication includes:

- inability to log in;
- password reset failures;
- immediately expired sessions;
- invalid credentials;
- locked accounts;
- inability to access an account.

#### Performance

Performance includes:

- slow pages;
- timeouts;
- freezing;
- long load time;
- hanging exports;
- crashes.

#### UI

UI includes:

- broken buttons;
- dropdown overlap;
- modals that do not open;
- page layout failures;
- broken visual controls.

#### Data

Data includes:

- missing records;
- incorrect report values;
- stale dashboard data;
- missing or inconsistent data.

#### Integration

Integration includes:

- webhook failures;
- CRM synchronization failures;
- third-party API failures;
- synchronization failures between named systems.

#### Notification

Notification includes:

- email not sent;
- OTP not received;
- delayed or missing notification delivery.

#### Security

Security includes:

- suspicious login;
- unauthorized access;
- permission failures;
- data exposure.

#### Other

`other` MAY be used for a concrete failure that cannot be mapped to a supported specific category.

### 10.3 Actionability Rules

The normalizer MUST treat an issue as actionable when a concrete failing behavior and meaningful affected system or customer impact can be inferred.

If extraction returns zero issues but input contains an actionable failure, the normalizer MUST synthesize a normalized issue.

If extraction requests clarification but the normalizer finds an actionable issue, the normalizer MUST:

- set `requires_clarification=false`;
- set `normalization_applied=true`;
- explain the override in `normalization_reason`;
- emit `[issue_normalizer] clarification_overridden=true`.

### 10.4 Clarification Rules

Clarification SHOULD be true only when one or more of the following conditions prevent safe action:

- no concrete failure exists;
- no customer or system impact exists;
- input is praise, greeting, or success-only feedback;
- category cannot be inferred and the description is too vague.

Actionable failure signals MUST override upstream clarification requests.

### 10.5 Normalizer Observability

The normalizer MUST log:

```text
[issue_normalizer] normalization_applied=true reason=...
```

It MUST log the clarification override when applicable.

## 11. Memory Requirements

Before planning an actionable issue, OpsPilot SHOULD search historical workflow memory using:

- normalized category;
- issue title;
- issue description;
- issue severity where useful.

Memory matches MAY:

- increase ticket priority;
- appear as source evidence;
- influence planner reasoning;
- inform founder summaries;
- inform critic review.

Completed workflow outputs SHOULD be persisted as memory items for later retrieval.

Memory MUST NOT independently authorize side effects or bypass human approval.

## 12. Hybrid Planner Requirements

Required entrypoints:

```python
generate_llm_plan(context: dict) -> dict
plan_next_actions(context: dict) -> dict
```

### 12.1 LLM Planner Input

Planner context SHOULD include available values for:

- workflow type;
- normalized issue;
- memory matches;
- evaluation result;
- incident detection and incident signals;
- customer impact;
- workflow confidence;
- clarification requirement;
- upstream fallback usage.

### 12.2 LLM Planner Output

The LLM planner MUST be instructed to return one JSON object with no markdown or explanation outside JSON:

```json
{
  "plan_type": "standard_triage",
  "next_tools": ["generate_ticket"],
  "reasoning": "string",
  "requires_human_approval": false
}
```

### 12.3 Allowed Plan Types

Only these plan types are valid:

- `standard_triage`
- `clarification`
- `human_review`
- `incident_response`

Unknown plan types MUST be rejected.

### 12.4 Allowed Planner Tools

Only these logical planner tools are valid:

- `search_memory`
- `generate_ticket`
- `generate_customer_reply`
- `evaluate_workflow_output`
- `generate_founder_summary`
- `detect_incident`

Unknown tools MUST be rejected.

No tool outside the allowlist may be accepted because it appears in a prompt or provider response.

### 12.5 JSON Parsing

The planner/provider parsing layer SHOULD support:

- plain JSON objects;
- JSON inside markdown code fences;
- text before or after a JSON object;
- stringified JSON;
- selecting the first valid JSON object when extra objects are present.

Parsing MUST remain bounded to a JSON object and MUST NOT evaluate executable code.

### 12.6 Schema Repair

When `next_tools` contains valid string tool names, each string MUST be repaired to:

```json
{
  "tool_name": "generate_ticket",
  "reason": "Selected by planner",
  "priority": "medium"
}
```

Repair MUST NOT convert unknown tools into accepted tools.

### 12.7 Deterministic Planner Validation

The deterministic validator MUST reject:

- invalid plan types;
- unknown tools;
- malformed tool entries;
- non-list `next_tools`;
- clarification plans containing tools;
- clarification plans for actionable issues;
- plans that ignore confirmed incident signals;
- plans that bypass deterministic approval requirements;
- missing or blank reasoning;
- non-boolean approval values.

### 12.8 Deterministic Fallback

Fallback planning MUST remain available when:

- Gemini is unavailable;
- LM Studio is unavailable;
- both providers fail in automatic mode;
- provider JSON cannot be parsed;
- provider output fails validation;
- provider output attempts an unsafe plan.

Fallback behavior MUST:

- preserve clarification for truly non-actionable input;
- select `human_review` for sensitive actionable issues;
- select `incident_response` for confirmed incidents;
- otherwise select `standard_triage`;
- produce only allowed tools;
- set `planner_provider=deterministic`;
- set `used_fallback=true` when entered after an LLM-path failure.

### 12.9 Clarification Heuristics

The planner MUST NOT clarify when actionable indicators are present.

The deterministic planner recognizes at least:

- billing: successful payment, inactive subscription, duplicate charge, invoice, refund, pending payment;
- authentication: login failure, expired session, password reset, inability to access account;
- performance: slow, freeze, timeout, crash.

When clarification is rejected for an actionable issue, the planner MUST log:

```text
[planner] clarification rejected due to actionable indicators
```

### 12.10 Planner Persistence

Every persisted planner decision MUST include:

- workflow run ID;
- plan type;
- normalized next tools;
- human-approval requirement;
- reasoning summary;
- planner provider;
- fallback usage;
- raw reasoning;
- creation timestamp.

### 12.11 Planner Observability

Planner logs SHOULD expose:

- selected provider;
- raw provider response;
- parse errors;
- validation success;
- validation failure reason;
- fallback reason.

Sensitive credentials MUST NOT be logged.

## 13. Provider Requirements

### 13.1 Supported Providers

Supported values for `LLM_PROVIDER` are:

- `gemini`
- `local`
- `auto`

Unknown values SHOULD resolve to a safe configured default.

### 13.2 Gemini

Gemini requires:

- `GEMINI_API_KEY`;
- `GEMINI_MODEL`, defaulting to `gemini-2.5-flash`.

Gemini structured responses SHOULD use an application/json response MIME type and response schema.

### 13.3 Local LM Studio

The local provider requires:

- `LOCAL_LLM_ENABLED=true`;
- `LOCAL_LLM_BASE_URL`;
- `LOCAL_LLM_API_KEY`;
- `LOCAL_LLM_MODEL`.

The endpoint MUST be OpenAI API compatible.

### 13.4 Automatic Mode

In `auto` mode, OpsPilot SHOULD:

1. attempt Gemini;
2. log Gemini failure without exposing secrets;
3. attempt the local provider;
4. mark local success as provider fallback;
5. raise a provider error if both attempts fail.

## 14. Tool Execution Safety

Planner tool validity and dynamic tool executability are separate concepts.

The dynamic executor v1 allowlist contains only:

- `search_memory`
- `evaluate_workflow_output`
- `generate_founder_summary`

Requirements:

1. Planned tools not in the dynamic executor allowlist MUST be skipped by dynamic execution.
2. Skipped tools MUST produce an explanatory result rather than execute.
3. Missing required context MUST cause a skip rather than a partial call.
4. Tool execution errors MUST be returned as structured errors.
5. The main workflow MAY call established internal generation stages directly.
6. OpsPilot MUST NOT autonomously send replies, create external tickets, or trigger external incident actions in v1.

## 15. Ticket Draft Requirements

An engineering ticket draft SHOULD contain:

- title;
- priority;
- owning team;
- normalized category;
- description;
- acceptance criteria;
- source evidence;
- approval requirement;
- draft status.

Memory evidence MAY increase priority and MUST be labeled as historical evidence rather than current fact.

Sensitive or human-review plans MUST mark generated tickets as requiring approval.

## 16. Customer Reply Requirements

A customer-reply draft SHOULD contain:

- customer when known;
- summarized issue;
- draft reply;
- risk level;
- risk reason;
- approval requirement;
- draft status.

The reply MUST NOT claim that an external fix, refund, payment, or deployment occurred unless supported by workflow context.

Replies remain drafts until human approval. The current system MUST NOT automatically deliver them to customers.

## 17. Evaluation Requirements

The evaluation result SHOULD include:

- `quality_score`;
- `reply_policy_compliance`;
- `ticket_completeness`;
- `unsupported_claim_rate`;
- `tool_recovery_success`;
- `requires_human_review`;
- `risks`.

Scores SHOULD be normalized consistently so monitoring and benchmark comparisons remain meaningful.

Evaluation MAY strengthen a human-review requirement but MUST NOT weaken a deterministic sensitive-category approval requirement.

## 18. Critic Requirements

The critic MUST inspect available:

- normalized issue;
- ticket draft;
- reply draft;
- evaluation result;
- planner decision;
- memory matches;
- provider and tool-call history;
- fallback state.

The critic SHOULD return:

- critic status;
- risk flags;
- quality notes;
- recommended action;
- manual-review requirement.

The critic is deterministic in the current release.

## 19. Founder Summary Requirements

The founder summary SHOULD communicate:

- what happened;
- who or what is affected;
- issue category and priority;
- output and approval status;
- major quality or policy risks;
- provider fallback or recovery information;
- useful memory context;
- recommended next actions.

The summary MUST NOT imply that a draft was sent or an external ticket was created.

## 20. Human Approval Requirements

Human approval MUST be required for:

- billing issues;
- authentication issues;
- refund issues;
- security issues;
- evaluation or reply outputs that explicitly request review;
- deterministic rules that identify equivalent sensitive signals.

Approval decisions apply to `ticket` or `reply` items and support:

- `approved`;
- `rejected`;
- optional reviewer note.

An approval decision MUST update the selected item's status and persist an audit record.

The approval API does not itself send or publish the item.

## 21. Incident Requirements

After a completed workflow, OpsPilot SHOULD run incident detection against recent workflow activity.

An active incident SHOULD expose:

- category;
- title and description;
- severity;
- workflow count;
- related workflow IDs;
- root-cause clusters;
- operational risks;
- recommended actions;
- first and last detection timestamps;
- active status.

Incident response planning MUST require human approval.

Incident email alerts MUST remain disabled unless explicitly configured.

## 22. Email Ingestion Requirements

Email ingestion is optional and MUST be disabled when `EMAIL_INGESTION_ENABLED=false`.

When enabled, the system MAY:

- preview unread IMAP emails;
- ingest a bounded number of unread emails;
- track processed emails;
- mark email as read when configured;
- expose worker status.

Configuration errors and IMAP authentication errors MUST return clear API errors.

Email credentials MUST NOT appear in API responses or logs.

## 23. Monitoring Requirements

Monitoring MUST expose enough information to distinguish logical tools from providers.

The summary SHOULD include:

- total workflows;
- completed, failed, and clarification workflow counts;
- total, successful, and failed tool calls;
- fallback count and rate;
- average quality score;
- average tool recovery score;
- provider breakdown;
- latest failed tool calls.

Provider labels SHOULD distinguish:

- Gemini;
- local LM Studio;
- provider fallback;
- deterministic execution;
- unknown legacy records.

## 24. Benchmark Requirements

Benchmark cases are JSON fixtures under `benchmarks/cases`.

The current suite includes cases for:

- billing;
- non-actionable feedback;
- refund risk;
- prompt injection;
- duplicate complaints;
- UI bugs;
- authentication/account access;
- vague feedback;
- payment risk;
- performance.

Benchmark execution SHOULD evaluate applicable expectations for:

- ticket creation;
- reply creation;
- human-review requirement;
- minimum quality score;
- issue/ticket category.

Each benchmark run MUST persist:

- total cases;
- passed cases;
- failed cases;
- pass rate;
- average quality score;
- per-case failures and workflow run ID where available.

## 25. API Requirements

All application endpoints use the `/api/v1` prefix.

### 25.1 Workflow API

- `GET /workflows`
- `POST /workflows/run`
- `GET /workflows/{workflow_run_id}`
- `GET /workflows/{workflow_run_id}/steps`
- `GET /workflows/{workflow_run_id}/tool-calls`
- `GET /workflows/{workflow_run_id}/memory`
- `GET /workflows/{workflow_run_id}/planner`
- `GET /workflows/{workflow_run_id}/critic`
- `GET /workflows/{workflow_run_id}/outputs`

### 25.2 Approval API

- `POST /approvals/approve`
- `POST /approvals/reject`

### 25.3 Monitoring API

- `GET /monitoring/summary`

### 25.4 Benchmark API

- `GET /benchmarks/cases`
- `POST /benchmarks/run`
- `GET /benchmarks/history`

### 25.5 Email API

- `GET /email-ingestion/preview`
- `POST /email-ingestion/run`
- `GET /email-ingestion/status`

### 25.6 Incident API

- `GET /incidents`
- `GET /incidents/alerts/status`

### 25.7 Health API

- `GET /health`

Existing response fields SHOULD remain backward compatible when additive metadata is introduced.

## 26. Frontend Requirements

The frontend MUST provide usable surfaces for:

- submitting a workflow;
- listing runs;
- viewing run details;
- viewing live run state;
- reviewing generated outputs;
- approving or rejecting drafts;
- monitoring provider and workflow health;
- viewing incidents;
- running and inspecting benchmarks.

The run-detail Planner Decision section MUST display:

- plan type;
- human-approval requirement;
- planned tool count;
- planner provider;
- fallback usage;
- reasoning source;
- reasoning summary;
- planned tools.

The UI MUST NOT imply that a draft was externally sent or created.

## 27. Persistence Requirements

The current implementation uses SQLite through SQLAlchemy.

Persisted entities include:

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
- benchmark runs and case results;
- agent execution traces.

Foreign-key-owned workflow data SHOULD be deleted when the parent workflow is deleted where cascade behavior is defined.

Schema changes in the current prototype MAY use additive startup migration logic. Production deployment SHOULD replace this with formal migrations.

## 28. Security and Privacy Requirements

1. API keys, email passwords, and secrets MUST be loaded from environment configuration.
2. Secrets MUST NOT be returned by application APIs.
3. Secrets MUST NOT be included in planner prompts unless strictly required, which current nodes do not require.
4. Prompt input MUST NOT expand tool or plan allowlists.
5. Structured output MUST be parsed as data and MUST NOT be evaluated as executable code.
6. Customer replies and tickets MUST remain drafts until reviewed.
7. Sensitive issue categories MUST require human approval.
8. CORS SHOULD be restricted to configured frontend origins.
9. Production deployments SHOULD add authentication, authorization, encryption, retention controls, and audit policy.

## 29. Reliability Requirements

1. Provider failure SHOULD produce a structured fallback rather than an unhandled exception when deterministic behavior exists.
2. Invalid JSON SHOULD be logged and repaired or rejected safely.
3. Unknown tools and plan types MUST fail closed.
4. Retry counts and fallback state SHOULD be recorded in tool-call metadata.
5. One provider's failure MUST NOT be mislabeled as another provider's success.
6. Workflow failure MUST be visible through status and error metadata.
7. Database initialization MUST create missing tables for local development.

## 30. Observability Requirements

Each tool-call record SHOULD include:

- workflow run ID;
- step name;
- logical tool name;
- provider;
- status;
- attempt number;
- fallback usage;
- latency when available;
- error message when applicable;
- creation timestamp.

Agent steps SHOULD provide concise input and output summaries without exposing secrets.

Logs SHOULD be useful for local diagnosis and SHOULD avoid credentials and excessive customer data.

## 31. Performance Requirements

The prototype does not define a strict production service-level objective.

For local use:

- workflow submission SHOULD return a created running workflow before background processing completes;
- list and detail APIs SHOULD remain responsive for a local SQLite dataset;
- provider time dominates generation latency and SHOULD be observable where possible;
- benchmark execution MAY run synchronously and is not intended for high concurrency.

Future production versions SHOULD define latency, throughput, availability, and retention SLOs.

## 32. Compatibility Requirements

1. Existing API routes MUST continue to function when normalization and planner metadata are added.
2. Additive response fields SHOULD have safe defaults for existing database rows.
3. Existing workflow history SHOULD remain readable after additive schema updates.
4. Frontend provider labels SHOULD tolerate legacy or unknown provider values.
5. Local development SHOULD work with either Gemini or LM Studio configuration.

## 33. Acceptance Criteria

### 33.1 Issue Normalization Acceptance

| Input | Expected category | Clarification | Expected behavior |
| --- | --- | --- | --- |
| `A customer made the payment successfully but the subscription is not yet active.` | `billing` | `false` | Create or normalize an actionable high-risk issue |
| `Payment succeeded but subscription remains disabled.` | `billing` | `false` | Override empty extraction or upstream clarification |
| `Users cannot login after password reset.` | `auth` | `false` | Create actionable auth issue requiring human review downstream |
| `Dashboard freezes while exporting reports.` | `performance` | `false` | Create actionable performance issue |
| `Webhook sync failed between Stripe and billing system.` | `integration` | `false` | Prefer failing integration over incidental billing terms |
| `Customer says everything works great.` | no issue | `true` | Do not create ticket or reply drafts |

### 33.2 Planner Acceptance

| Scenario | Expected plan | Human approval |
| --- | --- | --- |
| Actionable billing failure | `human_review` | `true` |
| Duplicate charge | `human_review` | `true` |
| Login failure | `human_review` | `true` |
| Dashboard freezing | `standard_triage` | `false`, unless another risk rule applies |
| Confirmed incident | `incident_response` | `true` |
| Vague non-actionable input | `clarification` | context dependent |

### 33.3 LLM Safety Acceptance

The planner MUST fall back deterministically when the LLM returns:

- invalid JSON;
- an unknown plan type;
- an unknown tool;
- a non-boolean approval value;
- blank reasoning;
- a clarification plan with tools;
- a plan that bypasses mandatory approval;
- a plan inconsistent with confirmed incident state.

### 33.4 Provider Acceptance

- Valid Gemini planner output MUST persist `planner_provider=gemini` and `used_fallback=false`.
- Valid primary local output MUST persist `planner_provider=local` and `used_fallback=false`.
- Valid local output after Gemini failure MUST record provider fallback.
- Deterministic planner fallback MUST persist `planner_provider=deterministic` and `used_fallback=true`.

### 33.5 Draft Safety Acceptance

- Generated tickets MUST remain internal drafts.
- Generated replies MUST remain internal drafts.
- Approval MUST update draft state but MUST NOT send or publish externally.
- Dynamic execution MUST skip tools outside its executor allowlist.

## 34. Regression Test Requirements

The repository SHOULD maintain automated regression coverage for:

- issue normalization taxonomy;
- actionability and clarification override;
- planner clarification heuristics;
- sensitive-category approval;
- provider JSON extraction and repair;
- plan and tool validation;
- deterministic fallback;
- benchmark expectations.

Current focused test commands:

```powershell
python -m unittest backend.tests.test_issue_normalization backend.tests.test_planner_heuristics
```

All discoverable backend unit tests:

```powershell
python -m unittest discover -s backend/tests -p "test_*.py"
```

Frontend production validation:

```powershell
cd frontend
npm run build
```

## 35. Configuration Requirements

Required provider-related environment variables MAY include:

```env
LLM_PROVIDER=gemini|local|auto
GEMINI_API_KEY=
GEMINI_MODEL=gemini-2.5-flash
LOCAL_LLM_ENABLED=false
LOCAL_LLM_BASE_URL=http://localhost:1234/v1
LOCAL_LLM_API_KEY=lm-studio
LOCAL_LLM_MODEL=
```

Optional email and alert variables include:

```env
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

Backend `.env` values override root `.env` values in the current configuration loader.

## 36. Known Constraints and Technical Debt

The current codebase has prototype constraints that future work SHOULD address:

- SQLite path depends on backend process working directory;
- startup schema updates are additive and not a full migration system;
- workflow orchestration is route-centered rather than expressed through a complete graph abstraction;
- latency metrics are not consistently captured from every provider call;
- benchmark checks cover selected outputs rather than every safety invariant;
- approval endpoints do not perform external publication;
- authentication and tenant boundaries are absent;
- local provider quality depends on the model loaded in LM Studio;
- taxonomy classification is deterministic and English-focused;
- incident and memory behavior require broader production-scale evaluation.

## 37. Future Roadmap

Future versions MAY add:

1. Formal workflow graph orchestration.
2. PostgreSQL and migration tooling.
3. Authentication, reviewer roles, and organization isolation.
4. Semantic memory and configurable retrieval strategies.
5. Organization-specific issue taxonomies.
6. Real ticketing and helpdesk integrations behind approval gates.
7. Controlled customer-reply delivery after approval.
8. Slack, PagerDuty, or email incident escalation policies.
9. Provider token, cost, latency, and quality analytics.
10. Expanded benchmark and adversarial safety suites.
11. Multilingual normalization and reply generation.
12. Deployment, container, CI, and production observability configuration.
13. Additional operational workflow types.

## 38. Definition of Done

A feature change affecting the workflow is complete only when:

1. Its behavior is represented in this specification or linked design documentation.
2. Existing APIs remain compatible or the breaking change is explicitly versioned.
3. Deterministic safety behavior is preserved.
4. Sensitive actions still require human approval.
5. Provider and fallback behavior remain observable.
6. Relevant regression tests are added or updated.
7. Backend code compiles and focused tests pass.
8. Frontend changes pass the production build when applicable.
9. README setup or usage instructions are updated when operator behavior changes.

## 39. Source of Truth

This document defines intended product behavior and engineering guarantees.

- `README.md` is the operator and contributor guide.
- `PROJECT_SPEC.md` is the behavioral product and engineering contract.
- Automated tests verify selected acceptance criteria.
- The running implementation remains authoritative for behavior not yet covered by this specification.

When implementation and specification disagree, the discrepancy SHOULD be resolved by updating code, tests, or this document rather than silently accepting drift.
