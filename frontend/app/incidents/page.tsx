"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

type Incident = {
  id: number;
  category: string;
  title: string;
  description: string;
  severity: "medium" | "high" | "critical" | string;
  workflow_count: number;
  related_workflow_ids: number[];
  root_cause_clusters: Array<{
    theme: string;
    workflow_count: number;
    summary: string;
  }>;
  operational_risks: string[];
  recommended_actions: string[];
  first_detected_at: string;
  last_detected_at: string;
  status: string;
};

type IncidentResponsePlan = {
  id: number;
  incident_id: number;
  plan_type: string;
  next_tools: string[];
  reasoning: string;
  created_at: string;
};

type IncidentExecutionTrace = {
  id: number;
  incident_id: number;
  response_plan_id: number;
  tool_name: string;
  status: "executed" | "skipped" | "error" | string;
  result_summary: string | null;
  error_message: string | null;
  created_at: string;
};

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
function titleize(value: string) {
  return value.replaceAll("_", " ");
}

function dateTime(value: string) {
  return new Intl.DateTimeFormat("en", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function severityTone(severity: string) {
  if (severity === "critical") return "border-rose-300/30 bg-rose-300/15 text-rose-100";
  if (severity === "high") return "border-orange-300/30 bg-orange-300/15 text-orange-100";
  return "border-amber-300/30 bg-amber-300/15 text-amber-100";
}

function executionTone(status: string) {
  if (status === "executed") return "border-emerald-300/30 bg-emerald-300/10 text-emerald-100";
  if (status === "error") return "border-rose-300/30 bg-rose-300/10 text-rose-100";
  return "border-amber-300/30 bg-amber-300/10 text-amber-100";
}

function Badge({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return <span className={`inline-flex rounded-full border px-2.5 py-1 text-xs font-semibold capitalize ${className}`}>{children}</span>;
}

function MetricCard({ label, value, tone = "default" }: { label: string; value: string; tone?: "critical" | "high" | "medium" | "default" }) {
  const toneClass = {
    critical: "border-rose-300/20 bg-rose-300/[0.07] shadow-rose-950/25",
    high: "border-orange-300/20 bg-orange-300/[0.07] shadow-orange-950/20",
    medium: "border-amber-300/20 bg-amber-300/[0.07] shadow-amber-950/20",
    default: "border-white/10 bg-white/[0.045] shadow-black/15",
  }[tone];

  return (
    <div className={`rounded-3xl border p-5 shadow-xl ${toneClass}`}>
      <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">{label}</p>
      <p className="mt-3 text-2xl font-semibold tracking-tight text-white">{value}</p>
    </div>
  );
}

export default function IncidentsPage() {
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [responsePlans, setResponsePlans] = useState<Record<number, IncidentResponsePlan>>({});
  const [executionTraces, setExecutionTraces] = useState<Record<number, IncidentExecutionTrace[]>>({});
  const [executingIncidentId, setExecutingIncidentId] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadIncidents() {
      setIsLoading(true);
      setError(null);

      try {
        const response = await fetch(`${API_BASE_URL}/api/v1/incidents`, { cache: "no-store" });
        if (!response.ok) {
          throw new Error(`Failed to load incidents: ${response.status}`);
        }
        const loadedIncidents = (await response.json()) as Incident[];
        setIncidents(loadedIncidents);

        const planEntries = await Promise.all(
          loadedIncidents.map(async (incident) => {
            const planResponse = await fetch(
              `${API_BASE_URL}/api/v1/incidents/${incident.id}/response-plan`,
              { cache: "no-store" },
            );
            if (!planResponse.ok) return null;
            return [incident.id, (await planResponse.json()) as IncidentResponsePlan] as const;
          }),
        );
        setResponsePlans(
          Object.fromEntries(
            planEntries.filter(
              (entry): entry is readonly [number, IncidentResponsePlan] => entry !== null,
            ),
          ),
        );

        const executionEntries = await Promise.all(
          loadedIncidents.map(async (incident) => {
            const executionResponse = await fetch(
              `${API_BASE_URL}/api/v1/incidents/${incident.id}/executions`,
              { cache: "no-store" },
            );
            if (!executionResponse.ok) return [incident.id, []] as const;
            return [incident.id, (await executionResponse.json()) as IncidentExecutionTrace[]] as const;
          }),
        );
        setExecutionTraces(Object.fromEntries(executionEntries));
      } catch (requestError) {
        setError(requestError instanceof Error ? requestError.message : "Unable to load incidents.");
      } finally {
        setIsLoading(false);
      }
    }

    loadIncidents();
  }, []);

  const criticalCount = incidents.filter((incident) => incident.severity === "critical").length;
  const highCount = incidents.filter((incident) => incident.severity === "high").length;
  const totalAffected = incidents.reduce((total, incident) => total + incident.workflow_count, 0);

  async function executeResponsePlan(incidentId: number) {
    setExecutingIncidentId(incidentId);
    setError(null);
    try {
      const executeResponse = await fetch(
        `${API_BASE_URL}/api/v1/incidents/${incidentId}/execute`,
        { method: "POST" },
      );
      if (!executeResponse.ok) {
        throw new Error(`Failed to execute response plan: ${executeResponse.status}`);
      }

      const tracesResponse = await fetch(
        `${API_BASE_URL}/api/v1/incidents/${incidentId}/executions`,
        { cache: "no-store" },
      );
      if (!tracesResponse.ok) {
        throw new Error(`Failed to refresh execution traces: ${tracesResponse.status}`);
      }
      const traces = (await tracesResponse.json()) as IncidentExecutionTrace[];
      setExecutionTraces((current) => ({ ...current, [incidentId]: traces }));
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to execute response plan.");
    } finally {
      setExecutingIncidentId(null);
    }
  }

  return (
    <main className="min-h-screen bg-[#05070b] text-slate-100">
      <div className="fixed inset-0 bg-[linear-gradient(180deg,rgba(15,23,42,0.72),rgba(2,6,23,0.96)),radial-gradient(circle_at_20%_0%,rgba(14,165,233,0.18),transparent_34%),radial-gradient(circle_at_90%_4%,rgba(168,85,247,0.16),transparent_30%)]" />
      <div className="relative flex min-h-screen">
        <section className="flex w-full flex-col">
          <div className="mx-auto flex w-full max-w-7xl flex-col gap-6 px-4 py-5 sm:px-6 lg:px-8 lg:py-8">
            <header className="rounded-3xl border border-white/10 bg-slate-950/70 p-6 shadow-2xl shadow-black/30 backdrop-blur-xl">
              <p className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-500">Incident Detection</p>
              <h1 className="mt-2 text-3xl font-semibold tracking-tight text-white">Operational Issue Spikes</h1>
              <p className="mt-3 max-w-3xl text-sm leading-7 text-slate-300">
                Heuristic v1 incident detection flags categories with three or more related workflow runs in the last 30 minutes.
              </p>
            </header>

            {error ? <div className="rounded-3xl border border-rose-400/25 bg-rose-400/10 p-5 text-sm text-rose-200">{error}</div> : null}

            <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
              <MetricCard label="Active Incidents" value={isLoading ? "..." : String(incidents.length)} />
              <MetricCard label="Critical" value={isLoading ? "..." : String(criticalCount)} tone={criticalCount ? "critical" : "default"} />
              <MetricCard label="High Severity" value={isLoading ? "..." : String(highCount)} tone={highCount ? "high" : "default"} />
              <MetricCard label="Affected Workflows" value={isLoading ? "..." : String(totalAffected)} tone={totalAffected ? "medium" : "default"} />
            </section>

            <section className="rounded-3xl border border-white/10 bg-slate-950/55 shadow-2xl shadow-black/25 backdrop-blur-xl">
              <div className="border-b border-white/10 px-6 py-5">
                <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">Active Incidents</p>
                <h2 className="mt-1 text-lg font-semibold tracking-tight text-white">Detected Spikes</h2>
              </div>
              <div className="space-y-4 p-6">
                {isLoading ? (
                  <div className="rounded-2xl border border-white/10 bg-black/20 p-5 text-sm text-slate-400">Loading incidents...</div>
                ) : incidents.length ? (
                  incidents.map((incident) => (
                    <div key={incident.id} className="rounded-3xl border border-white/10 bg-[#090d16] p-5 shadow-xl shadow-black/15">
                      <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
                        <div>
                          <div className="flex flex-wrap gap-2">
                            <Badge className={severityTone(incident.severity)}>{incident.severity}</Badge>
                            <Badge className="border-slate-500/30 bg-slate-500/10 text-slate-300">{titleize(incident.category)}</Badge>
                          </div>
                          <h3 className="mt-3 text-xl font-semibold tracking-tight text-white">{incident.title}</h3>
                          <p className="mt-2 max-w-3xl text-sm leading-7 text-slate-300">{incident.description}</p>
                        </div>
                        <div className="rounded-2xl border border-white/10 bg-white/[0.035] p-4 text-right">
                          <p className="text-2xl font-semibold text-white">{incident.workflow_count}</p>
                          <p className="text-xs text-slate-500">related workflows</p>
                        </div>
                      </div>

                      <div className="mt-5 flex flex-wrap gap-2">
                        {incident.related_workflow_ids.slice(0, 6).map((workflowId) => (
                          <Link key={workflowId} href={`/runs/${workflowId}`} className="rounded-full border border-sky-300/20 bg-sky-300/10 px-3 py-1 text-xs font-semibold text-sky-100 hover:bg-sky-300/15">
                            Run #{workflowId}
                          </Link>
                        ))}
                      </div>

                      <div className="mt-5 rounded-3xl border border-sky-300/15 bg-sky-300/[0.045] p-5">
                        <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-sky-200/70">
                          Founder Intelligence
                        </p>

                        <div className="mt-4 grid gap-4 lg:grid-cols-[1fr_0.8fr]">
                          <div>
                            <h4 className="text-sm font-semibold text-white">Root Cause Clusters</h4>
                            <div className="mt-3 grid gap-3 md:grid-cols-2">
                              {incident.root_cause_clusters.length ? (
                                incident.root_cause_clusters.map((cluster) => (
                                  <div key={cluster.theme} className="rounded-2xl border border-white/10 bg-black/20 p-4">
                                    <div className="flex items-start justify-between gap-3">
                                      <p className="text-sm font-semibold text-white">{titleize(cluster.theme)}</p>
                                      <Badge className="border-sky-300/20 bg-sky-300/10 text-sky-100">
                                        {cluster.workflow_count}
                                      </Badge>
                                    </div>
                                    <p className="mt-2 text-xs leading-5 text-slate-400">{cluster.summary}</p>
                                  </div>
                                ))
                              ) : (
                                <div className="rounded-2xl border border-white/10 bg-black/20 p-4 text-sm text-slate-400">
                                  No clusters generated yet.
                                </div>
                              )}
                            </div>
                          </div>

                          <div>
                            <h4 className="text-sm font-semibold text-white">Operational Risks</h4>
                            <div className="mt-3 flex flex-wrap gap-2">
                              {incident.operational_risks.length ? (
                                incident.operational_risks.map((risk) => (
                                  <Badge key={risk} className="border-amber-300/25 bg-amber-300/10 text-amber-100">
                                    {risk}
                                  </Badge>
                                ))
                              ) : (
                                <span className="text-sm text-slate-400">No risk tags generated.</span>
                              )}
                            </div>

                            <h4 className="mt-5 text-sm font-semibold text-white">Recommended Actions</h4>
                            {incident.recommended_actions.length ? (
                              <ol className="mt-3 space-y-2">
                                {incident.recommended_actions.map((action, index) => (
                                  <li key={action} className="flex gap-3 rounded-2xl border border-white/10 bg-black/20 p-3 text-sm leading-6 text-slate-300">
                                    <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-white/10 text-xs font-semibold text-slate-200">
                                      {index + 1}
                                    </span>
                                    <span>{action}</span>
                                  </li>
                                ))}
                              </ol>
                            ) : (
                              <p className="mt-3 text-sm text-slate-400">No recommended actions generated.</p>
                            )}
                          </div>
                        </div>
                      </div>

                      <div className="mt-5 overflow-hidden rounded-3xl border border-violet-300/20 bg-violet-300/[0.055] shadow-xl shadow-violet-950/15">
                        <div className="flex flex-col gap-3 border-b border-violet-300/15 px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
                          <div>
                            <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-violet-200/65">
                              Read-only planning v1
                            </p>
                            <h4 className="mt-1 text-base font-semibold text-white">Incident Response Plan</h4>
                          </div>
                          {responsePlans[incident.id] ? (
                            <Badge className="border-violet-300/25 bg-violet-300/10 text-violet-100">
                              {titleize(responsePlans[incident.id].plan_type)}
                            </Badge>
                          ) : null}
                        </div>

                        {responsePlans[incident.id] ? (
                          <div className="grid gap-5 p-5 lg:grid-cols-[1.25fr_0.75fr]">
                            <div>
                              <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-500">
                                Reasoning
                              </p>
                              <p className="mt-3 text-sm leading-7 text-slate-300">
                                {responsePlans[incident.id].reasoning}
                              </p>
                              <p className="hidden">
                                Planned {dateTime(responsePlans[incident.id].created_at)} · No actions executed
                              </p>
                              <p className="mt-3 text-xs text-slate-500">
                                Planned {dateTime(responsePlans[incident.id].created_at)} &middot; No actions executed
                              </p>
                            </div>

                            <div>
                              <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-500">
                                Selected Tools
                              </p>
                              <div className="mt-3 flex flex-wrap gap-2">
                                {responsePlans[incident.id].next_tools.map((tool) => (
                                  <span
                                    key={tool}
                                    className="rounded-xl border border-white/10 bg-black/25 px-3 py-2 font-mono text-xs text-violet-100"
                                  >
                                    {tool}
                                  </span>
                                ))}
                              </div>
                            </div>
                          </div>
                        ) : (
                          <div className="p-5 text-sm text-slate-400">Preparing response plan...</div>
                        )}
                      </div>

                      <div className="mt-5 overflow-hidden rounded-3xl border border-emerald-300/15 bg-emerald-300/[0.04] shadow-xl shadow-emerald-950/10">
                        <div className="flex flex-col gap-3 border-b border-emerald-300/10 px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
                          <div>
                            <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-emerald-200/60">
                              Explicit read-only execution
                            </p>
                            <h4 className="mt-1 text-base font-semibold text-white">Incident Response Execution</h4>
                            <p className="mt-1 text-xs text-slate-500">
                              Only memory search and founder summary are allowed. Email alerts remain blocked.
                            </p>
                          </div>
                          <button
                            type="button"
                            disabled={
                              executingIncidentId === incident.id
                              || !responsePlans[incident.id]
                              || (executionTraces[incident.id] ?? []).length > 0
                            }
                            onClick={() => executeResponsePlan(incident.id)}
                            className="rounded-xl border border-emerald-300/25 bg-emerald-300/10 px-4 py-2 text-xs font-semibold text-emerald-100 transition hover:bg-emerald-300/15 disabled:cursor-not-allowed disabled:opacity-50"
                          >
                            {executingIncidentId === incident.id
                              ? "Executing..."
                              : (executionTraces[incident.id] ?? []).length > 0
                                ? "Plan executed"
                                : "Execute response plan"}
                          </button>
                        </div>

                        <div className="space-y-3 p-5">
                          {(executionTraces[incident.id] ?? []).length ? (
                            executionTraces[incident.id]
                              .slice(-Math.max(responsePlans[incident.id]?.next_tools.length ?? 1, 1))
                              .map((trace) => (
                              <div key={trace.id} className="rounded-2xl border border-white/10 bg-black/20 p-4">
                                <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                                  <div>
                                    <p className="font-mono text-sm font-semibold text-white">{trace.tool_name}</p>
                                    <p className="mt-2 text-sm leading-6 text-slate-300">
                                      {trace.result_summary || trace.error_message || "No execution summary recorded."}
                                    </p>
                                  </div>
                                  <div className="flex flex-wrap items-center gap-2">
                                    <Badge className={executionTone(trace.status)}>{trace.status}</Badge>
                                    <span className="text-xs text-slate-500">{dateTime(trace.created_at)}</span>
                                  </div>
                                </div>
                              </div>
                              ))
                          ) : (
                            <div className="rounded-2xl border border-dashed border-white/10 bg-black/15 p-4 text-sm text-slate-400">
                              No execution traces yet. Execution starts only when you click the button.
                            </div>
                          )}
                          {(executionTraces[incident.id] ?? []).length > (responsePlans[incident.id]?.next_tools.length ?? 0) ? (
                            <p className="text-xs text-slate-500">
                              Earlier duplicate traces are hidden. This response plan is now protected from repeat execution.
                            </p>
                          ) : null}
                        </div>
                      </div>

                      <div className="mt-5 grid gap-3 text-xs text-slate-500 md:grid-cols-2">
                        <p>First detected: {dateTime(incident.first_detected_at)}</p>
                        <p>Last detected: {dateTime(incident.last_detected_at)}</p>
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="rounded-2xl border border-dashed border-white/12 bg-white/[0.025] p-6 text-sm text-slate-400">
                    No active incidents detected.
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
