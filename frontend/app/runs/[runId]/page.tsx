import type { ReactNode } from "react";

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

type WorkflowOutputs = {
  workflow_run: WorkflowRun;
  tickets: Ticket[];
  customer_replies: CustomerReply[];
  founder_summary: unknown;
  evaluation: Evaluation | null;
};

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

const TIMELINE_STEPS = [
  ["intent_router", "Intent", "Classify workflow"],
  ["issue_extraction", "Extract", "Extract structured issue"],
  ["ticket_generation", "Ticket", "Create engineering task"],
  ["reply_generation", "Reply", "Draft customer response"],
  ["evaluation", "Evaluate", "Score quality and risk"],
] as const;

const NAV_ITEMS = ["Dashboard", "Workflows", "Runs", "Benchmarks"] as const;

async function fetchJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, { cache: "no-store" });

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
  if (tone === "completed" || tone === "success" || tone === "low") {
    return "border-emerald-400/25 bg-emerald-400/10 text-emerald-200 shadow-emerald-950/30";
  }

  if (tone === "failed" || tone === "high") {
    return "border-rose-400/25 bg-rose-400/10 text-rose-200 shadow-rose-950/30";
  }

  if (tone === "needs_clarification" || tone === "medium" || tone === "skipped") {
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
) {
  if (step === "evaluation" && outputs.evaluation) return "completed";
  if (step === "ticket_generation" && outputs.tickets.length > 0) return "completed";
  if (step === "reply_generation" && outputs.customer_replies.length > 0) return "completed";

  const call = toolCalls.find((item) => item.step_name === step);
  if (call) return call.status === "success" ? "completed" : call.status;

  return workflow.status === "needs_clarification" ? "skipped" : "pending";
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

function MetricTile({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="rounded-3xl border border-white/10 bg-white/[0.045] p-5 shadow-xl shadow-black/15">
      <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">{label}</p>
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

  const [workflow, outputs, toolCalls] = await Promise.all([
    fetchJson<WorkflowRun>(`/api/v1/workflows/${runId}`),
    fetchJson<WorkflowOutputs>(`/api/v1/workflows/${runId}/outputs`),
    fetchJson<ToolCall[]>(`/api/v1/workflows/${runId}/tool-calls`),
  ]);

  const ticket = outputs.tickets[0];
  const reply = outputs.customer_replies[0];
  const evaluation = outputs.evaluation;
  const fallbackUsed = toolCalls.some((toolCall) => toolCall.fallback_used);
  const humanReviewRequired = Boolean(evaluation?.requires_human_review || reply?.requires_approval);

  return (
    <main className="min-h-screen bg-[#05070b] text-slate-100">
      <div className="fixed inset-0 bg-[linear-gradient(180deg,rgba(15,23,42,0.72),rgba(2,6,23,0.96)),radial-gradient(circle_at_20%_0%,rgba(14,165,233,0.18),transparent_34%),radial-gradient(circle_at_90%_4%,rgba(168,85,247,0.16),transparent_30%)]" />
      <div className="fixed inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-sky-300/40 to-transparent" />

      <div className="relative flex min-h-screen">
        <aside className="hidden w-72 shrink-0 border-r border-white/10 bg-black/20 px-4 py-5 backdrop-blur-2xl lg:fixed lg:inset-y-0 lg:flex lg:flex-col">
          <div className="flex items-center gap-3 rounded-2xl border border-white/10 bg-white/[0.045] p-3 shadow-lg shadow-black/20">
            <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-gradient-to-br from-sky-300 to-violet-400 text-sm font-black text-slate-950">
              OP
            </div>
            <div>
              <p className="text-sm font-semibold text-white">OpsPilot</p>
              <p className="text-xs text-slate-500">Agent operations</p>
            </div>
          </div>

          <nav className="mt-8 space-y-1">
            {NAV_ITEMS.map((item) => {
              const active = item === "Runs";

              return (
                <a
                  key={item}
                  className={cx(
                    "flex items-center justify-between rounded-2xl px-3 py-2.5 text-sm font-medium transition",
                    active
                      ? "border border-sky-300/20 bg-sky-300/10 text-sky-100 shadow-lg shadow-sky-950/20"
                      : "text-slate-400 hover:bg-white/[0.045] hover:text-white",
                  )}
                  href="#"
                >
                  <span>{item}</span>
                  {active ? <span className="h-1.5 w-1.5 rounded-full bg-sky-300" /> : null}
                </a>
              );
            })}
          </nav>

          <div className="mt-auto rounded-3xl border border-white/10 bg-white/[0.035] p-4">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Workspace</p>
            <p className="mt-2 text-sm font-medium text-white">Customer Feedback Triage</p>
            <p className="mt-2 text-xs leading-5 text-slate-500">Real agent outputs, tool recovery, and review status in one run view.</p>
          </div>
        </aside>

        <div className="flex w-full flex-col lg:pl-72">
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

            <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
              <MetricTile label="Status" value={titleize(workflow.status)} />
              <MetricTile label="Confidence" value={percent(workflow.confidence)} />
              <MetricTile label="Tickets" value={String(outputs.tickets.length)} />
              <MetricTile label="Replies" value={String(outputs.customer_replies.length)} />
              <MetricTile label="Tool Fallback" value={fallbackUsed ? "Used" : "None"} />
            </section>

            <Panel title="Workflow Timeline" eyebrow="Connected agent stages">
              <div className="grid gap-4 xl:grid-cols-5">
                {TIMELINE_STEPS.map(([key, label, description], index) => {
                  const state = timelineStatus(key, workflow, outputs, toolCalls);

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
                      <div className="grid gap-4 lg:grid-cols-[1.2fr_0.45fr_0.35fr_0.55fr] lg:items-center">
                        <div>
                          <p className="text-sm font-semibold text-white">{toolCall.tool_name}</p>
                          <p className="mt-1 text-xs text-slate-500">{titleize(toolCall.step_name)}</p>
                        </div>
                        <Badge tone={toolCall.status}>{titleize(toolCall.status)}</Badge>
                        <div>
                          <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-600">Attempt</p>
                          <p className="mt-1 text-sm font-semibold text-slate-200">{toolCall.attempt}</p>
                        </div>
                        <Badge tone={toolCall.fallback_used ? "medium" : "success"}>
                          {toolCall.fallback_used ? "fallback used" : "primary"}
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
