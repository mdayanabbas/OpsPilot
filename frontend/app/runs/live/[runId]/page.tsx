"use client";

import { use, useEffect, useMemo, useState } from "react";
import Link from "next/link";

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
  step_name: string;
  tool_name: string;
  provider: string;
  status: string;
  attempt: number;
  error_message: string | null;
  fallback_used: boolean;
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
  status: string;
};

type CustomerReply = {
  id: number;
  customer: string | null;
  issue: string;
  draft_reply: string | null;
  risk_level: string;
  risk_reason: string | null;
  status: string;
};

type Evaluation = {
  quality_score: number | null;
  reply_policy_compliance: number | null;
  ticket_completeness: number | null;
  tool_recovery_success: number | null;
  requires_human_review: boolean;
  risks: string | null;
};

type FounderSummary = {
  summary: string;
  risks: string | null;
  recommended_actions: string | null;
};

type MemoryItem = {
  id: number;
  workflow_run_id: number;
  title: string;
  category: string | null;
  relevance_score: number | null;
  created_at: string;
};

type WorkflowOutputs = {
  workflow_run: WorkflowRun;
  tickets: Ticket[];
  customer_replies: CustomerReply[];
  founder_summary: FounderSummary | null;
  evaluation: Evaluation | null;
};

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
const TERMINAL_STATUSES = new Set(["completed", "failed", "needs_clarification"]);
const STEPS = [
  ["intent_router", "Intent", "Classify workflow"],
  ["issue_extraction", "Extract", "Find actionable issue"],
  ["ticket_generation", "Ticket", "Create engineering ticket"],
  ["reply_generation", "Reply", "Draft customer response"],
  ["evaluation", "Evaluate", "Score quality and risk"],
] as const;

async function fetchJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, { cache: "no-store" });

  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
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

function providerLabel(provider: string, fallbackUsed = false) {
  if (provider === "local" || provider === "fallback" || fallbackUsed) return "LM Studio";
  return "Groq";
}

function Badge({ children, tone = "default" }: { children: React.ReactNode; tone?: string }) {
  const toneClass =
    tone === "success" || tone === "completed"
      ? "border-emerald-400/25 bg-emerald-400/10 text-emerald-200"
      : tone === "failed" || tone === "danger"
        ? "border-rose-400/25 bg-rose-400/10 text-rose-200"
        : tone === "running" || tone === "warning"
          ? "border-amber-400/25 bg-amber-400/10 text-amber-200"
          : "border-slate-500/30 bg-slate-500/10 text-slate-300";

  return <span className={cx("inline-flex rounded-full border px-2.5 py-1 text-xs font-semibold capitalize", toneClass)}>{children}</span>;
}

function Panel({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="rounded-3xl border border-white/10 bg-slate-950/55 shadow-2xl shadow-black/25 backdrop-blur-xl">
      <div className="border-b border-white/10 px-6 py-5">
        <h2 className="text-lg font-semibold tracking-tight text-white">{title}</h2>
      </div>
      <div className="p-6">{children}</div>
    </section>
  );
}

function stepState(step: string, workflow: WorkflowRun | null, outputs: WorkflowOutputs | null, toolCalls: ToolCall[]) {
  if (!workflow) return "pending";
  if (step === "ticket_generation" && outputs?.tickets.length) return "completed";
  if (step === "reply_generation" && outputs?.customer_replies.length) return "completed";
  if (step === "evaluation" && outputs?.evaluation) return "completed";

  const call = toolCalls.find((toolCall) => toolCall.step_name === step);
  if (call?.status === "failed") return "failed";
  if (call?.status === "success") return "completed";
  if (workflow.status === "failed") return "failed";
  return "pending";
}

