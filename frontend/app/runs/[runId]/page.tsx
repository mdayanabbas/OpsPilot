import type { ReactNode } from "react";
import { ApprovalActions } from "../../../components/approvals/ApprovalActions";
import { WorkflowReplayPanel } from "../../../components/replays/WorkflowReplayPanel";
import { AgentTraceFlow } from "../../../components/workflows/AgentTraceFlow";

type WorkflowRun = {
  id: number;
  input_text: string;
  status: string;
  workflow_type: string;
  confidence: number | null;
  created_at: string;
  updated_at: string;
};

type ToolCall = {
  id: number;
  workflow_run_id: number;
  step_name: string;
  tool_name: string;
  provider: string;
  status: string;
  attempt: number;
  latency_ms: number | null;
  error_message: string | null;
  fallback_used: boolean;
  created_at: string;
};

type Ticket = {
  id: number;
  title: string;
  priority: string;
  team: string | null;
  category: string | null;
  description: string;
  acceptance_criteria: string | null;
  source_evidence: string | null;
  requires_approval: boolean;
  status: string;
};

type CustomerReply = {
  id: number;
  customer: string | null;
  issue: string;
  draft_reply: string | null;
  risk_level: string;
  risk_reason: string | null;
  requires_approval: boolean;
  status: string;
};

type Evaluation = {
  id: number;
  quality_score: number | null;
  reply_policy_compliance: number | null;
  ticket_completeness: number | null;
  unsupported_claim_rate: number | null;
  tool_recovery_success: number | null;
  requires_human_review: boolean;
  risks: string | null;
};

type FounderSummary = {
  id: number;
  workflow_run_id: number;
  summary: string;
  risks: string | null;
  recommended_actions: string | null;
};

type MemoryItem = {
  id: number;
  workflow_run_id: number;
  item_type: string;
  title: string;
  category: string | null;
  content: string;
  relevance_score: number | null;
  created_at: string;
};

type CriticResult = {
  id: number;
  workflow_run_id: number;
  critic_status: "passed" | "warning" | "blocked" | string;
  risk_flags: string[];
  quality_notes: string[];
  recommended_action: string;
  requires_manual_review: boolean;
  created_at: string;
};

type PlannerTool = {
  tool_name: string;
  reason: string;
  priority: "low" | "medium" | "high" | string;
};

type PlannerDecision = {
  id: number;
  workflow_run_id: number;
  plan_type: string;
  next_tools: PlannerTool[];
  requires_human_approval: boolean;
  reasoning_summary: string;
  planner_provider: string;
  used_fallback: boolean;
  raw_reasoning: string;
  created_at: string;
};

type AgentExecutionTrace = {
  id: number;
  workflow_run_id: number;
  planner_decision_id: number;
  tool_name: string;
  status: "executed" | "skipped" | "error" | string;
  result_summary: string | null;
  error_message: string | null;
  created_at: string;
};

type WorkflowReplayGraphItem = {
  replay_workflow_run_id: number;
  changed: boolean;
  diff_summary: string;
};

type WorkflowOutputs = {
  workflow_run: WorkflowRun;
  tickets: Ticket[];
  customer_replies: CustomerReply[];
  founder_summary: FounderSummary | null;
  evaluation: Evaluation | null;
};

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

const TIMELINE_STEPS = [
  ["intent_router", "Intent", "Classify workflow"],
  ["issue_extraction", "Extract", "Extract structured issue"],
  ["planner", "Planner", "Choose next tools"],
  ["ticket_generation", "Ticket", "Create engineering task"],
  ["reply_generation", "Reply", "Draft customer response"],
  ["evaluation", "Evaluate", "Score quality and risk"],
  ["critic", "Critic", "Review generated outputs"],
] as const;

async function fetchJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, { cache: "no-store" });

  if (!response.ok) {
    throw new Error(`Request failed: ${response.status} ${response.statusText}`);
  }

  return response.json() as Promise<T>;
}

async function fetchOptionalJson<T>(path: string): Promise<T | null> {
  const response = await fetch(`${API_BASE_URL}${path}`, { cache: "no-store" });

  if (response.status === 404) {
    return null;
  }

  if (!response.ok) {
    throw new Error(`Request failed: ${response.status} ${response.statusText}`);
  }

  return response.json() as Promise<T>;
}

function cx(...classes: Array<string | false | null | undefined>) {
  return classes.filter(Boolean).join(" ");
}

function titleize(value: string | null | undefined) {
  if (!value) return "Unknown";
  return value.replaceAll("_", " ");
}

function percent(value: number | null | undefined) {
  if (value === null || value === undefined) return "n/a";
  return `${Math.round(value * 100)}%`;
}

