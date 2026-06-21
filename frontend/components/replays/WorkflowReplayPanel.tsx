"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";


type ReplayChange = {
  field: string;
  before: unknown;
  after: unknown;
};

type WorkflowReplay = {
  replay_id: number;
  source_workflow_run_id: number;
  replay_workflow_run_id: number;
  status: string;
  changed: boolean;
  diff_summary: string;
  changes: ReplayChange[];
  created_at: string;
};

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

function valueLabel(value: unknown) {
  if (value === null || value === undefined) return "None";
  if (typeof value === "boolean") return value ? "True" : "False";
  return String(value);
}

function dateTime(value: string) {
  return new Intl.DateTimeFormat("en", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export function WorkflowReplayPanel({ workflowRunId }: { workflowRunId: number }) {
  const router = useRouter();
  const [history, setHistory] = useState<WorkflowReplay[]>([]);
  const [latestReplay, setLatestReplay] = useState<WorkflowReplay | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isReplaying, setIsReplaying] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function loadHistory() {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/workflows/${workflowRunId}/replays`,
      { cache: "no-store" },
    );
    if (!response.ok) throw new Error(`Failed to load replay history: ${response.status}`);
    const loaded = (await response.json()) as WorkflowReplay[];
    setHistory(loaded);
  }

  useEffect(() => {
    loadHistory()
      .catch((requestError) => setError(requestError instanceof Error ? requestError.message : "Unable to load replay history."))
      .finally(() => setIsLoading(false));
  }, [workflowRunId]);

  async function replayWorkflow() {
    setIsReplaying(true);
    setError(null);
    try {
      const response = await fetch(
        `${API_BASE_URL}/api/v1/workflows/${workflowRunId}/replay`,
        { method: "POST" },
      );
      if (!response.ok) throw new Error(`Replay failed: ${response.status}`);
      const replay = (await response.json()) as WorkflowReplay;
      setLatestReplay(replay);
      await loadHistory();
      router.refresh();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to replay workflow.");
    } finally {
      setIsReplaying(false);
    }
  }

  return (
    <section className="rounded-3xl border border-white/10 bg-slate-950/55 shadow-2xl shadow-black/25 backdrop-blur-xl">
      <div className="flex flex-col gap-4 border-b border-white/10 px-6 py-5 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-violet-300/70">Observational time travel v1</p>
          <h2 className="mt-1 text-lg font-semibold tracking-tight text-white">Workflow Replay</h2>
          <p className="mt-2 text-xs leading-5 text-slate-500">Re-run the same input against current prompts, models, memory, and planner behavior.</p>
        </div>
        <button
          type="button"
          disabled={isReplaying}
          onClick={replayWorkflow}
          className="rounded-xl border border-violet-300/25 bg-violet-300/10 px-4 py-2.5 text-xs font-semibold text-violet-100 transition hover:bg-violet-300/15 disabled:cursor-wait disabled:opacity-60"
        >
          {isReplaying ? "Replaying workflow..." : "Replay Workflow"}
        </button>
      </div>

      <div className="space-y-6 p-6">
        {error ? <div className="rounded-2xl border border-rose-300/20 bg-rose-300/10 p-4 text-sm text-rose-100">{error}</div> : null}

        {latestReplay ? (
          <div className="rounded-3xl border border-violet-300/20 bg-violet-300/[0.055] p-5">
            <div className="flex flex-wrap items-center gap-2">
              <span className={`rounded-full border px-2.5 py-1 text-xs font-semibold ${latestReplay.changed ? "border-amber-300/25 bg-amber-300/10 text-amber-100" : "border-emerald-300/25 bg-emerald-300/10 text-emerald-100"}`}>
                {latestReplay.changed ? "Changed" : "Unchanged"}
              </span>
              <span className="text-xs text-slate-500">Source #{latestReplay.source_workflow_run_id}</span>
              <Link className="text-xs font-semibold text-sky-200 hover:text-sky-100" href={`/runs/${latestReplay.replay_workflow_run_id}`}>
                Replay #{latestReplay.replay_workflow_run_id}
              </Link>
            </div>
            <p className="mt-4 text-sm leading-7 text-slate-200">{latestReplay.diff_summary}</p>
            {latestReplay.changes.length ? (
              <div className="mt-4 grid gap-3 lg:grid-cols-2">
                {latestReplay.changes.map((change) => (
                  <div key={change.field} className="rounded-2xl border border-white/10 bg-black/20 p-4">
                    <p className="font-mono text-xs font-semibold text-violet-100">{change.field}</p>
                    <div className="mt-3 grid grid-cols-2 gap-3 text-xs">
                      <div><p className="text-slate-600">Before</p><p className="mt-1 break-words text-slate-300">{valueLabel(change.before)}</p></div>
                      <div><p className="text-slate-600">After</p><p className="mt-1 break-words text-white">{valueLabel(change.after)}</p></div>
                    </div>
                  </div>
                ))}
              </div>
            ) : null}
          </div>
        ) : null}

        <div>
          <h3 className="text-sm font-semibold text-white">Replay History</h3>
          <div className="mt-3 space-y-3">
            {isLoading ? (
              <div className="rounded-2xl border border-white/10 bg-black/20 p-4 text-sm text-slate-400">Loading replay history...</div>
            ) : history.length ? history.map((replay) => (
              <div key={replay.replay_id} className="flex flex-col gap-3 rounded-2xl border border-white/10 bg-black/20 p-4 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <Link className="font-semibold text-sky-200 hover:text-sky-100" href={`/runs/${replay.replay_workflow_run_id}`}>Replay run #{replay.replay_workflow_run_id}</Link>
                    <span className={`rounded-full border px-2 py-0.5 text-[11px] font-semibold ${replay.changed ? "border-amber-300/25 bg-amber-300/10 text-amber-100" : "border-emerald-300/25 bg-emerald-300/10 text-emerald-100"}`}>
                      {replay.changed ? "Changed" : "Unchanged"}
                    </span>
                  </div>
                  <p className="mt-2 text-xs leading-5 text-slate-400">{replay.diff_summary}</p>
                </div>
                <span className="shrink-0 text-xs text-slate-500">{dateTime(replay.created_at)}</span>
              </div>
            )) : (
              <div className="rounded-2xl border border-dashed border-white/10 bg-black/15 p-4 text-sm text-slate-400">No replays recorded for this run.</div>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}
