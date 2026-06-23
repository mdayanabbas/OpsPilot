"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

type WorkflowRun = {
  id: number;
  input_text: string;
  status: string;
  workflow_type: string;
  confidence: number | null;
  created_at: string;
  ticket_count?: number;
  human_review_required?: boolean;
};

type ApprovalStats = {
  pending_count: number;
  approved_today: number;
  rejected_today: number;
};

type MonitoringSummary = {
  total_workflows: number;
  completed_workflows: number;
  failed_workflows: number;
  needs_clarification_workflows: number;
  total_tool_calls: number;
  successful_tool_calls: number;
  failed_tool_calls: number;
  fallback_rate: number;
  average_quality_score: number;
  provider_breakdown: Record<string, number>;
};

type Incident = {
  id: number;
  title: string;
  category: string;
  severity: string;
  workflow_count: number;
  last_detected_at: string;
};

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

const NAV_ITEMS = [
  ["Overview", "/", "01"],
  ["Executive", "/dashboard", "02"],
  ["New workflow", "/workflows/new", "03"],
  ["Runs", "/runs", "04"],
  ["Approvals", "/approvals", "05"],
  ["Benchmarks", "/benchmarks", "06"],
  ["Monitoring", "/monitoring", "07"],
  ["Incidents", "/incidents", "08"],
] as const;

const EMPTY_MONITORING: MonitoringSummary = {
  total_workflows: 0,
  completed_workflows: 0,
  failed_workflows: 0,
  needs_clarification_workflows: 0,
  total_tool_calls: 0,
  successful_tool_calls: 0,
  failed_tool_calls: 0,
  fallback_rate: 0,
  average_quality_score: 0,
  provider_breakdown: {},
};

function formatDate(value: string) {
  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(new Date(value));
}

function titleize(value: string) {
  return value.replaceAll("_", " ");
}

function statusClass(status: string) {
  if (status === "completed") return "bg-emerald-300 text-emerald-950";
  if (status === "failed") return "bg-rose-300 text-rose-950";
  if (status === "needs_clarification") return "bg-amber-300 text-amber-950";
  return "bg-sky-300 text-sky-950";
}

function Metric({ index, label, value, detail, accent }: { index: string; label: string; value: string; detail: string; accent: string }) {
  return (
    <div className="group relative overflow-hidden border-r border-b border-white/[0.08] bg-[#0a0d12] p-5 transition hover:bg-[#0d1118]">
      <div className={`absolute inset-x-0 top-0 h-px ${accent}`} />
      <div className="flex items-start justify-between gap-4">
        <p className="text-[10px] font-semibold uppercase tracking-[0.19em] text-slate-500">{label}</p>
        <span className="font-mono text-[10px] text-slate-700">{index}</span>
      </div>
      <p className="mt-7 text-4xl font-medium tracking-[-0.045em] text-[#f4f2eb]">{value}</p>
      <p className="mt-2 text-xs text-slate-500">{detail}</p>
    </div>
  );
}

function Progress({ label, value, tone }: { label: string; value: number; tone: string }) {
  const safeValue = Math.max(0, Math.min(1, value || 0));
  return (
    <div>
      <div className="mb-2 flex items-center justify-between text-xs">
        <span className="text-slate-400">{label}</span>
        <span className="font-mono text-slate-500">{Math.round(safeValue * 100)}%</span>
      </div>
      <div className="h-1 overflow-hidden bg-white/[0.07]">
        <div className={`h-full ${tone}`} style={{ width: `${safeValue * 100}%` }} />
      </div>
    </div>
  );
}

