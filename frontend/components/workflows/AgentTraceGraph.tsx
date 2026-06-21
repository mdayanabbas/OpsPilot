import type { ReactNode } from "react";


type Workflow = {
  id: number;
  input_text: string;
  status: string;
  workflow_type: string;
};

type PlannerDecision = {
  plan_type: string;
  planner_provider: string;
  used_fallback: boolean;
  reasoning_summary: string;
} | null;

type AgentExecution = {
  tool_name: string;
  status: string;
  result_summary: string | null;
  error_message: string | null;
};

type ToolCall = {
  step_name: string;
  tool_name: string;
  provider: string;
  status: string;
  fallback_used: boolean;
};

type Outputs = {
  tickets: Array<{ title: string; priority: string }>;
  customer_replies: Array<{ risk_level: string }>;
  evaluation: { quality_score: number | null } | null;
};

type Critic = {
  critic_status: string;
  recommended_action: string;
} | null;

type Replay = {
  replay_workflow_run_id: number;
  changed: boolean;
  diff_summary: string;
};

type NodeStatus = "completed" | "skipped" | "warning" | "failed";

type GraphNode = {
  key: string;
  label: string;
  status: NodeStatus;
  provider?: string | null;
  fallback?: boolean;
  summary: string;
};

type Props = {
  workflow: Workflow;
  plannerDecision: PlannerDecision;
  agentExecutions: AgentExecution[];
  toolCalls: ToolCall[];
  outputs: Outputs;
  critic: Critic;
  replayHistory: Replay[];
};

function truncate(value: string, limit = 92) {
  return value.length > limit ? `${value.slice(0, limit - 1)}…` : value;
}

function titleize(value: string) {
  return value.replaceAll("_", " ");
}

function statusClasses(status: NodeStatus) {
  if (status === "completed") return "border-emerald-300/25 bg-emerald-300/[0.07] text-emerald-100 shadow-emerald-950/20";
  if (status === "warning") return "border-amber-300/30 bg-amber-300/[0.08] text-amber-100 shadow-amber-950/20";
  if (status === "failed") return "border-rose-300/30 bg-rose-300/[0.08] text-rose-100 shadow-rose-950/20";
  return "border-slate-500/25 bg-slate-500/[0.07] text-slate-300 shadow-slate-950/20";
}

function GraphCard({ node }: { node: GraphNode }) {
  return (
    <article className={`w-56 shrink-0 rounded-2xl border p-4 shadow-xl ${statusClasses(node.status)}`}>
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-[0.18em] opacity-60">Agent Node</p>
          <h3 className="mt-1 text-sm font-semibold text-white">{node.label}</h3>
        </div>
        <span className="rounded-full border border-current/20 bg-black/15 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide">
          {node.status}
        </span>
      </div>

      <p className="mt-3 min-h-12 text-xs leading-5 text-slate-300">{node.summary}</p>

      <div className="mt-3 flex flex-wrap gap-1.5">
        {node.provider ? (
          <span className="rounded-full border border-white/10 bg-black/20 px-2 py-1 text-[10px] font-medium text-slate-300">
            {titleize(node.provider)}
          </span>
        ) : null}
        {node.fallback ? (
          <span className="rounded-full border border-amber-300/25 bg-amber-300/10 px-2 py-1 text-[10px] font-semibold text-amber-100">
            fallback
          </span>
        ) : null}
      </div>
    </article>
  );
}

function Arrow({ children = "→" }: { children?: ReactNode }) {
  return <div className="flex shrink-0 items-center justify-center px-2 text-lg text-sky-300/45">{children}</div>;
}

function FlowRow({ nodes }: { nodes: GraphNode[] }) {
  return (
    <div className="overflow-x-auto pb-2">
      <div className="flex min-w-max items-stretch">
        {nodes.map((node, index) => (
          <div className="flex" key={node.key}>
            <GraphCard node={node} />
            {index < nodes.length - 1 ? <Arrow /> : null}
          </div>
        ))}
      </div>
    </div>
  );
}

