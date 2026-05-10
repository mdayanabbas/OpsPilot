"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";

type FailedToolCall = {
  workflow_run_id: number;
  step_name: string;
  tool_name: string;
  provider: string;
  error_message: string | null;
  created_at: string;
};

type MonitoringSummary = {
  total_workflows: number;
  completed_workflows: number;
  failed_workflows: number;
  needs_clarification_workflows: number;
  total_tool_calls: number;
  successful_tool_calls: number;
  failed_tool_calls: number;
  fallback_count: number;
  fallback_rate: number;
  average_quality_score: number;
  average_tool_recovery_success: number;
  provider_breakdown: Record<string, number>;
  latest_failed_tool_calls: FailedToolCall[];
};

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
const NAV_ITEMS = [
  ["Dashboard", "/"],
  ["Workflows", "/workflows/new"],
  ["Runs", "/runs"],
  ["Benchmarks", "/benchmarks"],
  ["Monitoring", "/monitoring"],
  ["Incidents", "/incidents"],
] as const;

function percent(value: number | null | undefined) {
  if (value === null || value === undefined) return "n/a";
  return `${Math.round(value * 100)}%`;
}

function titleize(value: string) {
  return value.replaceAll("_", " ");
}

function dateTime(value: string) {
  return new Intl.DateTimeFormat("en", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function providerLabel(provider: string) {
  if (provider === "local" || provider === "fallback") return "LM Studio";
  if (provider === "gemini") return "Gemini";
  return titleize(provider);
}

function Badge({ children, tone = "default" }: { children: React.ReactNode; tone?: "success" | "danger" | "warning" | "default" }) {
  const toneClass = {
    success: "border-emerald-400/25 bg-emerald-400/10 text-emerald-200",
    danger: "border-rose-400/25 bg-rose-400/10 text-rose-200",
    warning: "border-amber-400/25 bg-amber-400/10 text-amber-200",
    default: "border-slate-500/30 bg-slate-500/10 text-slate-300",
  }[tone];

  return <span className={`inline-flex rounded-full border px-2.5 py-1 text-xs font-semibold capitalize ${toneClass}`}>{children}</span>;
}

function MetricCard({ label, value, hint, tone = "default" }: { label: string; value: string; hint?: string; tone?: "success" | "danger" | "warning" | "default" }) {
  const glow = {
    success: "border-emerald-300/20 bg-emerald-300/[0.06] shadow-emerald-950/20",
    danger: "border-rose-300/20 bg-rose-300/[0.06] shadow-rose-950/25",
    warning: "border-amber-300/20 bg-amber-300/[0.06] shadow-amber-950/20",
    default: "border-white/10 bg-white/[0.045] shadow-black/15",
  }[tone];

  return (
    <div className={`rounded-3xl border p-5 shadow-xl ${glow}`}>
      <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">{label}</p>
      <p className="mt-3 text-2xl font-semibold tracking-tight text-white">{value}</p>
      {hint ? <p className="mt-2 text-xs leading-5 text-slate-500">{hint}</p> : null}
    </div>
  );
}

export default function MonitoringPage() {
  const [summary, setSummary] = useState<MonitoringSummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function loadSummary() {
      setIsLoading(true);
      setError(null);

      try {
        const response = await fetch(`${API_BASE_URL}/api/v1/monitoring/summary`, { cache: "no-store" });
        if (!response.ok) {
          throw new Error(`Failed to load monitoring summary: ${response.status}`);
        }
        setSummary((await response.json()) as MonitoringSummary);
      } catch (requestError) {
        setError(requestError instanceof Error ? requestError.message : "Unable to load monitoring summary.");
      } finally {
        setIsLoading(false);
      }
    }

    loadSummary();
  }, []);

  const providerRows = useMemo(
    () =>
      Object.entries(summary?.provider_breakdown ?? {}).sort(
        ([, leftCount], [, rightCount]) => rightCount - leftCount,
      ),
    [summary],
  );

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
              const active = item === "Monitoring";
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
        </aside>

        <section className="flex w-full flex-col lg:pl-72">
          <div className="mx-auto flex w-full max-w-7xl flex-col gap-6 px-4 py-5 sm:px-6 lg:px-8 lg:py-8">
            <header className="rounded-3xl border border-white/10 bg-slate-950/70 p-6 shadow-2xl shadow-black/30 backdrop-blur-xl">
              <p className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-500">Monitoring Layer</p>
              <div className="mt-2 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
                <div>
                  <h1 className="text-3xl font-semibold tracking-tight text-white">OpsPilot Health</h1>
                  <p className="mt-3 max-w-3xl text-sm leading-7 text-slate-300">
                    Operational visibility across workflow outcomes, provider reliability, fallback usage, and latest tool failures.
                  </p>
                </div>
                <Badge tone={summary?.failed_tool_calls ? "warning" : "success"}>
                  {isLoading ? "loading" : summary?.failed_tool_calls ? "attention needed" : "healthy"}
                </Badge>
              </div>
            </header>

            {error ? (
              <div className="rounded-3xl border border-rose-400/25 bg-rose-400/10 p-5 text-sm text-rose-200">{error}</div>
            ) : null}

            <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
              <MetricCard label="Total Workflows" value={isLoading ? "..." : String(summary?.total_workflows ?? 0)} />
              <MetricCard label="Completed" value={isLoading ? "..." : String(summary?.completed_workflows ?? 0)} tone="success" />
              <MetricCard label="Failed" value={isLoading ? "..." : String(summary?.failed_workflows ?? 0)} tone={summary?.failed_workflows ? "danger" : "success"} />
              <MetricCard label="Needs Clarification" value={isLoading ? "..." : String(summary?.needs_clarification_workflows ?? 0)} tone="warning" />
            </section>

            <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
              <MetricCard label="Tool Calls" value={isLoading ? "..." : String(summary?.total_tool_calls ?? 0)} />
              <MetricCard label="Successful Calls" value={isLoading ? "..." : String(summary?.successful_tool_calls ?? 0)} tone="success" />
              <MetricCard label="Failed Calls" value={isLoading ? "..." : String(summary?.failed_tool_calls ?? 0)} tone={summary?.failed_tool_calls ? "danger" : "success"} />
              <MetricCard label="Fallback Rate" value={isLoading ? "..." : percent(summary?.fallback_rate)} tone={summary?.fallback_count ? "warning" : "success"} hint={`${summary?.fallback_count ?? 0} fallback call(s)`} />
            </section>

            <section className="grid gap-4 md:grid-cols-2">
              <MetricCard label="Avg Quality Score" value={isLoading ? "..." : percent(summary?.average_quality_score)} />
              <MetricCard label="Avg Tool Recovery" value={isLoading ? "..." : percent(summary?.average_tool_recovery_success)} tone="success" />
            </section>

            <section className="grid gap-6 xl:grid-cols-[0.8fr_1.2fr]">
              <div className="rounded-3xl border border-white/10 bg-slate-950/55 shadow-2xl shadow-black/25 backdrop-blur-xl">
                <div className="border-b border-white/10 px-6 py-5">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">Provider Breakdown</p>
                  <h2 className="mt-1 text-lg font-semibold tracking-tight text-white">Tool Calls By Provider</h2>
                </div>
                <div className="space-y-3 p-6">
                  {providerRows.length > 0 ? (
                    providerRows.map(([provider, count]) => (
                      <div key={provider} className="rounded-2xl border border-white/10 bg-black/20 p-4">
                        <div className="flex items-center justify-between gap-4">
                          <Badge tone={provider === "gemini" ? "success" : provider === "unknown" ? "default" : "warning"}>{providerLabel(provider)}</Badge>
                          <span className="text-sm font-semibold text-white">{count}</span>
                        </div>
                        <div className="mt-3 h-2 overflow-hidden rounded-full bg-white/10">
                          <div
                            className="h-full rounded-full bg-gradient-to-r from-sky-300 to-violet-400"
                            style={{ width: `${summary?.total_tool_calls ? Math.round((count / summary.total_tool_calls) * 100) : 0}%` }}
                          />
                        </div>
                      </div>
                    ))
                  ) : (
                    <p className="text-sm text-slate-500">No provider activity recorded yet.</p>
                  )}
                </div>
              </div>

              <div className="rounded-3xl border border-white/10 bg-slate-950/55 shadow-2xl shadow-black/25 backdrop-blur-xl">
                <div className="border-b border-white/10 px-6 py-5">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">Latest Failures</p>
                  <h2 className="mt-1 text-lg font-semibold tracking-tight text-white">Failed Tool Calls</h2>
                </div>
                <div className="p-6">
                  {summary?.latest_failed_tool_calls.length ? (
                    <div className="space-y-3">
                      {summary.latest_failed_tool_calls.map((failure, index) => (
                        <div key={`${failure.workflow_run_id}-${failure.step_name}-${index}`} className="rounded-3xl border border-rose-400/20 bg-rose-400/[0.06] p-4">
                          <div className="grid gap-4 lg:grid-cols-[0.5fr_0.55fr_0.5fr_1fr] lg:items-start">
                            <Link href={`/runs/${failure.workflow_run_id}`} className="text-sm font-semibold text-sky-100 hover:text-sky-200">
                              Run #{failure.workflow_run_id}
                            </Link>
                            <div>
                              <p className="text-sm font-semibold text-white">{titleize(failure.step_name)}</p>
                              <p className="mt-1 text-xs text-slate-500">{titleize(failure.tool_name)}</p>
                            </div>
                            <Badge tone={failure.provider === "gemini" ? "success" : "warning"}>{providerLabel(failure.provider)}</Badge>
                            <div>
                              <p className="text-xs leading-5 text-rose-100">{failure.error_message ?? "No error message recorded."}</p>
                              <p className="mt-2 text-xs text-slate-500">{dateTime(failure.created_at)}</p>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="rounded-2xl border border-dashed border-white/12 bg-white/[0.025] p-6 text-sm text-slate-400">
                      No failed tool calls recorded.
                    </div>
                  )}
                </div>
              </div>
            </section>
          </div>
        </section>
      </div>
    </main>
  );
}
