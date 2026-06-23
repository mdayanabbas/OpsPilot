"use client";

import { useCallback, useEffect, useState } from "react";

type ActivityType = "workflow" | "incident" | "approval" | "benchmark";

type ExecutiveSummary = {
  workflows_today: number;
  total_workflows: number;
  completed_workflows: number;
  needs_clarification: number;
  automation_rate: number;
  human_review_rate: number;
  open_incidents: number;
  critical_incidents: number;
  high_incidents: number;
  top_incident_category: string | null;
  pending_approvals: number;
  approved_today: number;
  rejected_today: number;
  latest_benchmark_score: number | null;
  benchmark_trend: number | null;
  fallback_rate: number;
  critic_warning_rate: number;
  top_risks: string[];
  recent_activity: Array<{
    type: ActivityType;
    title: string;
    description: string;
    created_at: string;
  }>;
};

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

function percent(value: number | null) {
  return value === null ? "—" : `${Math.round(value * 100)}%`;
}

function signedPercent(value: number | null) {
  if (value === null) return "No prior run";
  const points = value * 100;
  return `${points >= 0 ? "+" : ""}${points.toFixed(1)} pts`;
}

function dateTime(value: string) {
  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(new Date(value));
}

function Kpi({ code, label, value, detail, color }: { code: string; label: string; value: string; detail: string; color: string }) {
  return (
    <article className="relative overflow-hidden border-r border-b border-white/[0.08] bg-[#0a0d12] p-5">
      <div className={`absolute inset-x-0 top-0 h-px ${color}`} />
      <div className="flex justify-between gap-4"><p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-500">{label}</p><span className="font-mono text-[9px] text-slate-700">{code}</span></div>
      <p className="mt-7 text-4xl font-medium tracking-[-0.05em] text-[#f4f2eb]">{value}</p>
      <p className="mt-2 text-xs text-slate-600">{detail}</p>
    </article>
  );
}

const ACTIVITY_STYLE: Record<ActivityType, { marker: string; label: string }> = {
  workflow: { marker: "bg-sky-300", label: "Workflow" },
  incident: { marker: "bg-rose-300", label: "Incident" },
  approval: { marker: "bg-amber-300", label: "Approval" },
  benchmark: { marker: "bg-violet-300", label: "Benchmark" },
};

