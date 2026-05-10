"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";

type BenchmarkCase = {
  id: string;
  category: string;
  input_text: string;
  expected?: Record<string, unknown>;
};

type BenchmarkResult = {
  case_id: string;
  passed: boolean;
  failures: string[];
  workflow_run_id: number | null;
};

type BenchmarkRun = {
  id: number;
  total_cases: number;
  passed_cases: number;
  failed_cases: number;
  pass_rate: number;
  average_quality_score: number;
  results: BenchmarkResult[];
};

type BenchmarkHistoryItem = {
  id: number;
  pass_rate: number;
  average_quality_score: number;
  created_at: string;
};

const API_BASE_URL = "http://localhost:8000";
const NAV_ITEMS = [
  ["Dashboard", "/"],
  ["Workflows", "/workflows/new"],
  ["Runs", "/runs"],
  ["Benchmarks", "/benchmarks"],
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

function signedPercent(value: number | null | undefined) {
  if (value === null || value === undefined) return "n/a";
  const rounded = Math.round(value * 100);
  return `${rounded > 0 ? "+" : ""}${rounded}%`;
}

function Badge({ children, tone = "default" }: { children: React.ReactNode; tone?: "success" | "danger" | "warning" | "default" }) {
  const toneClass = {
    success: "border-emerald-400/25 bg-emerald-400/10 text-emerald-200",
    danger: "border-rose-400/25 bg-rose-400/10 text-rose-200",
    warning: "border-amber-400/25 bg-amber-400/10 text-amber-200",
    default: "border-slate-500/30 bg-slate-500/10 text-slate-300",
  }[tone];

  return (
    <span className={`inline-flex items-center rounded-full border px-2.5 py-1 text-xs font-semibold capitalize ${toneClass}`}>
      {children}
    </span>
  );
}

function MetricCard({ label, value, tone = "default" }: { label: string; value: string; tone?: "success" | "danger" | "warning" | "default" }) {
  const glow = {
    success: "shadow-emerald-950/20",
    danger: "shadow-rose-950/25",
    warning: "shadow-amber-950/20",
    default: "shadow-black/15",
  }[tone];

  return (
    <div className={`rounded-3xl border border-white/10 bg-white/[0.045] p-5 shadow-xl ${glow}`}>
      <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">{label}</p>
      <p className="mt-3 text-2xl font-semibold tracking-tight text-white">{value}</p>
    </div>
  );
}

export default function BenchmarksPage() {
  const [cases, setCases] = useState<BenchmarkCase[]>([]);
  const [caseError, setCaseError] = useState<string | null>(null);
  const [isLoadingCases, setIsLoadingCases] = useState(true);
  const [isRunning, setIsRunning] = useState(false);
  const [runResult, setRunResult] = useState<BenchmarkRun | null>(null);
  const [runError, setRunError] = useState<string | null>(null);
  const [history, setHistory] = useState<BenchmarkHistoryItem[]>([]);
  const [historyError, setHistoryError] = useState<string | null>(null);
  const [isLoadingHistory, setIsLoadingHistory] = useState(true);

  const categories = useMemo(
    () => Array.from(new Set(cases.map((benchmarkCase) => benchmarkCase.category))).sort(),
    [cases],
  );

  const latestRun = history[0] ?? null;
  const previousRun = history[1] ?? null;
  const passRateImprovement = latestRun && previousRun ? latestRun.pass_rate - previousRun.pass_rate : null;
  const qualityTrend = latestRun && previousRun ? latestRun.average_quality_score - previousRun.average_quality_score : null;

  useEffect(() => {
    async function loadCases() {
      setIsLoadingCases(true);
      setCaseError(null);

      try {
        const response = await fetch(`${API_BASE_URL}/api/v1/benchmarks/cases`);

        if (!response.ok) {
          throw new Error(`Failed to load benchmark cases: ${response.status}`);
        }

        setCases((await response.json()) as BenchmarkCase[]);
      } catch (error) {
        setCaseError(error instanceof Error ? error.message : "Failed to load benchmark cases.");
      } finally {
        setIsLoadingCases(false);
      }
    }

    loadCases();
  }, []);

  async function loadHistory() {
    setIsLoadingHistory(true);
    setHistoryError(null);

    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/benchmarks/history`);

      if (!response.ok) {
        throw new Error(`Failed to load benchmark history: ${response.status}`);
      }

      setHistory((await response.json()) as BenchmarkHistoryItem[]);
    } catch (error) {
      setHistoryError(error instanceof Error ? error.message : "Failed to load benchmark history.");
    } finally {
      setIsLoadingHistory(false);
    }
  }

  useEffect(() => {
    loadHistory();
  }, []);

  async function runBenchmark() {
    setIsRunning(true);
    setRunError(null);

    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/benchmarks/run`, {
        method: "POST",
      });

      if (!response.ok) {
        const message = await response.text();
        throw new Error(message || `Benchmark run failed: ${response.status}`);
      }

      setRunResult((await response.json()) as BenchmarkRun);
      await loadHistory();
    } catch (error) {
      setRunError(error instanceof Error ? error.message : "Benchmark run failed.");
    } finally {
      setIsRunning(false);
    }
  }

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
              const active = item === "Benchmarks";

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
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Benchmark Suite</p>
            <p className="mt-2 text-sm font-medium text-white">Regression checks</p>
            <p className="mt-2 text-xs leading-5 text-slate-500">
              Validate triage behavior against curated customer feedback cases.
            </p>
          </div>
        </aside>

        <section className="flex w-full flex-col lg:pl-72">
          <div className="mx-auto flex w-full max-w-7xl flex-col gap-6 px-4 py-5 sm:px-6 lg:px-8 lg:py-8">
            <header className="overflow-hidden rounded-3xl border border-white/10 bg-slate-950/70 shadow-2xl shadow-black/30 backdrop-blur-xl">
              <div className="border-b border-white/10 bg-white/[0.035] px-6 py-4">
                <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-500">Benchmark Dashboard</p>
                    <h1 className="mt-1 text-2xl font-semibold tracking-tight text-white sm:text-3xl">
                      OpsPilot Evaluation Suite
                    </h1>
                  </div>

                  <button
                    type="button"
                    onClick={runBenchmark}
                    disabled={isRunning}
                    className="inline-flex items-center justify-center rounded-2xl bg-gradient-to-r from-sky-300 to-violet-400 px-5 py-3 text-sm font-bold text-slate-950 shadow-xl shadow-sky-950/30 transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {isRunning ? "Running Benchmark..." : "Run Benchmark"}
                  </button>
                </div>
              </div>

              <div className="grid gap-6 px-6 py-6 lg:grid-cols-[0.85fr_1.15fr]">
                <div>
                  <p className="text-sm leading-7 text-slate-300">
                    Track whether OpsPilot creates the right outputs, flags review risk, and maintains quality across
                    billing, auth, UI, performance, prompt injection, and vague feedback scenarios.
                  </p>
                </div>

                <div className="flex flex-wrap gap-2 rounded-3xl border border-white/10 bg-black/20 p-4">
                  {categories.length > 0 ? (
                    categories.map((category) => (
                      <Badge key={category}>{titleize(category)}</Badge>
                    ))
                  ) : (
                    <span className="text-sm text-slate-500">Categories loading...</span>
                  )}
                </div>
              </div>
            </header>

            <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
              <MetricCard label="Benchmark Cases" value={isLoadingCases ? "..." : String(cases.length)} />
              <MetricCard label="Categories Covered" value={String(categories.length)} />
              <MetricCard label="Last Pass Rate" value={runResult ? percent(runResult.pass_rate) : "Not run"} tone={runResult && runResult.failed_cases > 0 ? "warning" : "default"} />
              <MetricCard label="Failed Cases" value={runResult ? String(runResult.failed_cases) : "Not run"} tone={runResult?.failed_cases ? "danger" : "success"} />
            </section>

            <section className="rounded-3xl border border-white/10 bg-slate-950/55 shadow-2xl shadow-black/25 backdrop-blur-xl">
              <div className="border-b border-white/10 px-6 py-5">
                <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">Benchmark History</p>
                <h2 className="mt-1 text-lg font-semibold tracking-tight text-white">Run Trends</h2>
              </div>

              <div className="p-6">
                <div className="grid gap-4 md:grid-cols-3">
                  <MetricCard
                    label="Latest Pass Rate"
                    value={latestRun ? percent(latestRun.pass_rate) : isLoadingHistory ? "..." : "No runs"}
                    tone={latestRun && latestRun.pass_rate >= 0.8 ? "success" : latestRun ? "warning" : "default"}
                  />
                  <MetricCard
                    label="Improvement"
                    value={signedPercent(passRateImprovement)}
                    tone={passRateImprovement === null ? "default" : passRateImprovement >= 0 ? "success" : "danger"}
                  />
                  <MetricCard
                    label="Avg Quality Trend"
                    value={signedPercent(qualityTrend)}
                    tone={qualityTrend === null ? "default" : qualityTrend >= 0 ? "success" : "warning"}
                  />
                </div>

                {historyError ? (
                  <div className="mt-5 rounded-2xl border border-rose-400/25 bg-rose-400/10 p-4 text-sm text-rose-200">
                    {historyError}
                  </div>
                ) : null}

                <div className="mt-5 space-y-3">
                  {isLoadingHistory ? (
                    <div className="rounded-2xl border border-white/10 bg-black/20 p-5 text-sm text-slate-400">
                      Loading benchmark history...
                    </div>
                  ) : history.length > 0 ? (
                    history.map((historyItem) => (
                      <div
                        key={historyItem.id}
                        className="grid gap-4 rounded-3xl border border-white/10 bg-black/20 p-4 shadow-xl shadow-black/10 md:grid-cols-[0.5fr_0.5fr_0.6fr_1fr] md:items-center"
                      >
                        <div>
                          <p className="text-sm font-semibold text-white">Run #{historyItem.id}</p>
                          <p className="mt-1 text-xs text-slate-500">Benchmark run</p>
                        </div>
                        <Badge tone={historyItem.pass_rate >= 0.8 ? "success" : "warning"}>
                          {percent(historyItem.pass_rate)} pass
                        </Badge>
                        <p className="text-sm font-semibold text-slate-200">{percent(historyItem.average_quality_score)} quality</p>
                        <p className="text-sm text-slate-500">{dateTime(historyItem.created_at)}</p>
                      </div>
                    ))
                  ) : (
                    <div className="rounded-2xl border border-dashed border-white/12 bg-white/[0.025] p-6 text-sm leading-6 text-slate-400">
                      No benchmark runs have been recorded yet.
                    </div>
                  )}
                </div>
              </div>
            </section>

            <section className="rounded-3xl border border-white/10 bg-slate-950/55 shadow-2xl shadow-black/25 backdrop-blur-xl">
              <div className="border-b border-white/10 px-6 py-5">
                <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">Loaded Cases</p>
                <h2 className="mt-1 text-lg font-semibold tracking-tight text-white">Benchmark Coverage</h2>
              </div>

              <div className="p-6">
                {caseError ? (
                  <div className="rounded-2xl border border-rose-400/25 bg-rose-400/10 p-4 text-sm text-rose-200">
                    {caseError}
                  </div>
                ) : isLoadingCases ? (
                  <div className="rounded-2xl border border-white/10 bg-black/20 p-5 text-sm text-slate-400">
                    Loading benchmark cases...
                  </div>
                ) : (
                  <div className="space-y-3">
                    {cases.map((benchmarkCase) => (
                      <div
                        key={benchmarkCase.id}
                        className="grid gap-4 rounded-3xl border border-white/10 bg-black/20 p-4 shadow-xl shadow-black/10 lg:grid-cols-[0.7fr_0.4fr_1.4fr]"
                      >
                        <div>
                          <p className="text-sm font-semibold text-white">{benchmarkCase.id}</p>
                          <p className="mt-1 text-xs text-slate-500">Case ID</p>
                        </div>
                        <div>
                          <Badge>{titleize(benchmarkCase.category)}</Badge>
                        </div>
                        <p className="text-sm leading-6 text-slate-300">{benchmarkCase.input_text}</p>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </section>

            {runError ? (
              <div className="rounded-3xl border border-rose-400/25 bg-rose-400/10 p-5 text-sm leading-6 text-rose-200">
                {runError}
              </div>
            ) : null}

            {runResult ? (
              <>
                <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
                  <MetricCard label="Total Cases" value={String(runResult.total_cases)} />
                  <MetricCard label="Passed Cases" value={String(runResult.passed_cases)} tone="success" />
                  <MetricCard label="Failed Cases" value={String(runResult.failed_cases)} tone={runResult.failed_cases > 0 ? "danger" : "success"} />
                  <MetricCard label="Pass Rate" value={percent(runResult.pass_rate)} tone={runResult.pass_rate >= 0.8 ? "success" : "warning"} />
                  <MetricCard label="Avg Quality" value={percent(runResult.average_quality_score)} />
                </section>

                <section className="rounded-3xl border border-white/10 bg-slate-950/55 shadow-2xl shadow-black/25 backdrop-blur-xl">
                  <div className="border-b border-white/10 px-6 py-5">
                    <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">Execution Results</p>
                    <h2 className="mt-1 text-lg font-semibold tracking-tight text-white">Case Outcomes</h2>
                  </div>

                  <div className="space-y-3 p-6">
                    {runResult.results.map((result) => (
                      <div
                        key={result.case_id}
                        className={`rounded-3xl border p-4 shadow-xl shadow-black/10 ${
                          result.passed
                            ? "border-emerald-400/15 bg-emerald-400/[0.045]"
                            : "border-amber-400/25 bg-amber-400/10"
                        }`}
                      >
                        <div className="grid gap-4 lg:grid-cols-[0.8fr_0.35fr_1.5fr_0.45fr] lg:items-start">
                          <div>
                            <p className="text-sm font-semibold text-white">{result.case_id}</p>
                            <p className="mt-1 text-xs text-slate-500">Case ID</p>
                          </div>
                          <Badge tone={result.passed ? "success" : "warning"}>
                            {result.passed ? "passed" : "failed"}
                          </Badge>
                          <div>
                            {result.failures.length > 0 ? (
                              <div className="space-y-2">
                                {result.failures.map((failure) => (
                                  <div
                                    key={failure}
                                    className="rounded-2xl border border-rose-400/20 bg-rose-400/10 p-3 text-xs leading-5 text-rose-100"
                                  >
                                    {failure}
                                  </div>
                                ))}
                              </div>
                            ) : (
                              <p className="text-sm text-slate-400">No failures recorded.</p>
                            )}
                          </div>
                          <div>
                            {result.workflow_run_id ? (
                              <Link
                                href={`/runs/${result.workflow_run_id}`}
                                className="inline-flex rounded-2xl border border-sky-300/20 bg-sky-300/10 px-3 py-2 text-sm font-semibold text-sky-100 transition hover:bg-sky-300/15"
                              >
                                Run #{result.workflow_run_id}
                              </Link>
                            ) : (
                              <span className="text-sm text-slate-500">No run</span>
                            )}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </section>
              </>
            ) : null}
          </div>
        </section>
      </div>
    </main>
  );
}