export default function DashboardPage() {
  const [runs, setRuns] = useState<WorkflowRun[]>([]);
  const [approvals, setApprovals] = useState<ApprovalStats>({ pending_count: 0, approved_today: 0, rejected_today: 0 });
  const [monitoring, setMonitoring] = useState<MonitoringSummary>(EMPTY_MONITORING);
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [updatedAt, setUpdatedAt] = useState<Date | null>(null);

  const loadDashboard = useCallback(async (manual = false) => {
    if (manual) setRefreshing(true);
    setError(null);
    try {
      const responses = await Promise.all([
        fetch(`${API_BASE_URL}/api/v1/workflows`, { cache: "no-store" }),
        fetch(`${API_BASE_URL}/api/v1/approvals/stats`, { cache: "no-store" }),
        fetch(`${API_BASE_URL}/api/v1/monitoring/summary`, { cache: "no-store" }),
        fetch(`${API_BASE_URL}/api/v1/incidents`, { cache: "no-store" }),
      ]);
      if (responses.some((response) => !response.ok)) throw new Error("One or more dashboard services did not respond.");
      const [runData, approvalData, monitoringData, incidentData] = await Promise.all(responses.map((response) => response.json()));
      setRuns(runData as WorkflowRun[]);
      setApprovals(approvalData as ApprovalStats);
      setMonitoring(monitoringData as MonitoringSummary);
      setIncidents(incidentData as Incident[]);
      setUpdatedAt(new Date());
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to load the command dashboard.");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    void loadDashboard();
  }, [loadDashboard]);

  const completionRate = monitoring.total_workflows ? monitoring.completed_workflows / monitoring.total_workflows : 0;
  const toolSuccessRate = monitoring.total_tool_calls ? monitoring.successful_tool_calls / monitoring.total_tool_calls : 0;
  const providerRows = useMemo(() => Object.entries(monitoring.provider_breakdown).sort(([, a], [, b]) => b - a), [monitoring.provider_breakdown]);
  const recentRuns = runs.slice(0, 6);
  const attentionRuns = runs.filter((run) => run.human_review_required || run.status !== "completed").length;

  return (
    <main className="min-h-screen bg-[#07090d] text-slate-100 selection:bg-lime-200 selection:text-slate-950">
      <div className="fixed inset-0 pointer-events-none opacity-[0.035] [background-image:linear-gradient(rgba(255,255,255,.8)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,.8)_1px,transparent_1px)] [background-size:48px_48px]" />

      <aside className="fixed inset-y-0 left-0 z-20 hidden w-64 border-r border-white/[0.08] bg-[#080a0e]/95 px-5 py-6 backdrop-blur-xl lg:flex lg:flex-col">
        <Link href="/" className="flex items-center gap-3">
          <span className="grid h-9 w-9 place-items-center border border-lime-200/30 bg-lime-200 text-sm font-black text-[#080a0e]">OP</span>
          <span><strong className="block text-sm tracking-tight text-[#f4f2eb]">OpsPilot</strong><small className="text-[10px] uppercase tracking-[0.19em] text-slate-600">Control system</small></span>
        </Link>

        <div className="mt-10 text-[9px] font-semibold uppercase tracking-[0.22em] text-slate-700">Workspace / Primary</div>
        <nav className="mt-3 space-y-0.5">
          {NAV_ITEMS.map(([name, href, index]) => {
            const active = href === "/";
            return <Link key={href} href={href} className={`group flex items-center gap-3 border-l-2 px-3 py-2.5 text-sm transition ${active ? "border-lime-200 bg-lime-200/[0.07] text-[#f4f2eb]" : "border-transparent text-slate-500 hover:border-slate-600 hover:bg-white/[0.025] hover:text-slate-200"}`}><span className={`font-mono text-[9px] ${active ? "text-lime-200" : "text-slate-700"}`}>{index}</span><span>{name}</span>{name === "Approvals" && approvals.pending_count ? <span className="ml-auto min-w-5 bg-amber-300 px-1.5 py-0.5 text-center font-mono text-[9px] font-bold text-amber-950">{approvals.pending_count}</span> : null}</Link>;
          })}
        </nav>

        <div className="mt-auto border-t border-white/[0.08] pt-5">
          <div className="flex items-center gap-2 text-xs text-slate-500"><span className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-300" />API connected</div>
          <p className="mt-2 font-mono text-[9px] uppercase tracking-[0.16em] text-slate-700">Deterministic policies active</p>
        </div>
      </aside>

      <div className="relative lg:pl-64">
        <header className="sticky top-0 z-10 border-b border-white/[0.08] bg-[#07090d]/90 px-4 py-3 backdrop-blur-xl sm:px-7">
          <div className="mx-auto flex max-w-[1500px] items-center justify-between gap-4">
            <div className="flex min-w-0 items-center gap-3"><span className="font-mono text-[10px] uppercase tracking-[0.18em] text-slate-600">OP / 01</span><span className="h-3 w-px bg-white/10" /><span className="truncate text-xs text-slate-400">Operations overview</span></div>
            <div className="flex items-center gap-2">
              <button onClick={() => void loadDashboard(true)} disabled={refreshing} className="border border-white/10 px-3 py-2 font-mono text-[10px] uppercase tracking-wider text-slate-400 transition hover:border-white/20 hover:text-white disabled:opacity-50">{refreshing ? "Syncing…" : "Refresh"}</button>
              <Link href="/workflows/new" className="bg-lime-200 px-4 py-2 text-xs font-bold text-[#0a0c10] transition hover:bg-lime-100">Run workflow +</Link>
            </div>
          </div>
        </header>

        <div className="mx-auto max-w-[1500px] px-4 py-7 sm:px-7 lg:py-9">
          <div className="mb-6 flex gap-2 overflow-x-auto pb-1 lg:hidden">{NAV_ITEMS.map(([name, href]) => <Link key={href} href={href} className={`shrink-0 border px-3 py-2 text-xs ${href === "/" ? "border-lime-200/40 bg-lime-200/10 text-lime-100" : "border-white/10 text-slate-500"}`}>{name}</Link>)}</div>

          <section className="flex flex-col gap-6 border-b border-white/[0.08] pb-8 xl:flex-row xl:items-end xl:justify-between">
            <div>
              <div className="mb-4 flex items-center gap-2"><span className="h-2 w-2 bg-lime-200" /><p className="font-mono text-[10px] uppercase tracking-[0.22em] text-lime-200/70">Live operational state</p></div>
              <h1 className="max-w-3xl text-4xl font-medium tracking-[-0.05em] text-[#f4f2eb] sm:text-6xl">Your agents,<br /><span className="text-slate-600">under control.</span></h1>
            </div>
            <div className="max-w-md border-l border-white/10 pl-5">
              <p className="text-sm leading-6 text-slate-400">A single view of workflow throughput, human decisions, tool reliability, and operational incidents.</p>
              <p className="mt-3 font-mono text-[9px] uppercase tracking-[0.16em] text-slate-700">{updatedAt ? `Last sync ${updatedAt.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}` : "Connecting to services"}</p>
            </div>
          </section>

          {error ? <div className="mt-6 border border-rose-300/25 bg-rose-300/[0.06] p-4 text-sm text-rose-200">{error}</div> : null}

          <section className="mt-6 grid overflow-hidden border-l border-t border-white/[0.08] sm:grid-cols-2 xl:grid-cols-4">
            <Metric index="A1" label="Workflow volume" value={loading ? "—" : String(monitoring.total_workflows)} detail={`${monitoring.completed_workflows} completed`} accent="bg-sky-300" />
            <Metric index="A2" label="Completion rate" value={loading ? "—" : `${Math.round(completionRate * 100)}%`} detail={`${monitoring.failed_workflows} failed runs`} accent="bg-emerald-300" />
            <Metric index="A3" label="Awaiting approval" value={loading ? "—" : String(approvals.pending_count)} detail={`${approvals.approved_today} cleared today`} accent="bg-amber-300" />
            <Metric index="A4" label="Active incidents" value={loading ? "—" : String(incidents.length)} detail={`${attentionRuns} runs need attention`} accent="bg-rose-300" />
          </section>

          <section className="mt-6 grid gap-6 xl:grid-cols-[minmax(0,1.65fr)_minmax(320px,.85fr)]">
            <div className="border border-white/[0.08] bg-[#0a0d12]">
              <div className="flex items-center justify-between border-b border-white/[0.08] px-5 py-4"><div><p className="font-mono text-[9px] uppercase tracking-[0.2em] text-slate-600">Execution ledger</p><h2 className="mt-1 text-lg font-medium text-[#f4f2eb]">Recent workflow runs</h2></div><Link href="/runs" className="text-xs text-lime-200 hover:text-lime-100">View all →</Link></div>
              <div>
                {loading ? <div className="p-8 text-sm text-slate-600">Loading execution ledger…</div> : null}
                {!loading && !recentRuns.length ? <div className="p-8 text-sm text-slate-600">No workflow runs yet. Start the first one.</div> : null}
                {recentRuns.map((run) => <Link href={`/runs/${run.id}`} key={run.id} className="grid gap-3 border-b border-white/[0.06] px-5 py-4 transition last:border-b-0 hover:bg-white/[0.025] sm:grid-cols-[54px_minmax(0,1fr)_120px_88px] sm:items-center"><span className="font-mono text-[10px] text-slate-600">#{String(run.id).padStart(4, "0")}</span><div className="min-w-0"><p className="truncate text-sm text-slate-200">{run.input_text}</p><p className="mt-1 text-[10px] uppercase tracking-wider text-slate-600">{titleize(run.workflow_type)} · {formatDate(run.created_at)}</p></div><span className={`w-fit px-2 py-1 font-mono text-[9px] font-bold uppercase ${statusClass(run.status)}`}>{titleize(run.status)}</span><span className="text-right font-mono text-[10px] text-slate-600">{run.confidence === null ? "n/a" : `${Math.round(run.confidence * 100)}% conf.`}</span></Link>)}
              </div>
            </div>

            <div className="space-y-6">
              <Link href="/approvals" className="group block border border-amber-200/20 bg-amber-200/[0.055] p-5 transition hover:border-amber-200/40 hover:bg-amber-200/[0.08]">
                <div className="flex items-start justify-between"><div><p className="font-mono text-[9px] uppercase tracking-[0.2em] text-amber-200/60">Human gate</p><h2 className="mt-1 text-lg font-medium text-amber-50">Approval inbox</h2></div><span className="text-2xl text-amber-200 transition group-hover:translate-x-1">↗</span></div>
                <div className="mt-8 flex items-end justify-between"><span className="text-5xl font-medium tracking-[-0.06em] text-amber-100">{loading ? "—" : approvals.pending_count}</span><span className="pb-1 text-xs text-amber-200/55">waiting for a human</span></div>
                <div className="mt-5 grid grid-cols-2 border-t border-amber-100/10 pt-4 text-xs"><span className="text-amber-100/45">Approved today <strong className="ml-1 text-amber-100">{approvals.approved_today}</strong></span><span className="text-right text-amber-100/45">Rejected <strong className="ml-1 text-amber-100">{approvals.rejected_today}</strong></span></div>
              </Link>

              <div className="border border-white/[0.08] bg-[#0a0d12] p-5">
                <div className="flex items-center justify-between"><div><p className="font-mono text-[9px] uppercase tracking-[0.2em] text-slate-600">System pulse</p><h2 className="mt-1 text-lg font-medium text-[#f4f2eb]">Agent health</h2></div><Link href="/monitoring" className="text-xs text-slate-500 hover:text-white">Inspect →</Link></div>
                <div className="mt-6 space-y-5"><Progress label="Workflow completion" value={completionRate} tone="bg-emerald-300" /><Progress label="Tool success" value={toolSuccessRate} tone="bg-sky-300" /><Progress label="Output quality" value={monitoring.average_quality_score} tone="bg-violet-300" /></div>
                <div className="mt-6 flex flex-wrap gap-2 border-t border-white/[0.07] pt-4">{providerRows.length ? providerRows.map(([provider, count]) => <span key={provider} className="border border-white/[0.09] px-2 py-1 font-mono text-[9px] uppercase text-slate-500">{provider} · {count}</span>) : <span className="text-xs text-slate-600">No provider data yet.</span>}</div>
              </div>
            </div>
          </section>

          <section className="mt-6 grid gap-6 lg:grid-cols-2">
            <div className="border border-white/[0.08] bg-[#0a0d12] p-5"><div className="flex items-center justify-between"><div><p className="font-mono text-[9px] uppercase tracking-[0.2em] text-slate-600">Incident watch</p><h2 className="mt-1 text-lg font-medium text-[#f4f2eb]">Operational signals</h2></div><Link href="/incidents" className="text-xs text-slate-500 hover:text-white">All incidents →</Link></div><div className="mt-5 space-y-2">{incidents.slice(0, 3).map((incident) => <Link key={incident.id} href="/incidents" className="flex items-center gap-3 border border-white/[0.06] p-3 hover:bg-white/[0.025]"><span className={`h-2 w-2 ${incident.severity === "critical" ? "bg-rose-300" : incident.severity === "high" ? "bg-orange-300" : "bg-amber-300"}`} /><div className="min-w-0 flex-1"><p className="truncate text-sm text-slate-300">{incident.title}</p><p className="mt-1 font-mono text-[9px] uppercase text-slate-600">{incident.category} · {incident.workflow_count} workflows</p></div><span className="font-mono text-[9px] uppercase text-slate-600">{incident.severity}</span></Link>)}{!incidents.length ? <p className="py-5 text-sm text-slate-600">No active incident signals.</p> : null}</div></div>
            <div className="border border-white/[0.08] bg-[#0a0d12] p-5"><p className="font-mono text-[9px] uppercase tracking-[0.2em] text-slate-600">Quick launch</p><h2 className="mt-1 text-lg font-medium text-[#f4f2eb]">Move work forward</h2><div className="mt-5 grid gap-2 sm:grid-cols-2"><Link href="/workflows/new" className="border border-lime-200/20 bg-lime-200/[0.05] p-4 hover:border-lime-200/40"><span className="font-mono text-[9px] text-lime-200/60">01 / EXECUTE</span><p className="mt-5 text-sm font-medium text-lime-50">Start a workflow →</p></Link><Link href="/approvals" className="border border-white/[0.08] p-4 hover:bg-white/[0.025]"><span className="font-mono text-[9px] text-slate-600">02 / REVIEW</span><p className="mt-5 text-sm font-medium text-slate-200">Open approval queue →</p></Link><Link href="/benchmarks" className="border border-white/[0.08] p-4 hover:bg-white/[0.025]"><span className="font-mono text-[9px] text-slate-600">03 / MEASURE</span><p className="mt-5 text-sm font-medium text-slate-200">Run regression →</p></Link><Link href="/monitoring" className="border border-white/[0.08] p-4 hover:bg-white/[0.025]"><span className="font-mono text-[9px] text-slate-600">04 / OBSERVE</span><p className="mt-5 text-sm font-medium text-slate-200">Inspect health →</p></Link></div></div>
          </section>
        </div>
      </div>
    </main>
  );
}