export default function ExecutiveDashboardPage() {
  const [summary, setSummary] = useState<ExecutiveSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async (manual = false) => {
    if (manual) setRefreshing(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/monitoring/executive-summary`, { cache: "no-store" });
      if (!response.ok) throw new Error(`Executive summary unavailable: ${response.status}`);
      setSummary((await response.json()) as ExecutiveSummary);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to load executive summary.");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const systemStatus = !summary
    ? "Connecting to operational services"
    : summary.critical_incidents
      ? "Critical attention required"
      : summary.high_incidents || summary.fallback_rate >= 0.1 || summary.critic_warning_rate >= 0.25
        ? "Operating with elevated risk"
        : "All core systems are operating within policy";

  return (
    <main className="min-h-[calc(100vh-56px)] bg-transparent text-slate-100">
      <div className="mx-auto max-w-[1500px] px-4 py-7 sm:px-7 lg:py-9">
        <section className="flex flex-col gap-6 border-b border-white/[0.08] pb-8 xl:flex-row xl:items-end xl:justify-between">
          <div>
            <div className="mb-4 flex items-center gap-2"><span className={`h-2 w-2 ${summary?.critical_incidents ? "bg-rose-300" : "bg-lime-200"}`} /><p className="font-mono text-[10px] uppercase tracking-[0.22em] text-lime-200/70">Executive operations / live</p></div>
            <h1 className="text-4xl font-medium tracking-[-0.05em] text-[#f4f2eb] sm:text-6xl">OpsPilot<br /><span className="text-slate-600">Control Center.</span></h1>
          </div>
          <div className="max-w-lg border-l border-white/10 pl-5">
            <p className="text-sm leading-6 text-slate-300">{systemStatus}</p>
            <div className="mt-4 flex flex-wrap gap-x-5 gap-y-2 font-mono text-[9px] uppercase tracking-[0.15em] text-slate-600"><span>{summary?.total_workflows ?? 0} lifetime workflows</span><span>{summary?.completed_workflows ?? 0} completed</span><button onClick={() => void load(true)} disabled={refreshing} className="text-lime-200/65 hover:text-lime-100 disabled:opacity-40">{refreshing ? "Syncing…" : "Refresh data"}</button></div>
          </div>
        </section>

        {error ? <div className="mt-6 border border-rose-300/25 bg-rose-300/[0.06] p-4 text-sm text-rose-100">{error}</div> : null}

        <section className="mt-6 grid overflow-hidden border-l border-t border-white/[0.08] sm:grid-cols-2 xl:grid-cols-6">
          <Kpi code="K1" label="Workflows today" value={loading ? "—" : String(summary?.workflows_today ?? 0)} detail={`${summary?.needs_clarification ?? 0} need clarification`} color="bg-sky-300" />
          <Kpi code="K2" label="Automation rate" value={loading ? "—" : percent(summary?.automation_rate ?? 0)} detail="Completed without review" color="bg-emerald-300" />
          <Kpi code="K3" label="Human review rate" value={loading ? "—" : percent(summary?.human_review_rate ?? 0)} detail="Of completed workflows" color="bg-amber-300" />
          <Kpi code="K4" label="Open incidents" value={loading ? "—" : String(summary?.open_incidents ?? 0)} detail={`${summary?.critical_incidents ?? 0} critical · ${summary?.high_incidents ?? 0} high`} color="bg-rose-300" />
          <Kpi code="K5" label="Pending approvals" value={loading ? "—" : String(summary?.pending_approvals ?? 0)} detail={`${summary?.approved_today ?? 0} approved today`} color="bg-orange-300" />
          <Kpi code="K6" label="Benchmark score" value={loading ? "—" : percent(summary?.latest_benchmark_score ?? null)} detail={signedPercent(summary?.benchmark_trend ?? null)} color="bg-violet-300" />
        </section>

        <section className="mt-6 grid gap-6 xl:grid-cols-[minmax(320px,.8fr)_minmax(0,1.35fr)]">
          <div className="border border-white/[0.08] bg-[#0a0d12]">
            <div className="border-b border-white/[0.08] px-5 py-4"><p className="font-mono text-[9px] uppercase tracking-[0.2em] text-rose-200/55">Risk register</p><h2 className="mt-1 text-lg font-medium text-[#f4f2eb]">Operational Risk</h2></div>
            <div className="p-5">
              <div className="space-y-2">{summary?.top_risks.map((risk, index) => <div key={`${risk}-${index}`} className="grid grid-cols-[28px_1fr] border border-white/[0.06] p-3"><span className="font-mono text-[9px] text-rose-300/65">R{index + 1}</span><p className="text-sm leading-6 text-slate-300">{risk}</p></div>)}{loading ? <p className="py-5 text-sm text-slate-600">Calculating operational exposure…</p> : null}</div>
              <div className="mt-6 grid grid-cols-3 border-l border-t border-white/[0.07]">
                <div className="border-r border-b border-white/[0.07] p-3"><p className="text-[9px] uppercase tracking-wider text-slate-600">Top category</p><p className="mt-2 truncate text-sm capitalize text-slate-200">{summary?.top_incident_category ?? "None"}</p></div>
                <div className="border-r border-b border-white/[0.07] p-3"><p className="text-[9px] uppercase tracking-wider text-slate-600">Fallback</p><p className="mt-2 text-sm text-slate-200">{percent(summary?.fallback_rate ?? 0)}</p></div>
                <div className="border-r border-b border-white/[0.07] p-3"><p className="text-[9px] uppercase tracking-wider text-slate-600">Critic warning</p><p className="mt-2 text-sm text-slate-200">{percent(summary?.critic_warning_rate ?? 0)}</p></div>
              </div>
            </div>
          </div>

          <div className="border border-white/[0.08] bg-[#0a0d12]">
            <div className="flex items-center justify-between border-b border-white/[0.08] px-5 py-4"><div><p className="font-mono text-[9px] uppercase tracking-[0.2em] text-slate-600">Cross-system ledger</p><h2 className="mt-1 text-lg font-medium text-[#f4f2eb]">Recent Activity</h2></div><span className="font-mono text-[9px] uppercase text-slate-700">Newest first</span></div>
            <div>
              {summary?.recent_activity.map((activity, index) => { const style = ACTIVITY_STYLE[activity.type]; return <article key={`${activity.type}-${activity.created_at}-${index}`} className="grid gap-3 border-b border-white/[0.06] px-5 py-4 last:border-b-0 sm:grid-cols-[100px_minmax(0,1fr)_110px] sm:items-center"><div className="flex items-center gap-2"><span className={`h-1.5 w-1.5 ${style.marker}`} /><span className="font-mono text-[9px] uppercase tracking-wider text-slate-500">{style.label}</span></div><div className="min-w-0"><h3 className="truncate text-sm font-medium text-slate-200">{activity.title}</h3><p className="mt-1 truncate text-xs text-slate-600">{activity.description}</p></div><time className="font-mono text-[9px] uppercase text-slate-700 sm:text-right">{dateTime(activity.created_at)}</time></article>; })}
              {!loading && !summary?.recent_activity.length ? <p className="p-8 text-sm text-slate-600">No recent operational activity.</p> : null}
              {loading ? <p className="p-8 text-sm text-slate-600">Loading activity ledger…</p> : null}
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}
