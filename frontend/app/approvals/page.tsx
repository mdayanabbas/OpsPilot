"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

type ApprovalStatus = "pending" | "approved" | "rejected";
type ApprovalType = "reply" | "ticket" | "incident_action";

type ApprovalComment = {
  id: number;
  reviewer: string;
  comment: string;
  created_at: string;
};

type ApprovalItem = {
  id: number;
  approval_id: number;
  workflow_run_id: number;
  item_type: ApprovalType;
  item_id: number;
  status: ApprovalStatus;
  risk: "low" | "medium" | "high";
  title: string;
  summary: string | null;
  reviewer_note: string | null;
  created_at: string;
  reviewed_at: string | null;
  decided_at: string | null;
  comments: ApprovalComment[];
};

type ApprovalQueue = Record<ApprovalStatus, ApprovalItem[]>;
type ApprovalStats = {
  pending_count: number;
  approved_today: number;
  rejected_today: number;
};

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

const NAV_ITEMS = [
  ["Dashboard", "/"],
  ["Runs", "/runs"],
  ["Approvals", "/approvals"],
  ["Benchmarks", "/benchmarks"],
  ["Monitoring", "/monitoring"],
  ["Incidents", "/incidents"],
] as const;

function formatDate(value: string | null) {
  if (!value) return "Awaiting review";
  return new Intl.DateTimeFormat("en", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function label(value: string) {
  return value.replaceAll("_", " ");
}

function Badge({ value, kind }: { value: string; kind: "status" | "risk" | "type" }) {
  const colors =
    kind === "status"
      ? {
          pending: "border-amber-400/30 bg-amber-400/10 text-amber-200",
          approved: "border-emerald-400/30 bg-emerald-400/10 text-emerald-200",
          rejected: "border-rose-400/30 bg-rose-400/10 text-rose-200",
        }[value]
      : kind === "risk"
        ? {
            high: "border-rose-400/30 bg-rose-400/10 text-rose-200",
            medium: "border-amber-400/30 bg-amber-400/10 text-amber-200",
            low: "border-cyan-400/30 bg-cyan-400/10 text-cyan-200",
          }[value]
        : "border-slate-500/30 bg-slate-500/10 text-slate-300";

  return (
    <span className={`rounded-full border px-2.5 py-1 text-[10px] font-bold uppercase tracking-[0.14em] ${colors}`}>
      {kind === "risk" ? `${value} risk` : label(value)}
    </span>
  );
}

function Metric({ label: metricLabel, value, tone }: { label: string; value: number; tone: string }) {
  return (
    <div className="relative overflow-hidden rounded-3xl border border-white/10 bg-white/[0.045] p-5 shadow-2xl shadow-black/20">
      <div className={`absolute -right-8 -top-8 h-24 w-24 rounded-full blur-3xl ${tone}`} />
      <p className="relative text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">{metricLabel}</p>
      <p className="relative mt-3 text-3xl font-semibold tracking-tight text-white">{value}</p>
    </div>
  );
}

function Timeline({ item }: { item: ApprovalItem }) {
  const final = item.status !== "pending";
  const steps = [
    { name: "Created", date: item.created_at, done: true },
    { name: "Reviewed", date: item.reviewed_at, done: Boolean(item.reviewed_at) || final },
    { name: final ? label(item.status) : "Decision", date: item.decided_at, done: final },
  ];

  return (
    <div className="mt-5 grid grid-cols-3 gap-2 border-t border-white/8 pt-5">
      {steps.map((step, index) => (
        <div className="relative" key={step.name}>
          {index < steps.length - 1 ? (
            <div className={`absolute left-4 top-2 h-px w-[calc(100%-0.5rem)] ${steps[index + 1].done ? "bg-cyan-300/40" : "bg-white/10"}`} />
          ) : null}
          <div className={`relative h-4 w-4 rounded-full border-4 border-[#0b1018] ${step.done ? "bg-cyan-300" : "bg-slate-700"}`} />
          <p className={`mt-2 text-xs font-semibold capitalize ${step.done ? "text-slate-200" : "text-slate-600"}`}>{step.name}</p>
          <p className="mt-1 text-[10px] leading-4 text-slate-600">{step.date ? formatDate(step.date) : "—"}</p>
        </div>
      ))}
    </div>
  );
}

export default function ApprovalsPage() {
  const [queue, setQueue] = useState<ApprovalQueue>({ pending: [], approved: [], rejected: [] });
  const [stats, setStats] = useState<ApprovalStats>({ pending_count: 0, approved_today: 0, rejected_today: 0 });
  const [statusFilter, setStatusFilter] = useState<"all" | ApprovalStatus>("pending");
  const [typeFilter, setTypeFilter] = useState<"all" | ApprovalType>("all");
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [commentingId, setCommentingId] = useState<number | null>(null);
  const [comment, setComment] = useState("");
  const [reviewer, setReviewer] = useState("Ops reviewer");
  const [visibleLimit, setVisibleLimit] = useState(24);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setError(null);
      const [queueResponse, statsResponse] = await Promise.all([
        fetch(`${API_BASE_URL}/api/v1/approvals/queue`, { cache: "no-store" }),
        fetch(`${API_BASE_URL}/api/v1/approvals/stats`, { cache: "no-store" }),
      ]);
      if (!queueResponse.ok || !statsResponse.ok) throw new Error("Unable to load the approval workspace.");
      setQueue(await queueResponse.json());
      setStats(await statsResponse.json());
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to load approvals.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const visibleItems = useMemo(() => {
    const items = statusFilter === "all" ? [...queue.pending, ...queue.approved, ...queue.rejected] : queue[statusFilter];
    return typeFilter === "all" ? items : items.filter((item) => item.item_type === typeFilter);
  }, [queue, statusFilter, typeFilter]);
  const displayedItems = visibleItems.slice(0, visibleLimit);

  useEffect(() => {
    setVisibleLimit(24);
  }, [statusFilter, typeFilter]);

  async function decide(item: ApprovalItem, decision: "approve" | "reject") {
    setBusyId(item.id);
    setError(null);
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/approvals/${decision}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          workflow_run_id: item.workflow_run_id,
          item_type: item.item_type,
          item_id: item.item_id,
          reviewer_note: null,
        }),
      });
      if (!response.ok) throw new Error((await response.text()) || `Unable to ${decision} item.`);
      await load();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Decision failed.");
    } finally {
      setBusyId(null);
    }
  }

  async function addComment(item: ApprovalItem) {
    if (!reviewer.trim() || !comment.trim()) return;
    setBusyId(item.id);
    setError(null);
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/approvals/comment`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ approval_id: item.approval_id, reviewer, comment }),
      });
      if (!response.ok) throw new Error((await response.text()) || "Unable to save comment.");
      setComment("");
      setCommentingId(null);
      await load();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Comment failed.");
    } finally {
      setBusyId(null);
    }
  }

  return (
    <main className="min-h-screen bg-[#05070b] text-slate-100">
      <div className="pointer-events-none fixed inset-0 bg-[radial-gradient(circle_at_18%_0%,rgba(34,211,238,0.09),transparent_32%),radial-gradient(circle_at_88%_16%,rgba(139,92,246,0.08),transparent_28%)]" />
      <div className="relative mx-auto max-w-7xl px-5 py-8 lg:px-8">
        <nav className="mb-10 flex flex-wrap items-center justify-between gap-5">
          <Link href="/" className="text-lg font-bold tracking-tight text-white">OpsPilot <span className="text-cyan-300">/</span> Control</Link>
          <div className="flex flex-wrap gap-1 rounded-2xl border border-white/10 bg-white/[0.035] p-1.5">
            {NAV_ITEMS.map(([name, href]) => (
              <Link key={href} href={href} className={`rounded-xl px-3 py-2 text-xs font-semibold transition ${href === "/approvals" ? "bg-cyan-300/12 text-cyan-200" : "text-slate-500 hover:text-white"}`}>{name}</Link>
            ))}
          </div>
        </nav>

        <header className="max-w-3xl">
          <p className="text-xs font-bold uppercase tracking-[0.24em] text-cyan-300">Human Approval Center</p>
          <h1 className="mt-3 text-4xl font-semibold tracking-[-0.035em] text-white sm:text-5xl">Decisions with context.</h1>
          <p className="mt-4 max-w-2xl text-sm leading-7 text-slate-400">Review customer-facing work, document judgment, and keep a clean decision trail from one operational workspace.</p>
        </header>

        <section className="mt-10">
          <div className="mb-4 flex items-center justify-between"><h2 className="text-lg font-semibold text-white">Approval Summary</h2><span className="text-xs text-slate-600">Live queue totals</span></div>
          <div className="grid gap-4 sm:grid-cols-3">
            <Metric label="Pending" value={stats.pending_count} tone="bg-amber-400/20" />
            <Metric label="Approved Today" value={stats.approved_today} tone="bg-emerald-400/20" />
            <Metric label="Rejected Today" value={stats.rejected_today} tone="bg-rose-400/20" />
          </div>
        </section>

        <section className="mt-10">
          <div className="flex flex-col justify-between gap-4 lg:flex-row lg:items-end">
            <div><h2 className="text-lg font-semibold text-white">Approval Queue</h2><p className="mt-1 text-xs text-slate-500">{visibleItems.length} items in this view</p></div>
            <div className="flex flex-wrap gap-3">
              <div className="flex rounded-xl border border-white/10 bg-black/20 p-1">
                {(["all", "pending", "approved", "rejected"] as const).map((status) => <button key={status} onClick={() => setStatusFilter(status)} className={`rounded-lg px-3 py-2 text-xs font-semibold capitalize ${statusFilter === status ? "bg-white/10 text-white" : "text-slate-500 hover:text-slate-300"}`}>{status}</button>)}
              </div>
              <select value={typeFilter} onChange={(event) => setTypeFilter(event.target.value as typeof typeFilter)} className="rounded-xl border border-white/10 bg-[#0a0e15] px-4 py-2 text-xs font-semibold text-slate-300 outline-none focus:border-cyan-400/40">
                <option value="all">All types</option><option value="reply">Reply</option><option value="ticket">Ticket</option><option value="incident_action">Incident</option>
              </select>
            </div>
          </div>

          {error ? <div className="mt-5 rounded-2xl border border-rose-400/25 bg-rose-400/10 p-4 text-sm text-rose-100">{error}</div> : null}

          <div className="mt-5 grid gap-5 lg:grid-cols-2">
            {loading ? <div className="col-span-full rounded-3xl border border-white/10 bg-white/[0.03] p-10 text-center text-sm text-slate-500">Loading approval queue…</div> : null}
            {!loading && visibleItems.length === 0 ? <div className="col-span-full rounded-3xl border border-dashed border-white/10 bg-white/[0.025] p-12 text-center"><p className="font-semibold text-slate-300">Nothing needs attention here.</p><p className="mt-2 text-sm text-slate-600">Try another status or item type.</p></div> : null}
            {displayedItems.map((item) => (
              <article key={item.id} className="rounded-3xl border border-white/10 bg-[#0a0e15]/95 p-6 shadow-2xl shadow-black/25 transition hover:border-white/15">
                <div className="flex flex-wrap items-center gap-2"><Badge value={item.item_type} kind="type" /><Badge value={item.status} kind="status" /><Badge value={item.risk} kind="risk" /></div>
                <h3 className="mt-5 line-clamp-2 text-lg font-semibold leading-7 text-white">{item.title}</h3>
                {item.summary ? <p className="mt-3 line-clamp-3 text-sm leading-6 text-slate-400">{item.summary}</p> : null}
                <div className="mt-4 flex items-center justify-between text-xs text-slate-600"><span>Approval #{item.id}</span><Link href={`/runs/${item.workflow_run_id}`} className="text-cyan-300/80 hover:text-cyan-200">Run #{item.workflow_run_id} ↗</Link></div>

                <Timeline item={item} />

                {item.comments.length ? <div className="mt-5 space-y-2">{item.comments.map((entry) => <div key={entry.id} className="rounded-2xl border border-white/8 bg-white/[0.03] p-3"><div className="flex justify-between gap-3 text-[10px] uppercase tracking-wider text-slate-600"><span>{entry.reviewer}</span><span>{formatDate(entry.created_at)}</span></div><p className="mt-2 text-xs leading-5 text-slate-300">{entry.comment}</p></div>)}</div> : null}

                {commentingId === item.id ? <div className="mt-4 space-y-2 rounded-2xl border border-cyan-400/15 bg-cyan-400/[0.035] p-3"><input value={reviewer} onChange={(event) => setReviewer(event.target.value)} placeholder="Reviewer" className="w-full rounded-xl border border-white/10 bg-black/25 px-3 py-2 text-xs text-white outline-none focus:border-cyan-300/40" /><textarea value={comment} onChange={(event) => setComment(event.target.value)} placeholder="Add review context…" rows={3} className="w-full resize-none rounded-xl border border-white/10 bg-black/25 px-3 py-2 text-xs leading-5 text-white outline-none focus:border-cyan-300/40" /><button disabled={busyId === item.id || !comment.trim()} onClick={() => void addComment(item)} className="rounded-xl bg-cyan-300 px-4 py-2 text-xs font-bold text-slate-950 disabled:opacity-50">Save comment</button></div> : null}

                <div className="mt-5 flex flex-wrap gap-2 border-t border-white/8 pt-5">
                  {item.status === "pending" ? <><button disabled={busyId === item.id} onClick={() => void decide(item, "approve")} className="flex-1 rounded-xl border border-emerald-400/25 bg-emerald-400/10 px-4 py-2.5 text-xs font-bold text-emerald-200 hover:bg-emerald-400/15 disabled:opacity-50">Approve</button><button disabled={busyId === item.id} onClick={() => void decide(item, "reject")} className="flex-1 rounded-xl border border-rose-400/25 bg-rose-400/10 px-4 py-2.5 text-xs font-bold text-rose-200 hover:bg-rose-400/15 disabled:opacity-50">Reject</button></> : null}
                  <button onClick={() => setCommentingId(commentingId === item.id ? null : item.id)} className="rounded-xl border border-white/10 bg-white/[0.04] px-4 py-2.5 text-xs font-bold text-slate-300 hover:bg-white/[0.07]">Comment</button>
                </div>
              </article>
            ))}
          </div>
          {displayedItems.length < visibleItems.length ? <div className="mt-6 flex justify-center"><button onClick={() => setVisibleLimit((value) => value + 24)} className="rounded-xl border border-white/10 bg-white/[0.04] px-5 py-3 text-xs font-bold text-slate-300 hover:bg-white/[0.07]">Show 24 more</button></div> : null}
        </section>
      </div>
    </main>
  );
}
