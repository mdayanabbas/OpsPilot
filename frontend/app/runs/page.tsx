"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

type WorkflowRunListItem = {
  id: number;
  input_text: string;
  status: string;
  workflow_type: string;
  confidence: number | null;
  created_at: string;
  updated_at: string;
  ticket_count?: number;
  human_review_required?: boolean;
};

const API_BASE_URL = "http://localhost:8000";
const NAV_ITEMS = [
  ["Dashboard", "/"],
  ["Workflows", "/workflows/new"],
  ["Runs", "/runs"],
  ["Benchmarks", "/benchmarks"],
  ["Monitoring", "/monitoring"],
  ["Incidents", "/incidents"],
] as const;

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

function statusTone(status: string) {
  if (status === "completed") {
    return "border-emerald-400/25 bg-emerald-400/10 text-emerald-200";
  }

  if (status === "failed") {
    return "border-rose-400/25 bg-rose-400/10 text-rose-200";
  }

  if (status === "needs_clarification") {
    return "border-amber-400/25 bg-amber-400/10 text-amber-200";
  }

  return "border-slate-500/30 bg-slate-500/10 text-slate-300";
}

function Badge({ children, className }: { children: React.ReactNode; className: string }) {
  return (
    <span className={`inline-flex items-center rounded-full border px-2.5 py-1 text-xs font-semibold capitalize ${className}`}>
      {children}
    </span>
  );
}

function MetricCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-3xl border border-white/10 bg-white/[0.045] p-5 shadow-xl shadow-black/15">
      <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">{label}</p>
      <p className="mt-3 text-2xl font-semibold tracking-tight text-white">{value}</p>
    </div>
  );
}