function dateTime(value: string) {
  return new Intl.DateTimeFormat("en", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function toneClass(tone: string) {
  if (tone === "completed" || tone === "executed" || tone === "success" || tone === "low" || tone === "healthy" || tone === "passed") {
    return "border-emerald-400/25 bg-emerald-400/10 text-emerald-200 shadow-emerald-950/30";
  }

  if (tone === "failed" || tone === "error" || tone === "high" || tone === "degraded" || tone === "blocked") {
    return "border-rose-400/25 bg-rose-400/10 text-rose-200 shadow-rose-950/30";
  }

  if (tone === "needs_clarification" || tone === "medium" || tone === "skipped" || tone === "recovered" || tone === "warning") {
    return "border-amber-400/25 bg-amber-400/10 text-amber-200 shadow-amber-950/30";
  }

  return "border-slate-500/30 bg-slate-500/10 text-slate-300 shadow-slate-950/20";
}

function timelineDotClass(state: string) {
  if (state === "completed" || state === "success") {
    return "border-emerald-300/60 bg-emerald-400 text-emerald-950 shadow-emerald-400/30";
  }

  if (state === "failed") {
    return "border-rose-300/60 bg-rose-400 text-rose-950 shadow-rose-400/30";
  }

  if (state === "skipped" || state === "needs_clarification") {
    return "border-amber-300/60 bg-amber-300 text-amber-950 shadow-amber-400/25";
  }

  return "border-white/15 bg-white/10 text-slate-400";
}

function timelineStatus(
  step: string,
  workflow: WorkflowRun,
  outputs: WorkflowOutputs,
  toolCalls: ToolCall[],
  criticResult?: CriticResult | null,
) {
  if (step === "critic" && criticResult) return "completed";
  if (step === "evaluation" && outputs.evaluation) return "completed";
  if (step === "ticket_generation" && outputs.tickets.length > 0) return "completed";
  if (step === "reply_generation" && outputs.customer_replies.length > 0) return "completed";

  const call = toolCalls.find((item) => item.step_name === step);
  if (call) return call.status === "success" ? "completed" : call.status;

  return workflow.status === "needs_clarification" ? "skipped" : "pending";
}

function metricToneClass(tone: string = "default") {
  if (tone === "healthy" || tone === "success" || tone === "passed") {
    return "border-emerald-300/20 bg-emerald-300/[0.07] shadow-emerald-950/20";
  }

  if (tone === "recovered" || tone === "medium" || tone === "warning") {
    return "border-amber-300/20 bg-amber-300/[0.07] shadow-amber-950/20";
  }

  if (tone === "failed" || tone === "degraded" || tone === "blocked") {
    return "border-rose-300/20 bg-rose-300/[0.07] shadow-rose-950/20";
  }

  return "border-white/10 bg-white/[0.045] shadow-black/15";
}

function providerLabel(provider: string | null | undefined, fallbackUsed = false) {
  if (provider === "deterministic") {
    return "Deterministic";
  }

  if (provider === "local" || provider === "fallback" || fallbackUsed) {
    return "LM Studio";
  }

  return "Groq";
}

function plannerReasoningSource(plannerDecision: PlannerDecision) {
  if (plannerDecision.raw_reasoning?.trim()) {
    return "LLM reasoning";
  }

  if (plannerDecision.used_fallback) {
    return "Deterministic fallback";
  }

  return "Deterministic rules";
}

function logicalToolLabel(toolName: string) {
  return titleize(
    toolName
      .replace(/^groq_/, "")
      .replace(/_generator$/, "")
      .replace(/_extractor$/, "")
      .replace(/_router$/, "_router"),
  );
}

function providerSummary(toolCalls: ToolCall[]) {
  const providers = new Set<string>();

  toolCalls.forEach((toolCall) => {
    providers.add(providerLabel(toolCall.provider, toolCall.fallback_used));
  });

  if (providers.size > 1) return "Mixed providers";
  return providers.values().next().value ?? "Groq";
}

function executionHealth(
  workflow: WorkflowRun,
  failedToolCalls: number,
  fallbackActivated: boolean,
  successfulRecoveries: number,
) {
  if (workflow.status === "failed") return "failed";
  if (failedToolCalls > 0 && successfulRecoveries > 0) return "recovered";
  if (failedToolCalls > 0) return "degraded";
  if (fallbackActivated && successfulRecoveries > 0) return "recovered";
  if (fallbackActivated) return "degraded";
  return "healthy";
}

function Badge({ children, tone = "default", className }: { children: ReactNode; tone?: string; className?: string }) {
  return (
    <span
      className={cx(
        "inline-flex items-center gap-1 rounded-full border px-2.5 py-1 text-xs font-semibold capitalize shadow-sm",
        toneClass(tone),
        className,
      )}
    >
      {children}
    </span>
  );
}

function Panel({
  title,
  eyebrow,
  children,
  className,
}: {
  title: string;
  eyebrow?: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section
      className={cx(
        "rounded-3xl border border-white/10 bg-slate-950/55 shadow-2xl shadow-black/25 backdrop-blur-xl",
        className,
      )}
    >
      <div className="border-b border-white/10 px-6 py-5">
        {eyebrow ? (
          <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">{eyebrow}</p>
        ) : null}
        <h2 className="mt-1 text-lg font-semibold tracking-tight text-white">{title}</h2>
      </div>
      <div className="p-6">{children}</div>
    </section>
  );
}

function MetricTile({ label, value, hint, tone = "default" }: { label: string; value: string; hint?: string; tone?: string }) {
  return (
    <div className={cx("rounded-3xl border p-5 shadow-xl", metricToneClass(tone))}>
      <div className="flex items-center gap-2">
        <span
          className={cx(
            "h-2 w-2 rounded-full",
            tone === "healthy" || tone === "success"
              ? "bg-emerald-300 shadow-[0_0_12px_rgba(110,231,183,0.55)]"
              : tone === "recovered" || tone === "medium"
                ? "bg-amber-300 shadow-[0_0_12px_rgba(252,211,77,0.5)]"
                : tone === "failed" || tone === "degraded"
                  ? "bg-rose-300 shadow-[0_0_12px_rgba(253,164,175,0.5)]"
                  : "bg-slate-500",
          )}
        />
        <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">{label}</p>
      </div>
      <p className="mt-3 text-2xl font-semibold tracking-tight text-white">{value}</p>
      {hint ? <p className="mt-2 text-xs text-slate-500">{hint}</p> : null}
    </div>
  );
}

function EmptyState({ children }: { children: ReactNode }) {
  return (
    <div className="rounded-2xl border border-dashed border-white/12 bg-white/[0.025] p-6 text-sm leading-6 text-slate-400">
      {children}
    </div>
  );
}

export default async function WorkflowRunDetailsPage({
  params,
}: {
  params: Promise<{ runId: string }>;
}) {
  const { runId } = await params;

  const [workflow, outputs, toolCalls, memoryItems, criticResult, plannerDecision, agentExecutions, replayHistory] = await Promise.all([
    fetchJson<WorkflowRun>(`/api/v1/workflows/${runId}`),
    fetchJson<WorkflowOutputs>(`/api/v1/workflows/${runId}/outputs`),
    fetchJson<ToolCall[]>(`/api/v1/workflows/${runId}/tool-calls`),
    fetchJson<MemoryItem[]>(`/api/v1/workflows/${runId}/memory`),
    fetchOptionalJson<CriticResult>(`/api/v1/workflows/${runId}/critic`),
    fetchOptionalJson<PlannerDecision>(`/api/v1/workflows/${runId}/planner`),
    fetchJson<AgentExecutionTrace[]>(`/api/v1/workflows/${runId}/agent-executions`),
    fetchJson<WorkflowReplayGraphItem[]>(`/api/v1/workflows/${runId}/replays`),
  ]);

  const ticket = outputs.tickets[0];
  const reply = outputs.customer_replies[0];
  const evaluation = outputs.evaluation;
  const founderSummary = outputs.founder_summary;
  const fallbackUsed = toolCalls.some((toolCall) => toolCall.fallback_used);
  const totalRetries = toolCalls.reduce((total, toolCall) => total + Math.max(toolCall.attempt - 1, 0), 0);
  const failedToolCalls = toolCalls.filter((toolCall) => toolCall.status === "failed").length;
  const successfulRecoveries = toolCalls.filter(
    (toolCall) => toolCall.fallback_used && toolCall.status === "success",
  ).length;
  const primaryProvider = providerSummary(toolCalls);
  const health = executionHealth(workflow, failedToolCalls, fallbackUsed, successfulRecoveries);
  const sortedMemoryItems = [...memoryItems].sort(
    (left, right) => (right.relevance_score ?? 0) - (left.relevance_score ?? 0),
  );
  const memoryInfluencedRun = memoryItems.some((memoryItem) => memoryItem.workflow_run_id !== workflow.id);
  const humanReviewRequired = Boolean(evaluation?.requires_human_review || reply?.requires_approval);

  return (
    <main className="min-h-screen bg-[#05070b] text-slate-100">
      <div className="fixed inset-0 bg-[linear-gradient(180deg,rgba(15,23,42,0.72),rgba(2,6,23,0.96)),radial-gradient(circle_at_20%_0%,rgba(14,165,233,0.18),transparent_34%),radial-gradient(circle_at_90%_4%,rgba(168,85,247,0.16),transparent_30%)]" />
      <div className="fixed inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-sky-300/40 to-transparent" />

      <div className="relative flex min-h-screen">
        <div className="flex w-full flex-col">
          <div className="mx-auto flex w-full max-w-7xl flex-col gap-6 px-4 py-5 sm:px-6 lg:px-8 lg:py-8">
            <header className="overflow-hidden rounded-3xl border border-white/10 bg-slate-950/70 shadow-2xl shadow-black/30 backdrop-blur-xl">
              <div className="border-b border-white/10 bg-white/[0.035] px-6 py-4">
                <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                  <div className="flex items-center gap-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-2xl border border-white/10 bg-white/[0.06] text-sm font-bold text-sky-200 lg:hidden">
                      OP
                    </div>
                    <div>
                      <p className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-500">Workflow Run</p>
                      <h1 className="mt-1 text-2xl font-semibold tracking-tight text-white sm:text-3xl">Run #{workflow.id}</h1>
                    </div>
                  </div>

                  <div className="flex flex-wrap gap-2">
                    <Badge tone={workflow.status}>{titleize(workflow.status)}</Badge>
                    <Badge tone="default">{percent(workflow.confidence)} confidence</Badge>
                    <Badge tone={humanReviewRequired ? "medium" : "success"}>
                      {humanReviewRequired ? "human review" : "no review needed"}
                    </Badge>
                  </div>
                </div>
              </div>

              <div className="grid gap-6 px-6 py-6 xl:grid-cols-[1.4fr_0.6fr]">
                <div>
                  <p className="max-w-4xl text-sm leading-7 text-slate-300">{workflow.input_text}</p>
                  <div className="mt-5 flex flex-wrap gap-2">
                    <Badge tone="default">{titleize(workflow.workflow_type)}</Badge>
                    <Badge tone={fallbackUsed ? "medium" : "success"}>
                      {fallbackUsed ? "tool fallback used" : "primary tools"}
                    </Badge>
                  </div>
                </div>

                <div className="grid gap-3 rounded-3xl border border-white/10 bg-black/20 p-4 text-sm">
                  <div className="flex items-center justify-between gap-4">
                    <span className="text-slate-500">Created</span>
                    <span className="font-medium text-slate-200">{dateTime(workflow.created_at)}</span>
                  </div>
                  <div className="flex items-center justify-between gap-4">
                    <span className="text-slate-500">Updated</span>
                    <span className="font-medium text-slate-200">{dateTime(workflow.updated_at)}</span>
                  </div>
                </div>
              </div>
            </header>

            <AgentTraceFlow
              key={replayHistory[0]?.replay_workflow_run_id ?? "no-replay"}
              workflow={workflow}
              plannerDecision={plannerDecision}
              agentExecutions={agentExecutions}
              toolCalls={toolCalls}
              outputs={outputs}
              critic={criticResult}
              replayHistory={replayHistory}
            />

            <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
              <MetricTile label="Status" value={titleize(workflow.status)} />
              <MetricTile label="Confidence" value={percent(workflow.confidence)} />
              <MetricTile label="Tickets" value={String(outputs.tickets.length)} />
              <MetricTile label="Replies" value={String(outputs.customer_replies.length)} />
              <MetricTile label="Tool Fallback" value={fallbackUsed ? "Used" : "None"} />
            </section>

            <Panel title="Execution Insights" eyebrow="Runtime reliability">
              <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <div className="flex flex-wrap gap-2">
                  <Badge tone={health}>execution {health}</Badge>
                  <Badge tone={primaryProvider === "Mixed providers" ? "medium" : "success"}>
                    {primaryProvider}
                  </Badge>
                </div>
                <p className="text-xs leading-5 text-slate-500">
                  Derived from recorded provider activity for this workflow run.
                </p>
              </div>

              <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                <MetricTile
                  label="Total Tool Calls"
                  value={String(toolCalls.length)}
                  hint="Provider operations recorded"
                  tone={health}
                />
                <MetricTile
                  label="Total Retries"
                  value={String(totalRetries)}
                  hint="Extra attempts beyond first pass"
                  tone={totalRetries > 0 ? "recovered" : "healthy"}
                />
                <MetricTile
                  label="Fallback Activated"
                  value={fallbackUsed ? "Yes" : "No"}
                  hint={fallbackUsed ? "Secondary provider was used" : "Primary provider completed the run"}
                  tone={fallbackUsed ? "recovered" : "healthy"}
                />
                <MetricTile
                  label="Failed Tool Calls"
                  value={String(failedToolCalls)}
                  hint={failedToolCalls > 0 ? "Failures detected in execution log" : "No failed calls recorded"}
                  tone={failedToolCalls > 0 ? "failed" : "healthy"}
                />
                <MetricTile
                  label="Successful Recoveries"
                  value={String(successfulRecoveries)}
                  hint={successfulRecoveries > 0 ? "Fallback calls completed successfully" : "No recovery path needed"}
                  tone={successfulRecoveries > 0 ? "recovered" : "healthy"}
                />
                <MetricTile
                  label="Primary Provider"
                  value={primaryProvider}
                  hint="Provider recorded separately from tool name"
                  tone={primaryProvider === "Mixed providers" ? "recovered" : "success"}
                />
              </div>
            </Panel>

            <Panel title="Planner Decision" eyebrow="Agent orchestration">
              {plannerDecision ? (
                <div className="space-y-5">
                  <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                    <MetricTile label="Plan Type" value={titleize(plannerDecision.plan_type)} />
                    <MetricTile
                      label="Human Approval"
                      value={plannerDecision.requires_human_approval ? "Required" : "Not required"}
                      tone={plannerDecision.requires_human_approval ? "medium" : "healthy"}
                    />
                    <MetricTile
                      label="Planned Tools"
                      value={String(plannerDecision.next_tools.length)}
                      hint={dateTime(plannerDecision.created_at)}
                    />
                    <MetricTile
                      label="Planner Provider"
                      value={providerLabel(plannerDecision.planner_provider, plannerDecision.used_fallback)}
                      tone={plannerDecision.used_fallback ? "medium" : "healthy"}
                    />
                    <MetricTile
                      label="Fallback Used"
                      value={plannerDecision.used_fallback ? "Yes" : "No"}
                      tone={plannerDecision.used_fallback ? "medium" : "healthy"}
                    />
                    <MetricTile
                      label="Reasoning Source"
                      value={plannerReasoningSource(plannerDecision)}
                      tone={plannerDecision.raw_reasoning ? "healthy" : "default"}
                    />
                  </div>

                  <div className="rounded-3xl border border-sky-300/15 bg-sky-300/[0.055] p-5 shadow-xl shadow-sky-950/15">
                    <p className="text-xs font-semibold uppercase tracking-[0.18em] text-sky-200/70">Reasoning Summary</p>
                    <p className="mt-3 text-sm leading-7 text-slate-200">{plannerDecision.reasoning_summary}</p>
                  </div>

                  {plannerDecision.next_tools.length > 0 ? (
                    <div className="grid gap-4 lg:grid-cols-2">
                      {plannerDecision.next_tools.map((tool) => (
                        <div
                          key={`${plannerDecision.id}-${tool.tool_name}`}
                          className="rounded-3xl border border-white/10 bg-[#090d16] p-5 shadow-xl shadow-black/15"
                        >
                          <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                            <div>
                              <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">Next Tool</p>
                              <h3 className="mt-2 text-base font-semibold tracking-tight text-white">
                                {logicalToolLabel(tool.tool_name)}
                              </h3>
                            </div>
                            <Badge tone={tool.priority}>{tool.priority}</Badge>
                          </div>
                          <p className="mt-4 text-sm leading-6 text-slate-400">{tool.reason}</p>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <EmptyState>No tools were planned because the workflow needs clarification first.</EmptyState>
                  )}
                </div>
              ) : (
                <EmptyState>No planner decision has been recorded for this run yet.</EmptyState>
              )}
            </Panel>

            <WorkflowReplayPanel workflowRunId={workflow.id} />

            <Panel title="Agent Execution" eyebrow="Dynamic tool executor v2">
              <div className="mb-5 flex flex-col gap-3 rounded-2xl border border-amber-300/15 bg-amber-300/[0.055] p-4 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <p className="text-sm font-semibold text-amber-100">Safety allowlist active</p>
                  <p className="mt-1 text-xs leading-5 text-amber-100/65">
                    Skipped tools were intentionally blocked by the v2 dynamic-execution allowlist; legacy workflow outputs still run normally.
                  </p>
                </div>
                <Badge tone="skipped">v2 guarded</Badge>
              </div>

              {agentExecutions.length > 0 ? (
                <div className="space-y-3">
                  {agentExecutions.map((execution) => (
                    <article
                      key={execution.id}
                      className="overflow-hidden rounded-3xl border border-white/10 bg-[#090d16] shadow-xl shadow-black/15"
                    >
                      <div className="flex flex-col gap-4 border-b border-white/10 bg-white/[0.025] px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
                        <div className="min-w-0">
                          <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">
                            Planner Decision #{execution.planner_decision_id}
                          </p>
                          <h3 className="mt-2 truncate font-mono text-sm font-semibold text-white">
                            {execution.tool_name}
                          </h3>
                        </div>
                        <div className="flex flex-wrap items-center gap-2">
                          <Badge tone={execution.status}>{titleize(execution.status)}</Badge>
                          <span className="text-xs text-slate-500">{dateTime(execution.created_at)}</span>
                        </div>
                      </div>

                      <div className="grid gap-4 p-5 lg:grid-cols-2">
                        <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
                          <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-500">
                            Result Summary
                          </p>
                          <p className="mt-2 text-sm leading-6 text-slate-300">
                            {execution.result_summary || "No result summary recorded."}
                          </p>
                          {execution.status === "skipped" ? (
                            <p className="mt-3 text-xs font-medium text-amber-200/80">
                              Intentionally blocked by the dynamic execution v2 allowlist.
                            </p>
                          ) : null}
                        </div>

                        <div
                          className={cx(
                            "rounded-2xl border p-4",
                            execution.error_message
                              ? "border-rose-300/20 bg-rose-300/[0.055]"
                              : "border-white/10 bg-black/20",
                          )}
                        >
                          <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-500">
                            Error Message
                          </p>
                          <p className={cx("mt-2 text-sm leading-6", execution.error_message ? "text-rose-100" : "text-slate-500")}>
                            {execution.error_message || "None"}
                          </p>
                        </div>
                      </div>
                    </article>
                  ))}
                </div>
              ) : (
                <EmptyState>No dynamic agent execution traces were recorded for this run.</EmptyState>
              )}
            </Panel>

            <Panel title="Workflow Timeline" eyebrow="Connected agent stages">
              <div className="grid gap-4 xl:grid-cols-7">
                {TIMELINE_STEPS.map(([key, label, description], index) => {
                  const state = timelineStatus(key, workflow, outputs, toolCalls, criticResult);

                  return (
                    <div key={key} className="relative">
                      {index < TIMELINE_STEPS.length - 1 ? (
                        <div className="absolute left-10 top-6 hidden h-px w-[calc(100%+1rem)] bg-gradient-to-r from-white/20 to-transparent xl:block" />
                      ) : null}
                      <div className="relative rounded-3xl border border-white/10 bg-white/[0.035] p-4 shadow-xl shadow-black/10">
                        <div
                          className={cx(
                            "flex h-12 w-12 items-center justify-center rounded-2xl border text-sm font-black shadow-lg",
                            timelineDotClass(state),
                          )}
                        >
                          {state === "completed" ? "✓" : index + 1}
                        </div>
                        <h3 className="mt-4 text-sm font-semibold text-white">{label}</h3>
                        <p className="mt-1 min-h-10 text-xs leading-5 text-slate-500">{description}</p>
                        <Badge tone={state} className="mt-4">{titleize(state)}</Badge>
                      </div>
                    </div>
                  );
                })}
              </div>
            </Panel>

            <Panel title="Tool Calls" eyebrow="Provider activity">
              {toolCalls.length > 0 ? (
                <div className="space-y-3">
                  {toolCalls.map((toolCall) => (
                    <div
                      key={toolCall.id}
                      className="rounded-3xl border border-white/10 bg-black/20 p-4 shadow-xl shadow-black/10"
                    >
                      <div className="grid gap-4 lg:grid-cols-[1.1fr_0.4fr_0.45fr_0.3fr_0.55fr] lg:items-center">
                        <div>
                          <p className="text-sm font-semibold text-white">{logicalToolLabel(toolCall.tool_name)}</p>
                          <p className="mt-1 text-xs text-slate-500">{titleize(toolCall.step_name)}</p>
                        </div>
                        <Badge tone={toolCall.status}>{titleize(toolCall.status)}</Badge>
                        <Badge tone={providerLabel(toolCall.provider, toolCall.fallback_used) === "LM Studio" ? "medium" : "success"}>
                          {providerLabel(toolCall.provider, toolCall.fallback_used)}
                        </Badge>
                        <div>
                          <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-600">Attempt</p>
                          <p className="mt-1 text-sm font-semibold text-slate-200">{toolCall.attempt}</p>
                        </div>
                        <Badge tone={toolCall.fallback_used ? "medium" : "success"}>
                          {toolCall.fallback_used ? "Recovered via fallback" : "Primary path"}
                        </Badge>
                      </div>

                      {toolCall.error_message ? (
                        <div className="mt-4 rounded-2xl border border-rose-400/25 bg-rose-400/10 p-3 text-xs leading-5 text-rose-200">
                          {toolCall.error_message}
                        </div>
                      ) : null}
                    </div>
                  ))}
                </div>
              ) : (
                <EmptyState>No tool calls have been recorded for this run.</EmptyState>
              )}
            </Panel>

            <section className="grid gap-6 xl:grid-cols-2">
              <Panel title="Generated Ticket" eyebrow="Linear-style issue">
                {ticket ? (
                  <div className="rounded-3xl border border-white/10 bg-[#090d16] p-5 shadow-2xl shadow-black/20">
                    <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                      <div>
                        <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">OPS-{ticket.id}</p>
                        <h3 className="mt-2 text-xl font-semibold tracking-tight text-white">{ticket.title}</h3>
                      </div>
                      <Badge tone={ticket.priority}>{ticket.priority}</Badge>
                    </div>

                    <div className="mt-5 flex flex-wrap gap-2">
                      <Badge tone="default">{ticket.category ?? "uncategorized"}</Badge>
                      <Badge tone="default">{ticket.team ?? "unassigned"}</Badge>
                      <Badge tone={ticket.requires_approval ? "medium" : "success"}>
                        {ticket.requires_approval ? "approval required" : "ready"}
                      </Badge>
                      <Badge tone={ticket.status}>{ticket.status}</Badge>
                    </div>

                    <p className="mt-5 text-sm leading-7 text-slate-300">{ticket.description}</p>

                    <div className="mt-5 rounded-2xl border border-white/10 bg-white/[0.035] p-4">
                      <p className="text-sm font-semibold text-white">Acceptance Criteria</p>
                      <pre className="mt-3 whitespace-pre-wrap text-sm leading-7 text-slate-300">
                        {ticket.acceptance_criteria ?? "No acceptance criteria recorded."}
                      </pre>
                    </div>

                    {ticket.source_evidence ? (
                      <div className="mt-4 rounded-2xl border border-sky-300/15 bg-sky-300/5 p-4">
                        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-sky-200/70">Source Evidence</p>
                        <p className="mt-2 text-sm leading-6 text-sky-100/80">{ticket.source_evidence}</p>
                      </div>
                    ) : null}

                    <ApprovalActions
                      workflowRunId={workflow.id}
                      itemType="ticket"
                      itemId={ticket.id}
                    />
                  </div>
                ) : (
                  <EmptyState>No ticket generated. The workflow likely needs clarification before creating engineering work.</EmptyState>
                )}
              </Panel>

              <Panel title="Customer Reply" eyebrow="Support draft">
                {reply ? (
                  <div className="space-y-4">
                    <div className="rounded-3xl border border-white/10 bg-[#090d16] p-5 shadow-2xl shadow-black/20">
                      <div className="flex flex-wrap gap-2">
                        <Badge tone={reply.risk_level}>{reply.risk_level} risk</Badge>
                        <Badge tone={reply.requires_approval ? "medium" : "success"}>
                          {reply.requires_approval ? "approval required" : "approved"}
                        </Badge>
                        <Badge tone={reply.status}>{reply.status}</Badge>
                      </div>

                      <div className="mt-5 grid gap-4 rounded-2xl border border-white/10 bg-white/[0.035] p-4 sm:grid-cols-2">
                        <div>
                          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Customer</p>
                          <p className="mt-2 text-sm font-semibold text-white">{reply.customer ?? "Unknown"}</p>
                        </div>
                        <div>
                          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Issue</p>
                          <p className="mt-2 text-sm font-semibold text-white">{reply.issue}</p>
                        </div>
                      </div>

                      <div className="mt-5 rounded-2xl border border-white/10 bg-black/25 p-4">
                        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Draft Reply</p>
                        <p className="mt-3 whitespace-pre-wrap text-sm leading-7 text-slate-300">
                          {reply.draft_reply ?? "Reply withheld due to risk."}
                        </p>
                      </div>

                      <ApprovalActions
                        workflowRunId={workflow.id}
                        itemType="reply"
                        itemId={reply.id}
                      />
                    </div>

                    {reply.risk_reason ? (
                      <div className="rounded-2xl border border-amber-300/20 bg-amber-300/10 p-4 text-sm leading-6 text-amber-100">
                        {reply.risk_reason}
                      </div>
                    ) : null}
                  </div>
                ) : (
                  <EmptyState>No customer reply generated for this run.</EmptyState>
                )}
              </Panel>
            </section>

            <Panel title="Founder Summary" eyebrow="Executive readout">
              {founderSummary ? (
                <div className="grid gap-4 xl:grid-cols-[1.15fr_0.85fr]">
                  <div className="rounded-3xl border border-sky-300/15 bg-sky-300/[0.055] p-5 shadow-xl shadow-sky-950/15">
                    <p className="text-xs font-semibold uppercase tracking-[0.18em] text-sky-200/70">Summary</p>
                    <p className="mt-3 text-sm leading-7 text-slate-200">{founderSummary.summary}</p>
                  </div>

                  <div className="rounded-3xl border border-amber-300/20 bg-amber-300/[0.065] p-5 shadow-xl shadow-amber-950/15">
                    <p className="text-xs font-semibold uppercase tracking-[0.18em] text-amber-100/75">Risks</p>
                    <p className="mt-3 text-sm leading-7 text-amber-50/90">
                      {founderSummary.risks ?? "No risks recorded."}
                    </p>
                  </div>

                  <div className="rounded-3xl border border-white/10 bg-black/20 p-5 shadow-xl shadow-black/15 xl:col-span-2">
                    <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
                      Recommended Actions
                    </p>
                    <pre className="mt-3 whitespace-pre-wrap text-sm leading-7 text-slate-300">
                      {founderSummary.recommended_actions ?? "No recommended actions recorded."}
                    </pre>
                  </div>
                </div>
              ) : (
                <EmptyState>No founder summary recorded for this run.</EmptyState>
              )}
            </Panel>

            <Panel
              title="Memory"
              eyebrow={memoryInfluencedRun ? "Memory influenced this run" : "Similar Past Issues"}
            >
              {sortedMemoryItems.length > 0 ? (
                <div className="space-y-4">
                  {memoryInfluencedRun ? (
                    <div className="rounded-2xl border border-amber-300/20 bg-amber-300/10 p-4">
                      <Badge tone="recovered">Memory influenced this run</Badge>
                      <p className="mt-3 text-sm leading-6 text-amber-50/90">
                        Similar past issues were found before ticket generation, so OpsPilot raised recurrence risk and may have increased ticket priority.
                      </p>
                    </div>
                  ) : null}

                  <div className="grid gap-4 lg:grid-cols-2">
                    {sortedMemoryItems.map((memoryItem, index) => (
                      <div
                        key={memoryItem.id}
                        className={cx(
                          "rounded-3xl border p-5 shadow-xl",
                          index === 0 && memoryItem.relevance_score
                            ? "border-amber-300/30 bg-amber-300/[0.07] shadow-amber-950/20"
                            : "border-white/10 bg-[#090d16] shadow-black/15",
                        )}
                      >
                        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                          <div>
                            <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">
                              Source Run #{memoryItem.workflow_run_id}
                            </p>
                            <h3 className="mt-2 text-base font-semibold tracking-tight text-white">
                              {memoryItem.title}
                            </h3>
                          </div>
                          <div className="flex flex-wrap gap-2">
                            {index === 0 && memoryItem.relevance_score ? <Badge tone="recovered">strongest match</Badge> : null}
                            <Badge tone="default">{memoryItem.category ?? "uncategorized"}</Badge>
                          </div>
                        </div>

                        <p className="mt-4 text-sm leading-6 text-slate-400">{memoryItem.content}</p>

                        <div className="mt-5 flex flex-wrap items-center gap-2">
                          <Badge tone="default">{titleize(memoryItem.item_type)}</Badge>
                          <Badge tone={memoryItem.relevance_score ? "success" : "default"}>
                            relevance {memoryItem.relevance_score ?? "n/a"}
                          </Badge>
                          <span className="text-xs text-slate-500">{dateTime(memoryItem.created_at)}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <EmptyState>No similar past issues have been stored yet.</EmptyState>
              )}
            </Panel>

            <Panel title="Critic Review" eyebrow="Deterministic reflection">
              {criticResult ? (
                <div className="space-y-5">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge tone={criticResult.critic_status}>{titleize(criticResult.critic_status)}</Badge>
                    <Badge tone={criticResult.requires_manual_review ? "medium" : "success"}>
                      {criticResult.requires_manual_review ? "manual review required" : "manual review clear"}
                    </Badge>
                    <Badge tone="default">{dateTime(criticResult.created_at)}</Badge>
                  </div>

                  <div className="grid gap-4 md:grid-cols-3">
                    <MetricTile label="Status" value={titleize(criticResult.critic_status)} tone={criticResult.critic_status} />
                    <MetricTile
                      label="Manual Review"
                      value={criticResult.requires_manual_review ? "Required" : "Clear"}
                      tone={criticResult.requires_manual_review ? "medium" : "healthy"}
                    />
                    <MetricTile label="Risk Flags" value={String(criticResult.risk_flags.length)} tone={criticResult.risk_flags.length ? "medium" : "healthy"} />
                    <MetricTile label="Reviewed" value={dateTime(criticResult.created_at)} />
                  </div>

                  <div className="rounded-3xl border border-white/10 bg-black/20 p-5 shadow-xl shadow-black/15">
                    <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Recommended Action</p>
                    <p className="mt-3 text-sm leading-7 text-slate-200">{criticResult.recommended_action}</p>
                  </div>

                  <div className="grid gap-4 lg:grid-cols-2">
                    <div className="rounded-3xl border border-rose-300/20 bg-rose-300/[0.055] p-5 shadow-xl shadow-rose-950/15">
                      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-rose-100/75">Risk Flags</p>
                      <div className="flex items-center justify-between gap-3">
                        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-rose-100/75">Risk Flags</p>
                        <Badge tone={criticResult.risk_flags.length ? "high" : "success"}>
                          {criticResult.risk_flags.length || "none"}
                        </Badge>
                      </div>
                      {criticResult.risk_flags.length > 0 ? (
                        <ul className="mt-4 space-y-3 text-sm leading-6 text-rose-50/90">
                          {criticResult.risk_flags.map((flag) => (
                            <li key={flag}>{flag}</li>
                          ))}
                        </ul>
                      ) : (
                        <p className="mt-4 text-sm leading-6 text-slate-400">No risk flags detected.</p>
                      )}
                    </div>

                    <div className="rounded-3xl border border-amber-300/20 bg-amber-300/[0.06] p-5 shadow-xl shadow-amber-950/15">
                      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-amber-100/75">Quality Notes</p>
                      <div className="flex items-center justify-between gap-3">
                        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-amber-100/75">Quality Notes</p>
                        <Badge tone={criticResult.quality_notes.length ? "medium" : "success"}>
                          {criticResult.quality_notes.length || "none"}
                        </Badge>
                      </div>
                      {criticResult.quality_notes.length > 0 ? (
                        <ul className="mt-4 space-y-3 text-sm leading-6 text-amber-50/90">
                          {criticResult.quality_notes.map((note) => (
                            <li key={note}>{note}</li>
                          ))}
                        </ul>
                      ) : (
                        <p className="mt-4 text-sm leading-6 text-slate-400">No quality warnings detected.</p>
                      )}
                    </div>
                  </div>
                </div>
              ) : (
                <EmptyState>No critic review has been recorded for this run yet.</EmptyState>
              )}
            </Panel>

            <Panel title="Evaluation" eyebrow="Quality metrics">
              {evaluation ? (
                <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                  <MetricTile label="Quality Score" value={percent(evaluation.quality_score)} />
                  <MetricTile label="Reply Policy" value={percent(evaluation.reply_policy_compliance)} />
                  <MetricTile label="Ticket Complete" value={percent(evaluation.ticket_completeness)} />
                  <MetricTile label="Unsupported Claims" value={percent(evaluation.unsupported_claim_rate)} />
                  <MetricTile label="Tool Recovery" value={percent(evaluation.tool_recovery_success)} />
                  <MetricTile label="Human Review" value={evaluation.requires_human_review ? "Required" : "Clear"} />

                  <div className="rounded-3xl border border-white/10 bg-black/20 p-5 md:col-span-2 xl:col-span-3">
                    <p className="text-sm font-semibold text-white">Risk Notes</p>
                    <p className="mt-3 text-sm leading-7 text-slate-300">
                      {evaluation.risks ?? "No risks recorded."}
                    </p>
                  </div>
                </div>
              ) : (
                <EmptyState>No evaluation recorded for this run.</EmptyState>
              )}
            </Panel>
          </div>
        </div>
      </div>
    </main>
  );
}
