"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";

type IncidentStatus = "open" | "investigating" | "mitigated" | "resolved" | string;

type IncidentAlert = {
  id: number;
  alert_type: string;
  severity: string;
  recipient: string;
  subject: string;
  sent_at: string;
};

type TimelineEvent = {
  event_type: string;
  label: string;
  timestamp: string;
};

type Incident = {
  id: number;
  category: string;
  title: string;
  description: string;
  severity: "medium" | "high" | "critical" | string;
  workflow_count: number;
  related_workflow_ids: number[];
  workflow_links?: Array<{ workflow_run_id: number; href: string }>;
  root_cause_clusters: Array<{
    theme: string;
    workflow_count: number;
    summary: string;
  }>;
  operational_risks: string[];
  recommended_actions: string[];
  playbook_steps: string[];
  alert_history?: IncidentAlert[];
  operational_timeline?: TimelineEvent[];
  owner: string | null;
  resolution_notes: string | null;
  first_detected_at: string;
  last_detected_at: string;
  status: IncidentStatus;
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

const STATUS_ACTIONS = [
  { label: "Mark investigating", status: "investigating" },
  { label: "Mark mitigated", status: "mitigated" },
  { label: "Mark resolved", status: "resolved" },
] as const;

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

function statusTone(status: string) {
  if (status === "resolved") return "border-emerald-300/30 bg-emerald-300/15 text-emerald-100";
  if (status === "mitigated") return "border-cyan-300/30 bg-cyan-300/15 text-cyan-100";
  if (status === "investigating") return "border-violet-300/30 bg-violet-300/15 text-violet-100";
  return "border-slate-500/30 bg-slate-500/10 text-slate-300";
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
  const [selectedIncident, setSelectedIncident] = useState<Incident | null>(null);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isDetailLoading, setIsDetailLoading] = useState(false);
  const [isUpdatingStatus, setIsUpdatingStatus] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function loadIncidentDetail(incidentId: number) {
    setSelectedId(incidentId);
    setIsDetailLoading(true);
    setError(null);

    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/incidents/${incidentId}`, { cache: "no-store" });
      if (!response.ok) {
        throw new Error(`Failed to load incident detail: ${response.status}`);
      }
      setSelectedIncident((await response.json()) as Incident);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to load incident detail.");
    } finally {
      setIsDetailLoading(false);
    }
  }

  async function loadIncidents() {
    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/incidents`, { cache: "no-store" });
      if (!response.ok) {
        throw new Error(`Failed to load incidents: ${response.status}`);
      }
      const payload = (await response.json()) as Incident[];
      setIncidents(payload);
      if (payload.length && selectedId === null) {
        await loadIncidentDetail(payload[0].id);
      }
      if (!payload.length) {
        setSelectedIncident(null);
        setSelectedId(null);
      }
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to load incidents.");
    } finally {
      setIsLoading(false);
    }
  }

  async function updateStatus(status: string) {
    if (!selectedIncident) return;

    setIsUpdatingStatus(true);
    setError(null);

    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/incidents/${selectedIncident.id}/status`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status }),
      });

      if (!response.ok) {
        throw new Error(`Failed to update status: ${response.status}`);
      }

      const updatedIncident = (await response.json()) as Incident;
      setSelectedIncident(updatedIncident);
      setIncidents((current) => {
        if (updatedIncident.status === "resolved") {
          return current.filter((incident) => incident.id !== updatedIncident.id);
        }
        return current.map((incident) => (incident.id === updatedIncident.id ? { ...incident, ...updatedIncident } : incident));
      });
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to update incident status.");
    } finally {
      setIsUpdatingStatus(false);
    }
  }

  useEffect(() => {
    loadIncidents();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const criticalCount = incidents.filter((incident) => incident.severity === "critical").length;
  const highCount = incidents.filter((incident) => incident.severity === "high").length;
  const totalAffected = incidents.reduce((total, incident) => total + incident.workflow_count, 0);
  const alertCount = selectedIncident?.alert_history?.length ?? 0;

  const orderedTimeline = useMemo(() => {
    return [...(selectedIncident?.operational_timeline ?? [])].sort(
      (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime(),
    );
  }, [selectedIncident]);

  return (
    <main className="min-h-screen bg-[#05070b] text-slate-100">
      <div className="fixed inset-0 bg-[linear-gradient(180deg,rgba(15,23,42,0.72),rgba(2,6,23,0.96)),radial-gradient(circle_at_20%_0%,rgba(14,165,233,0.18),transparent_34%),radial-gradient(circle_at_90%_4%,rgba(168,85,247,0.16),transparent_30%)]" />
      <div className="relative flex min-h-screen">
        <aside className="hidden w-72 shrink-0 border-r border-white/10 bg-black/20 px-4 py-5 backdrop-blur-2xl lg:fixed lg:inset-y-0 lg:flex lg:flex-col">
          <div className="flex items-center gap-3 rounded-2xl border border-white/10 bg-white/[0.045] p-3 shadow-lg shadow-black/20">
            <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-gradient-to-br from-sky-300 to-violet-400 text-sm font-black text-slate-950">OP</div>
            <div>
              <p className="text-sm font-semibold text-white">OpsPilot</p>
              <p className="text-xs text-slate-500">Agent operations</p>
            </div>
          </div>
          <nav className="mt-8 space-y-1">
            {NAV_ITEMS.map(([item, href]) => {
              const active = item === "Incidents";
              return (
                <Link key={item} className={`flex items-center justify-between rounded-2xl px-3 py-2.5 text-sm font-medium transition ${active ? "border border-sky-300/20 bg-sky-300/10 text-sky-100 shadow-lg shadow-sky-950/20" : "text-slate-400 hover:bg-white/[0.045] hover:text-white"}`} href={href}>
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
              <p className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-500">Incident Response</p>
              <h1 className="mt-2 text-3xl font-semibold tracking-tight text-white">Operational Incidents</h1>
              <p className="mt-3 max-w-3xl text-sm leading-7 text-slate-300">
                Track incident severity, alert history, lifecycle status, playbooks, and affected workflow runs from one command surface.
              </p>
            </header>

            {error ? <div className="rounded-3xl border border-rose-400/25 bg-rose-400/10 p-5 text-sm text-rose-200">{error}</div> : null}

            <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
              <MetricCard label="Open Incidents" value={isLoading ? "..." : String(incidents.length)} />
              <MetricCard label="Critical" value={isLoading ? "..." : String(criticalCount)} tone={criticalCount ? "critical" : "default"} />
              <MetricCard label="High Severity" value={isLoading ? "..." : String(highCount)} tone={highCount ? "high" : "default"} />
              <MetricCard label="Affected Workflows" value={isLoading ? "..." : String(totalAffected)} tone={totalAffected ? "medium" : "default"} />
            </section>

            <section className="grid gap-5 xl:grid-cols-[0.85fr_1.15fr]">
              <div className="rounded-3xl border border-white/10 bg-slate-950/55 shadow-2xl shadow-black/25 backdrop-blur-xl">
                <div className="border-b border-white/10 px-6 py-5">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">Detected Spikes</p>
                  <h2 className="mt-1 text-lg font-semibold tracking-tight text-white">Incident Queue</h2>
                </div>
                <div className="space-y-3 p-4">
                  {isLoading ? (
                    <div className="rounded-2xl border border-white/10 bg-black/20 p-5 text-sm text-slate-400">Loading incidents...</div>
                  ) : incidents.length ? (
                    incidents.map((incident) => {
                      const active = incident.id === selectedId;
                      return (
                        <button
                          key={incident.id}
                          className={`w-full rounded-3xl border p-5 text-left shadow-xl shadow-black/15 transition ${active ? "border-sky-300/30 bg-sky-300/[0.08]" : "border-white/10 bg-[#090d16] hover:border-white/20 hover:bg-white/[0.045]"}`}
                          onClick={() => loadIncidentDetail(incident.id)}
                          type="button"
                        >
                          <div className="flex flex-wrap gap-2">
                            <Badge className={severityTone(incident.severity)}>{incident.severity}</Badge>
                            <Badge className={statusTone(incident.status)}>{titleize(incident.status)}</Badge>
                            <Badge className="border-slate-500/30 bg-slate-500/10 text-slate-300">{titleize(incident.category)}</Badge>
                          </div>
                          <h3 className="mt-3 text-lg font-semibold tracking-tight text-white">{incident.title}</h3>
                          <p className="mt-2 line-clamp-2 text-sm leading-6 text-slate-400">{incident.description}</p>
                          <div className="mt-4 flex items-center justify-between text-xs text-slate-500">
                            <span>{incident.workflow_count} workflows</span>
                            <span>{dateTime(incident.last_detected_at)}</span>
                          </div>
                        </button>
                      );
                    })
                  ) : (
                    <div className="rounded-2xl border border-dashed border-white/12 bg-white/[0.025] p-6 text-sm text-slate-400">
                      No open incidents detected.
                    </div>
                  )}
                </div>
              </div>

              <div className="rounded-3xl border border-white/10 bg-slate-950/55 shadow-2xl shadow-black/25 backdrop-blur-xl">
                <div className="border-b border-white/10 px-6 py-5">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">Incident Detail</p>
                  <h2 className="mt-1 text-lg font-semibold tracking-tight text-white">
                    {selectedIncident ? selectedIncident.title : "Select an incident"}
                  </h2>
                </div>

                {isDetailLoading ? (
                  <div className="p-6 text-sm text-slate-400">Loading incident detail...</div>
                ) : selectedIncident ? (
                  <div className="space-y-5 p-6">
                    <div className="flex flex-col gap-4 rounded-3xl border border-white/10 bg-[#090d16] p-5 md:flex-row md:items-start md:justify-between">
                      <div>
                        <div className="flex flex-wrap gap-2">
                          <Badge className={severityTone(selectedIncident.severity)}>{selectedIncident.severity}</Badge>
                          <Badge className={statusTone(selectedIncident.status)}>{titleize(selectedIncident.status)}</Badge>
                          <Badge className="border-slate-500/30 bg-slate-500/10 text-slate-300">{titleize(selectedIncident.category)}</Badge>
                        </div>
                        <p className="mt-3 max-w-3xl text-sm leading-7 text-slate-300">{selectedIncident.description}</p>
                        <p className="mt-3 text-xs text-slate-500">
                          Owner: {selectedIncident.owner || "Unassigned"} | Alerts sent: {alertCount}
                        </p>
                      </div>
                      <div className="grid grid-cols-2 gap-3 text-right">
                        <div className="rounded-2xl border border-white/10 bg-white/[0.035] p-4">
                          <p className="text-2xl font-semibold text-white">{selectedIncident.workflow_count}</p>
                          <p className="text-xs text-slate-500">workflows</p>
                        </div>
                        <div className="rounded-2xl border border-white/10 bg-white/[0.035] p-4">
                          <p className="text-2xl font-semibold text-white">{selectedIncident.playbook_steps.length}</p>
                          <p className="text-xs text-slate-500">playbook steps</p>
                        </div>
                      </div>
                    </div>

                    <div className="flex flex-wrap gap-2">
                      {STATUS_ACTIONS.map((action) => (
                        <button
                          key={action.status}
                          className="rounded-full border border-sky-300/20 bg-sky-300/10 px-4 py-2 text-xs font-semibold text-sky-100 transition hover:bg-sky-300/15 disabled:cursor-not-allowed disabled:opacity-50"
                          disabled={isUpdatingStatus || selectedIncident.status === action.status}
                          onClick={() => updateStatus(action.status)}
                          type="button"
                        >
                          {isUpdatingStatus ? "Updating..." : action.label}
                        </button>
                      ))}
                    </div>

                    <div className="grid gap-5 lg:grid-cols-2">
                      <div className="rounded-3xl border border-sky-300/15 bg-sky-300/[0.045] p-5">
                        <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-sky-200/70">Playbook Checklist</p>
                        {selectedIncident.playbook_steps.length ? (
                          <ol className="mt-4 space-y-3">
                            {selectedIncident.playbook_steps.map((step, index) => (
                              <li key={step} className="flex gap-3 rounded-2xl border border-white/10 bg-black/20 p-3 text-sm leading-6 text-slate-300">
                                <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-white/10 text-xs font-semibold text-slate-200">
                                  {index + 1}
                                </span>
                                <span>{step}</span>
                              </li>
                            ))}
                          </ol>
                        ) : (
                          <p className="mt-4 text-sm text-slate-400">No playbook generated yet.</p>
                        )}
                      </div>

                      <div className="rounded-3xl border border-white/10 bg-[#090d16] p-5">
                        <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">Alert History</p>
                        {selectedIncident.alert_history?.length ? (
                          <div className="mt-4 space-y-3">
                            {selectedIncident.alert_history.map((alert) => (
                              <div key={alert.id} className="rounded-2xl border border-white/10 bg-black/20 p-4">
                                <div className="flex flex-wrap items-center justify-between gap-2">
                                  <Badge className={severityTone(alert.severity)}>{alert.severity}</Badge>
                                  <span className="text-xs text-slate-500">{dateTime(alert.sent_at)}</span>
                                </div>
                                <p className="mt-3 text-sm font-semibold text-white">{alert.subject}</p>
                                <p className="mt-1 text-xs text-slate-500">To {alert.recipient} | {titleize(alert.alert_type)}</p>
                              </div>
                            ))}
                          </div>
                        ) : (
                          <p className="mt-4 text-sm text-slate-400">No alert emails have been recorded for this incident.</p>
                        )}
                      </div>
                    </div>

                    <div className="rounded-3xl border border-white/10 bg-[#090d16] p-5">
                      <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">Founder Intelligence</p>
                      <div className="mt-4 grid gap-4 lg:grid-cols-[1fr_0.8fr]">
                        <div>
                          <h4 className="text-sm font-semibold text-white">Root Cause Clusters</h4>
                          <div className="mt-3 grid gap-3 md:grid-cols-2">
                            {selectedIncident.root_cause_clusters.length ? (
                              selectedIncident.root_cause_clusters.map((cluster) => (
                                <div key={cluster.theme} className="rounded-2xl border border-white/10 bg-black/20 p-4">
                                  <div className="flex items-start justify-between gap-3">
                                    <p className="text-sm font-semibold text-white">{titleize(cluster.theme)}</p>
                                    <Badge className="border-sky-300/20 bg-sky-300/10 text-sky-100">{cluster.workflow_count}</Badge>
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
                            {selectedIncident.operational_risks.length ? (
                              selectedIncident.operational_risks.map((risk) => (
                                <Badge key={risk} className="border-amber-300/25 bg-amber-300/10 text-amber-100">{risk}</Badge>
                              ))
                            ) : (
                              <span className="text-sm text-slate-400">No risk tags generated.</span>
                            )}
                          </div>

                          <h4 className="mt-5 text-sm font-semibold text-white">Recommended Actions</h4>
                          {selectedIncident.recommended_actions.length ? (
                            <ol className="mt-3 space-y-2">
                              {selectedIncident.recommended_actions.map((action, index) => (
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

                    <div className="grid gap-5 lg:grid-cols-2">
                      <div className="rounded-3xl border border-white/10 bg-[#090d16] p-5">
                        <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">Affected Workflows</p>
                        <div className="mt-4 flex flex-wrap gap-2">
                          {(selectedIncident.workflow_links ?? []).length ? (
                            selectedIncident.workflow_links?.map((workflow) => (
                              <Link key={workflow.workflow_run_id} href={workflow.href} className="rounded-full border border-sky-300/20 bg-sky-300/10 px-3 py-1 text-xs font-semibold text-sky-100 hover:bg-sky-300/15">
                                Run #{workflow.workflow_run_id}
                              </Link>
                            ))
                          ) : (
                            <span className="text-sm text-slate-400">No workflow links available.</span>
                          )}
                        </div>
                      </div>

                      <div className="rounded-3xl border border-white/10 bg-[#090d16] p-5">
                        <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">Operational Timeline</p>
                        {orderedTimeline.length ? (
                          <div className="mt-4 space-y-3">
                            {orderedTimeline.map((event, index) => (
                              <div key={`${event.event_type}-${event.timestamp}-${index}`} className="flex gap-3">
                                <div className="mt-1 h-2.5 w-2.5 shrink-0 rounded-full bg-sky-300 shadow-lg shadow-sky-500/30" />
                                <div>
                                  <p className="text-sm font-semibold text-white">{event.label}</p>
                                  <p className="mt-1 text-xs text-slate-500">{dateTime(event.timestamp)}</p>
                                </div>
                              </div>
                            ))}
                          </div>
                        ) : (
                          <p className="mt-4 text-sm text-slate-400">No timeline events available.</p>
                        )}
                      </div>
                    </div>

                    {selectedIncident.resolution_notes ? (
                      <div className="rounded-3xl border border-emerald-300/20 bg-emerald-300/[0.06] p-5 text-sm leading-7 text-emerald-100">
                        {selectedIncident.resolution_notes}
                      </div>
                    ) : null}
                  </div>
                ) : (
                  <div className="p-6 text-sm text-slate-400">Select an incident to view response history.</div>
                )}
              </div>
            </section>
          </div>
        </section>
      </div>
    </main>
  );
}