export default function RunsPage() {
  const [runs, setRuns] = useState<WorkflowRunListItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadRuns() {
      setIsLoading(true);
      setError(null);

      try {
        const response = await fetch(`${API_BASE_URL}/api/v1/workflows`);

        if (!response.ok) {
          throw new Error(`Failed to load workflow runs: ${response.status}`);
        }

        setRuns((await response.json()) as WorkflowRunListItem[]);
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : "Failed to load workflow runs.");
      } finally {
        setIsLoading(false);
      }
    }

    loadRuns();
  }, []);

  const stats = useMemo(() => {
    const completed = runs.filter((run) => run.status === "completed").length;
    const failed = runs.filter((run) => run.status === "failed").length;
    const clarification = runs.filter((run) => run.status === "needs_clarification").length;

    return {
      total: runs.length,
      completed,
      failed,
      clarification,
    };
  }, [runs]);

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
            {NAV_ITEMS.map(([item, href]) => {
              const active = item === "Runs";

              return (
                <Link
                  key={item}
                  className={`flex items-center justify-between rounded-2xl px-3 py-2.5 text-sm font-medium transition ${
                    active
                      ? "border border-sky-300/20 bg-sky-300/10 text-sky-100 shadow-lg shadow-sky-950/20"
                      : "text-slate-400 hover:bg-white/[0.045] hover:text-white"
                  }`}
                  href={href}
                >
                  <span>{item}</span>
                  {active ? <span className="h-1.5 w-1.5 rounded-full bg-sky-300" /> : null}
                </Link>
              );
            })}
          </nav>

          <div className="mt-auto rounded-3xl border border-white/10 bg-white/[0.035] p-4">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Runs History</p>
            <p className="mt-2 text-sm font-medium text-white">Workflow operations</p>
            <p className="mt-2 text-xs leading-5 text-slate-500">
              Review completed, failed, and clarification-required agent runs.
            </p>
          </div>
        </aside>

        <section className="flex w-full flex-col lg:pl-72">
          <div className="mx-auto flex w-full max-w-7xl flex-col gap-6 px-4 py-5 sm:px-6 lg:px-8 lg:py-8">
            <header className="overflow-hidden rounded-3xl border border-white/10 bg-slate-950/70 shadow-2xl shadow-black/30 backdrop-blur-xl">
              <div className="border-b border-white/10 bg-white/[0.035] px-6 py-4">
                <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-500">Workflow Runs</p>
                    <h1 className="mt-1 text-2xl font-semibold tracking-tight text-white sm:text-3xl">
                      Runs History
                    </h1>
                  </div>

                  <Link
                    href="/workflows/new"
                    className="inline-flex rounded-2xl bg-gradient-to-r from-sky-300 to-violet-400 px-5 py-3 text-sm font-bold text-slate-950 shadow-xl shadow-sky-950/30 transition hover:brightness-110"
                  >
                    New Workflow
                  </Link>
                </div>
              </div>

              <div className="px-6 py-6">
                <p className="max-w-3xl text-sm leading-7 text-slate-300">
                  Browse recent OpsPilot workflow runs, inspect their status, and jump into the full timeline,
                  generated outputs, tool calls, and evaluation metrics.
                </p>
              </div>
            </header>

            <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
              <MetricCard label="Total Runs" value={isLoading ? "..." : String(stats.total)} />
              <MetricCard label="Completed Runs" value={String(stats.completed)} />
              <MetricCard label="Failed Runs" value={String(stats.failed)} />
              <MetricCard label="Clarification Required" value={String(stats.clarification)} />
            </section>

            <section className="rounded-3xl border border-white/10 bg-slate-950/55 shadow-2xl shadow-black/25 backdrop-blur-xl">
              <div className="border-b border-white/10 px-6 py-5">
                <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">Latest First</p>
                <h2 className="mt-1 text-lg font-semibold tracking-tight text-white">Workflow Run List</h2>
              </div>

              <div className="p-6">
                {error ? (
                  <div className="rounded-2xl border border-rose-400/25 bg-rose-400/10 p-4 text-sm leading-6 text-rose-200">
                    {error}
                  </div>
                ) : isLoading ? (
                  <div className="rounded-2xl border border-white/10 bg-black/20 p-5 text-sm text-slate-400">
                    Loading workflow runs...
                  </div>
                ) : runs.length === 0 ? (
                  <div className="rounded-3xl border border-dashed border-white/12 bg-black/20 p-8 text-center">
                    <p className="text-lg font-semibold text-white">No workflow runs yet</p>
                    <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-slate-400">
                      Launch a new workflow from customer feedback and it will appear here.
                    </p>
                    <Link
                      href="/workflows/new"
                      className="mt-5 inline-flex rounded-2xl bg-gradient-to-r from-sky-300 to-violet-400 px-5 py-3 text-sm font-bold text-slate-950 shadow-xl shadow-sky-950/30 transition hover:brightness-110"
                    >
                      Create First Run
                    </Link>
                  </div>
                ) : (
                  <div className="space-y-3">
                    <div className="hidden grid-cols-[0.35fr_0.55fr_0.8fr_0.45fr_0.7fr_0.4fr_0.65fr] gap-4 px-4 text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-600 xl:grid">
                      <span>Run ID</span>
                      <span>Status</span>
                      <span>Workflow</span>
                      <span>Confidence</span>
                      <span>Created</span>
                      <span>Tickets</span>
                      <span>Human Review</span>
                    </div>

                    {runs.map((run) => (
                      <Link
                        key={run.id}
                        href={`/runs/${run.id}`}
                        className="block rounded-3xl border border-white/10 bg-black/20 p-4 shadow-xl shadow-black/10 transition hover:border-sky-300/25 hover:bg-white/[0.045]"
                      >
                        <div className="grid gap-4 xl:grid-cols-[0.35fr_0.55fr_0.8fr_0.45fr_0.7fr_0.4fr_0.65fr] xl:items-center">
                          <div>
                            <p className="text-sm font-semibold text-white">#{run.id}</p>
                            <p className="mt-1 text-xs text-slate-500 xl:hidden">Run ID</p>
                          </div>

                          <Badge className={statusTone(run.status)}>{titleize(run.status)}</Badge>

                          <div>
                            <p className="text-sm font-medium capitalize text-slate-200">{titleize(run.workflow_type)}</p>
                            <p className="mt-1 line-clamp-1 text-xs text-slate-500">{run.input_text}</p>
                          </div>

                          <p className="text-sm font-semibold text-slate-200">{percent(run.confidence)}</p>
                          <p className="text-sm text-slate-400">{dateTime(run.created_at)}</p>
                          <p className="text-sm font-semibold text-slate-200">{run.ticket_count ?? "n/a"}</p>

                          <Badge
                            className={
                              run.human_review_required
                                ? "border-amber-400/25 bg-amber-400/10 text-amber-200"
                                : "border-emerald-400/25 bg-emerald-400/10 text-emerald-200"
                            }
                          >
                            {run.human_review_required ? "Required" : "Clear"}
                          </Badge>
                        </div>
                      </Link>
                    ))}
                  </div>
                )}
              </div>
            </section>
          </div>
        </section>
      </div>
    </main>
  );
}
