"use client";

import Link from "next/link";
import { useEffect, useState } from "react";


type RegressionRun = {
  id: number;
  suite_name: string;
  cases_run: number;
  avg_score: number;
  planner_accuracy: number;
  category_accuracy: number;
  priority_accuracy: number;
  critic_accuracy: number;
  created_at: string;
};

type RegressionResult = {
  id: number;
  benchmark_case_id: string;
  workflow_run_id: number | null;
  total_score: number;
  passed: boolean;
  mismatches: string[];
  created_at: string;
};

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

function percent(value: number | null | undefined) {
  if (value === null || value === undefined) return "n/a";
  return `${Math.round(value * 100)}%`;
}

function dateTime(value: string) {
  return new Intl.DateTimeFormat("en", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-3xl border border-white/10 bg-black/20 p-5 shadow-xl shadow-black/15">
      <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">{label}</p>
      <p className="mt-3 text-2xl font-semibold tracking-tight text-white">{value}</p>
    </div>
  );
}

export function RegressionDashboard() {
  const [history, setHistory] = useState<RegressionRun[]>([]);
  const [results, setResults] = useState<RegressionResult[]>([]);
  const [latest, setLatest] = useState<RegressionRun | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isRunning, setIsRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function loadRegressionData() {
    const [historyResponse, resultsResponse] = await Promise.all([
      fetch(`${API_BASE_URL}/api/v1/benchmarks/regression-history`, { cache: "no-store" }),
      fetch(`${API_BASE_URL}/api/v1/benchmarks/results`, { cache: "no-store" }),
    ]);
    if (!historyResponse.ok || !resultsResponse.ok) {
      throw new Error("Failed to load regression benchmark data.");
    }
    const loadedHistory = (await historyResponse.json()) as RegressionRun[];
    setHistory(loadedHistory);
    setLatest(loadedHistory[0] ?? null);
    setResults((await resultsResponse.json()) as RegressionResult[]);
  }

  useEffect(() => {
    loadRegressionData()
      .catch((requestError) => setError(requestError instanceof Error ? requestError.message : "Unable to load regression data."))
      .finally(() => setIsLoading(false));
  }, []);

  async function runRegression() {
    setIsRunning(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/benchmarks/run-regression`, { method: "POST" });
      if (!response.ok) throw new Error(`Regression run failed: ${response.status}`);
      const run = (await response.json()) as RegressionRun;
      setLatest(run);
      await loadRegressionData();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Regression run failed.");
    } finally {
      setIsRunning(false);
    }
  }

  return (
    <section className="overflow-hidden rounded-3xl border border-violet-300/15 bg-slate-950/60 shadow-2xl shadow-black/25 backdrop-blur-xl">
      <div className="flex flex-col gap-4 border-b border-white/10 bg-violet-300/[0.035] px-6 py-5 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-violet-300/70">Deterministic system evaluation</p>
          <h2 className="mt-1 text-lg font-semibold tracking-tight text-white">Regression Summary</h2>
          <p className="mt-2 text-xs leading-5 text-slate-500">15 reusable workflow cases · six persisted-output checks per case · no LLM judge</p>
        </div>
        <button
          type="button"
          disabled={isRunning}
          onClick={runRegression}
          className="rounded-2xl bg-gradient-to-r from-violet-300 to-sky-300 px-5 py-3 text-sm font-bold text-slate-950 shadow-xl shadow-violet-950/25 transition hover:brightness-110 disabled:cursor-wait disabled:opacity-60"
        >
          {isRunning ? "Running 15 cases..." : "Run Regression Suite"}
        </button>
      </div>

      <div className="space-y-6 p-6">
        {error ? <div className="rounded-2xl border border-rose-300/20 bg-rose-300/10 p-4 text-sm text-rose-100">{error}</div> : null}

        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
          <Metric label="Average Score" value={latest ? percent(latest.avg_score) : isLoading ? "..." : "No runs"} />
          <Metric label="Planner Accuracy" value={latest ? percent(latest.planner_accuracy) : "n/a"} />
          <Metric label="Category Accuracy" value={latest ? percent(latest.category_accuracy) : "n/a"} />
          <Metric label="Priority Accuracy" value={latest ? percent(latest.priority_accuracy) : "n/a"} />
          <Metric label="Critic Accuracy" value={latest ? percent(latest.critic_accuracy) : "n/a"} />
        </div>

        <div className="grid gap-6 xl:grid-cols-[0.75fr_1.25fr]">
          <div>
            <h3 className="text-sm font-semibold text-white">Historical Runs</h3>
            <div className="mt-3 space-y-3">
              {history.length ? history.map((run) => (
                <div key={run.id} className="rounded-2xl border border-white/10 bg-black/20 p-4">
                  <div className="flex items-center justify-between gap-3">
                    <div><p className="text-sm font-semibold text-white">Run #{run.id}</p><p className="mt-1 text-xs text-slate-500">{dateTime(run.created_at)}</p></div>
                    <span className="rounded-full border border-violet-300/20 bg-violet-300/10 px-2.5 py-1 text-xs font-semibold text-violet-100">{percent(run.avg_score)}</span>
                  </div>
                </div>
              )) : <div className="rounded-2xl border border-dashed border-white/10 p-4 text-sm text-slate-400">No regression runs yet.</div>}
            </div>
          </div>

          <div>
            <h3 className="text-sm font-semibold text-white">Benchmark Results</h3>
            <div className="mt-3 max-h-[34rem] space-y-3 overflow-y-auto pr-1">
              {results.length ? results.map((result) => (
                <div key={result.id} className={`rounded-2xl border p-4 ${result.passed ? "border-emerald-300/15 bg-emerald-300/[0.045]" : "border-amber-300/20 bg-amber-300/[0.055]"}`}>
                  <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                    <div>
                      <p className="font-mono text-xs font-semibold text-white">{result.benchmark_case_id}</p>
                      <p className="mt-2 text-xs text-slate-400">
                        {result.mismatches.length ? `Mismatches: ${result.mismatches.join(", ")}` : "All six expectations matched."}
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className={`rounded-full border px-2 py-1 text-[10px] font-semibold uppercase ${result.passed ? "border-emerald-300/25 bg-emerald-300/10 text-emerald-100" : "border-amber-300/25 bg-amber-300/10 text-amber-100"}`}>{result.passed ? "pass" : "fail"}</span>
                      <span className="text-sm font-semibold text-white">{percent(result.total_score)}</span>
                    </div>
                  </div>
                  {result.workflow_run_id ? <Link href={`/runs/${result.workflow_run_id}`} className="mt-3 inline-flex text-xs font-semibold text-sky-200 hover:text-sky-100">Open workflow run #{result.workflow_run_id}</Link> : null}
                </div>
              )) : <div className="rounded-2xl border border-dashed border-white/10 p-4 text-sm text-slate-400">Run the regression suite to capture results.</div>}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