export function AgentTraceGraph({
  workflow,
  plannerDecision,
  agentExecutions,
  toolCalls,
  outputs,
  critic,
  replayHistory,
}: Props) {
  const call = (step: string) => toolCalls.find((item) => item.step_name === step);
  const statusFor = (evidence: boolean, toolCall?: ToolCall, warning = false): NodeStatus => {
    if (toolCall?.status === "failed") return "failed";
    if (warning || toolCall?.fallback_used) return "warning";
    return evidence || toolCall?.status === "success" ? "completed" : "skipped";
  };
  const nodeFromCall = (
    key: string,
    label: string,
    step: string,
    summary: string,
    evidence = false,
  ): GraphNode => {
    const toolCall = call(step);
    return {
      key,
      label,
      status: statusFor(evidence, toolCall),
      provider: toolCall?.provider,
      fallback: toolCall?.fallback_used,
      summary,
    };
  };

  const executionErrors = agentExecutions.filter((item) => item.status === "error").length;
  const executionSkips = agentExecutions.filter((item) => item.status === "skipped").length;
  const executionSuccesses = agentExecutions.filter((item) => item.status === "executed").length;
  const memoryExecution = agentExecutions.find((item) => item.tool_name === "search_memory");
  const memoryCall = toolCalls.find((item) => item.tool_name === "search_memory");
  const latestReplay = replayHistory[0];

  const spine: GraphNode[] = [
    {
      key: "input",
      label: "Customer Input",
      status: "completed",
      summary: truncate(workflow.input_text),
    },
    nodeFromCall("intent", "Intent Router", "intent_router", `Classified as ${titleize(workflow.workflow_type)}.`),
    nodeFromCall("extract", "Issue Extraction", "issue_extraction", "Converted customer input into structured issue data."),
    nodeFromCall("normalize", "Issue Normalization", "issue_normalization", "Applied deterministic taxonomy and clarification rules."),
    {
      key: "planner",
      label: "Planner",
      status: statusFor(Boolean(plannerDecision), call("planner"), Boolean(plannerDecision?.used_fallback)),
      provider: plannerDecision?.planner_provider ?? call("planner")?.provider,
      fallback: plannerDecision?.used_fallback ?? call("planner")?.fallback_used,
      summary: plannerDecision ? `${titleize(plannerDecision.plan_type)} — ${truncate(plannerDecision.reasoning_summary, 72)}` : "No planner decision recorded.",
    },
    {
      key: "executor",
      label: "Dynamic Tool Executor",
      status: executionErrors ? "failed" : agentExecutions.length ? "completed" : "skipped",
      provider: agentExecutions.length ? "deterministic" : null,
      summary: agentExecutions.length
        ? `${executionSuccesses} executed, ${executionSkips} skipped, ${executionErrors} error(s).`
        : "No dynamic tool traces recorded.",
    },
  ];

  const outputsLane: GraphNode[] = [
    nodeFromCall(
      "ticket",
      "Ticket Generation",
      "ticket_generation",
      outputs.tickets[0] ? `${truncate(outputs.tickets[0].title, 64)} · ${outputs.tickets[0].priority} priority` : "No ticket generated.",
      outputs.tickets.length > 0,
    ),
    nodeFromCall(
      "reply",
      "Customer Reply",
      "reply_generation",
      outputs.customer_replies[0] ? `${outputs.customer_replies[0].risk_level} risk reply draft created.` : "No customer reply generated.",
      outputs.customer_replies.length > 0,
    ),
    {
      key: "evaluation",
      label: "Evaluation",
      status: statusFor(Boolean(outputs.evaluation), call("evaluation")),
      provider: call("evaluation")?.provider,
      fallback: call("evaluation")?.fallback_used,
      summary: outputs.evaluation?.quality_score != null
        ? `Quality score ${Math.round(outputs.evaluation.quality_score * 100)}%.`
        : "No evaluation result recorded.",
    },
    {
      key: "critic",
      label: "Critic Review",
      status: statusFor(Boolean(critic), call("critic"), critic?.critic_status === "warning"),
      provider: call("critic")?.provider,
      fallback: call("critic")?.fallback_used,
      summary: critic ? `${titleize(critic.critic_status)} — ${truncate(critic.recommended_action, 68)}` : "No critic result recorded.",
    },
  ];

  const branches: GraphNode[] = [
    {
      key: "memory",
      label: "Memory",
      status: memoryExecution?.status === "error" || memoryCall?.status === "failed"
        ? "failed"
        : memoryExecution?.status === "executed" || memoryCall?.status === "success"
          ? memoryCall?.fallback_used ? "warning" : "completed"
          : "skipped",
      provider: memoryCall?.provider ?? (memoryExecution ? "deterministic" : null),
      fallback: memoryCall?.fallback_used,
      summary: memoryExecution?.result_summary || "No memory search recorded for this run.",
    },
  ];
  if (latestReplay) {
    branches.push({
      key: "replay",
      label: "Replay Diff",
      status: "completed",
      provider: "deterministic",
      summary: `Replay #${latestReplay.replay_workflow_run_id}: ${truncate(latestReplay.diff_summary, 70)}`,
    });
  }

  return (
    <section className="overflow-hidden rounded-3xl border border-white/10 bg-slate-950/60 shadow-2xl shadow-black/30 backdrop-blur-xl">
      <div className="flex flex-col gap-2 border-b border-white/10 px-6 py-5 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-sky-300/60">Derived execution topology</p>
          <h2 className="mt-1 text-lg font-semibold tracking-tight text-white">Agent Trace Graph</h2>
        </div>
        <p className="text-xs text-slate-500">Visual only · built from existing run APIs</p>
      </div>

      <div className="space-y-3 p-5 sm:p-6">
        <FlowRow nodes={spine} />
        <div className="flex items-center gap-3 pl-24 text-xs font-semibold uppercase tracking-[0.16em] text-sky-300/45">
          <span className="h-8 w-px bg-gradient-to-b from-sky-300/40 to-sky-300/10" />
          downstream fan-out
        </div>
        <div className="grid gap-4 xl:grid-cols-[minmax(0,4fr)_minmax(224px,1fr)]">
          <FlowRow nodes={outputsLane} />
          <div className="space-y-3 border-l border-sky-300/15 pl-4">
            {branches.map((node) => <GraphCard key={node.key} node={node} />)}
          </div>
        </div>
      </div>
    </section>
  );
}