export default function LiveWorkflowRunPage({ params }: { params: Promise<{ runId: string }> }) {
  const { runId } = use(params);
  const [workflow, setWorkflow] = useState<WorkflowRun | null>(null);
  const [toolCalls, setToolCalls] = useState<ToolCall[]>([]);
  const [outputs, setOutputs] = useState<WorkflowOutputs | null>(null);
  const [memory, setMemory] = useState<MemoryItem[]>([]);
  const [error, setError] = useState<string | null>(null);

  const isTerminal = workflow ? TERMINAL_STATUSES.has(workflow.status) : false;
  const fallbackUsed = toolCalls.some((toolCall) => toolCall.fallback_used);
  const sortedMemory = [...memory].sort(
    (left, right) => (right.relevance_score ?? 0) - (left.relevance_score ?? 0),
  );
  const currentStep = useMemo(() => {
    if (!workflow || isTerminal) return null;
    return STEPS.find(([step]) => stepState(step, workflow, outputs, toolCalls) === "pending")?.[0] ?? "evaluation";
  }, [isTerminal, outputs, toolCalls, workflow]);

  useEffect(() => {
    let cancelled = false;
    let intervalId: ReturnType<typeof setInterval> | null = null;

    async function poll() {
      try {
        const [nextWorkflow, nextToolCalls, nextOutputs] = await Promise.all([
          fetchJson<WorkflowRun>(`/api/v1/workflows/${runId}`),
          fetchJson<ToolCall[]>(`/api/v1/workflows/${runId}/tool-calls`),
          fetchJson<WorkflowOutputs>(`/api/v1/workflows/${runId}/outputs`),
        ]);

        if (cancelled) return;
        setWorkflow(nextWorkflow);
        setToolCalls(nextToolCalls);
        setOutputs(nextOutputs);
        setError(null);

        if (TERMINAL_STATUSES.has(nextWorkflow.status)) {
          const memoryItems = await fetchJson<MemoryItem[]>(`/api/v1/workflows/${runId}/memory`);
          if (!cancelled) setMemory(memoryItems);
          if (intervalId) clearInterval(intervalId);
        }
      } catch (requestError) {
        if (!cancelled) {
          setError(requestError instanceof Error ? requestError.message : "Unable to poll workflow.");
        }
      }
    }

    poll();
    intervalId = setInterval(poll, 1500);

    return () => {
      cancelled = true;
      if (intervalId) clearInterval(intervalId);
    };
  }, [runId]);

  return (
    <main className="min-h-screen bg-[#05070b] text-slate-100">
      <div className="fixed inset-0 bg-[linear-gradient(180deg,rgba(15,23,42,0.72),rgba(2,6,23,0.96)),radial-gradient(circle_at_20%_0%,rgba(14,165,233,0.18),transparent_34%),radial-gradient(circle_at_90%_4%,rgba(168,85,247,0.16),transparent_30%)]" />
      <div className="relative mx-auto flex w-full max-w-7xl flex-col gap-6 px-4 py-6 sm:px-6 lg:px-8">
        <header className="rounded-3xl border border-white/10 bg-slate-950/70 p-6 shadow-2xl shadow-black/30 backdrop-blur-xl">
          <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-500">Live Workflow Run</p>
              <h1 className="mt-2 text-3xl font-semibold tracking-tight text-white">Run #{runId}</h1>
              <p className="mt-3 max-w-3xl text-sm leading-7 text-slate-300">
                {workflow?.input_text ?? "Loading workflow..."}
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              <Badge tone={workflow?.status === "completed" ? "success" : workflow?.status === "failed" ? "danger" : "running"}>
                {titleize(workflow?.status ?? "running")}
              </Badge>
              {!isTerminal ? <Badge tone="running">OpsPilot is analyzing...</Badge> : null}
              {fallbackUsed ? <Badge tone="warning">fallback alert</Badge> : null}
            </div>
          </div>
        </header>

        {error ? (
          <div className="rounded-3xl border border-rose-400/25 bg-rose-400/10 p-5 text-sm text-rose-200">{error}</div>
        ) : null}

        <Panel title="Live Timeline">
          <div className="grid gap-4 xl:grid-cols-5">
            {STEPS.map(([step, label, description], index) => {
              const state = step === currentStep ? "running" : stepState(step, workflow, outputs, toolCalls);
              return (
                <div key={step} className="rounded-3xl border border-white/10 bg-white/[0.035] p-4 shadow-xl shadow-black/10">
                  <div
                    className={cx(
                      "flex h-12 w-12 items-center justify-center rounded-2xl border text-sm font-black shadow-lg",
                      state === "completed" && "border-emerald-300/60 bg-emerald-400 text-emerald-950",
                      state === "running" && "animate-pulse border-amber-300/60 bg-amber-300 text-amber-950",
                      state === "failed" && "border-rose-300/60 bg-rose-400 text-rose-950",
                      state === "pending" && "border-white/15 bg-white/10 text-slate-400",
                    )}
                  >
                    {state === "completed" ? "✓" : index + 1}
                  </div>
                  <h3 className="mt-4 text-sm font-semibold text-white">{label}</h3>
                  <p className="mt-1 min-h-10 text-xs leading-5 text-slate-500">{description}</p>
                  <Badge tone={state} >{state}</Badge>
                </div>
              );
            })}
          </div>
        </Panel>

        <Panel title="Provider Activity">
          {toolCalls.length ? (
            <div className="space-y-3">
              {toolCalls.map((toolCall) => (
                <div key={toolCall.id} className="grid gap-4 rounded-3xl border border-white/10 bg-black/20 p-4 md:grid-cols-[1fr_0.4fr_0.5fr_0.35fr_0.7fr] md:items-center">
                  <div>
                    <p className="text-sm font-semibold text-white">{titleize(toolCall.tool_name)}</p>
                    <p className="mt-1 text-xs text-slate-500">{titleize(toolCall.step_name)}</p>
                  </div>
                  <Badge tone={toolCall.status === "success" ? "success" : toolCall.status}>{titleize(toolCall.status)}</Badge>
                  <Badge tone={providerLabel(toolCall.provider, toolCall.fallback_used) === "LM Studio" ? "warning" : "success"}>
                    {providerLabel(toolCall.provider, toolCall.fallback_used)}
                  </Badge>
                  <p className="text-sm font-semibold text-slate-200">Retry {Math.max(toolCall.attempt - 1, 0)}</p>
                  <Badge tone={toolCall.fallback_used ? "warning" : "default"}>
                    {toolCall.fallback_used ? "Recovered via fallback" : "Primary path"}
                  </Badge>
                </div>
              ))}
            </div>
          ) : (
            <div className="rounded-2xl border border-dashed border-white/12 bg-white/[0.025] p-6 text-sm text-slate-400">
              Waiting for the first tool call...
            </div>
          )}
        </Panel>

        {isTerminal && outputs ? (
          <>
            <section className="grid gap-6 xl:grid-cols-2">
              <Panel title="Generated Ticket">
                {outputs.tickets[0] ? (
                  <div className="space-y-4">
                    <div className="flex flex-wrap gap-2">
                      <Badge>{outputs.tickets[0].category ?? "uncategorized"}</Badge>
                      <Badge tone={outputs.tickets[0].priority === "high" ? "danger" : "warning"}>{outputs.tickets[0].priority}</Badge>
                    </div>
                    <h3 className="text-xl font-semibold text-white">{outputs.tickets[0].title}</h3>
                    <p className="text-sm leading-7 text-slate-300">{outputs.tickets[0].description}</p>
                    {outputs.tickets[0].source_evidence ? <p className="rounded-2xl border border-sky-300/15 bg-sky-300/5 p-4 text-sm text-sky-100/80">{outputs.tickets[0].source_evidence}</p> : null}
                  </div>
                ) : (
                  <p className="text-sm text-slate-400">No ticket generated.</p>
                )}
              </Panel>

              <Panel title="Customer Reply">
                {outputs.customer_replies[0] ? (
                  <div className="space-y-4">
                    <div className="flex flex-wrap gap-2">
                      <Badge tone={outputs.customer_replies[0].risk_level === "high" ? "danger" : "warning"}>
                        {outputs.customer_replies[0].risk_level} risk
                      </Badge>
                      <Badge>{outputs.customer_replies[0].status}</Badge>
                    </div>
                    <p className="text-sm leading-7 text-slate-300 whitespace-pre-wrap">
                      {outputs.customer_replies[0].draft_reply ?? "Reply withheld due to risk."}
                    </p>
                  </div>
                ) : (
                  <p className="text-sm text-slate-400">No reply generated.</p>
                )}
              </Panel>
            </section>

            <Panel title="Evaluation">
              {outputs.evaluation ? (
                <div className="grid gap-4 md:grid-cols-4">
                  <div className="rounded-2xl border border-white/10 bg-black/20 p-4"><p className="text-xs text-slate-500">Quality</p><p className="mt-2 text-xl font-semibold">{percent(outputs.evaluation.quality_score)}</p></div>
                  <div className="rounded-2xl border border-white/10 bg-black/20 p-4"><p className="text-xs text-slate-500">Reply Policy</p><p className="mt-2 text-xl font-semibold">{percent(outputs.evaluation.reply_policy_compliance)}</p></div>
                  <div className="rounded-2xl border border-white/10 bg-black/20 p-4"><p className="text-xs text-slate-500">Ticket Complete</p><p className="mt-2 text-xl font-semibold">{percent(outputs.evaluation.ticket_completeness)}</p></div>
                  <div className="rounded-2xl border border-white/10 bg-black/20 p-4"><p className="text-xs text-slate-500">Tool Recovery</p><p className="mt-2 text-xl font-semibold">{percent(outputs.evaluation.tool_recovery_success)}</p></div>
                </div>
              ) : null}
            </Panel>

            <section className="grid gap-6 xl:grid-cols-2">
              <Panel title="Founder Summary">
                <p className="text-sm leading-7 text-slate-300">{outputs.founder_summary?.summary ?? "No founder summary recorded."}</p>
              </Panel>
              <Panel title="Memory">
                {sortedMemory.length ? (
                  <div className="space-y-3">
                    {sortedMemory.map((item, index) => (
                      <div
                        key={item.id}
                        className={cx(
                          "rounded-2xl border p-4",
                          index === 0 && item.relevance_score
                            ? "border-amber-300/30 bg-amber-300/10"
                            : "border-white/10 bg-black/20",
                        )}
                      >
                        <p className="text-sm font-semibold text-white">{item.title}</p>
                        <div className="mt-2 flex flex-wrap gap-2">
                          {index === 0 && item.relevance_score ? <Badge tone="warning">strongest match</Badge> : null}
                          <Badge>{item.category ?? "uncategorized"}</Badge>
                          <Badge>relevance {item.relevance_score ?? "n/a"}</Badge>
                        </div>
                        <p className="mt-2 text-xs text-slate-500">Workflow #{item.workflow_run_id}</p>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-slate-400">No related memory items found.</p>
                )}
              </Panel>
            </section>

            <div className="flex justify-end">
              <Link href={`/runs/${runId}`} className="rounded-2xl border border-sky-300/20 bg-sky-300/10 px-4 py-2 text-sm font-semibold text-sky-100 transition hover:bg-sky-300/15">
                Open full run details
              </Link>
            </div>
          </>
        ) : null}
      </div>
    </main>
  );
}
