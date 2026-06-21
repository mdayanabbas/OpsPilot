"use client";

import ReactFlow, {
  Background,
  Controls,
  Handle,
  MarkerType,
  MiniMap,
  Position,
  type Edge,
  type Node,
  type NodeProps,
} from "reactflow";
import "reactflow/dist/style.css";


type NodeStatus = "completed" | "warning" | "failed" | "skipped";
type TraceNodeData = {
  label: string;
  status: NodeStatus;
  provider?: string | null;
  fallback?: boolean;
  summary: string;
};

type Workflow = { id: number; input_text: string; status: string; workflow_type: string };
type PlannerDecision = {
  plan_type: string;
  planner_provider: string;
  used_fallback: boolean;
  reasoning_summary: string;
} | null;
type AgentExecution = { tool_name: string; status: string; result_summary: string | null; error_message: string | null };
type ToolCall = { step_name: string; tool_name: string; provider: string; status: string; fallback_used: boolean };
type Outputs = {
  tickets: Array<{ title: string; priority: string }>;
  customer_replies: Array<{ risk_level: string }>;
  evaluation: { quality_score: number | null } | null;
};
type Critic = { critic_status: string; recommended_action: string } | null;
type Replay = { replay_workflow_run_id: number; changed: boolean; diff_summary: string };

type Props = {
  workflow: Workflow;
  plannerDecision: PlannerDecision;
  agentExecutions: AgentExecution[];
  toolCalls: ToolCall[];
  outputs: Outputs;
  critic: Critic;
  replayHistory: Replay[];
};

const NODE_WIDTH = 224;
const statusColor: Record<NodeStatus, string> = {
  completed: "#34d399",
  warning: "#fbbf24",
  failed: "#fb7185",
  skipped: "#64748b",
};

function truncate(value: string, limit = 82) {
  return value.length > limit ? `${value.slice(0, limit - 1)}…` : value;
}

function titleize(value: string) {
  return value.replaceAll("_", " ");
}

function nodeClasses(status: NodeStatus) {
  if (status === "completed") return "border-emerald-300/30 bg-[#0b1917] shadow-emerald-950/40";
  if (status === "warning") return "border-amber-300/35 bg-[#1b160b] shadow-amber-950/40";
  if (status === "failed") return "border-rose-300/35 bg-[#1c0d13] shadow-rose-950/40";
  return "border-slate-500/30 bg-[#111621] shadow-slate-950/40";
}

function TraceNode({ data }: NodeProps<TraceNodeData>) {
  return (
    <div className={`flex h-44 flex-col rounded-2xl border p-4 shadow-2xl backdrop-blur-xl ${nodeClasses(data.status)}`} style={{ width: NODE_WIDTH }}>
      <Handle type="target" position={Position.Top} className="!h-2 !w-2 !border-0 !bg-sky-300" />
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="text-[9px] font-semibold uppercase tracking-[0.18em] text-slate-500">Agent Node</p>
          <h3 className="mt-1 text-sm font-semibold text-white">{data.label}</h3>
        </div>
        <span
          className="rounded-full border px-2 py-0.5 text-[9px] font-bold uppercase tracking-wide"
          style={{ borderColor: `${statusColor[data.status]}55`, color: statusColor[data.status], backgroundColor: `${statusColor[data.status]}12` }}
        >
          {data.status}
        </span>
      </div>
      <p className="mt-3 line-clamp-3 flex-1 text-[11px] leading-[1.15rem] text-slate-300">{data.summary}</p>
      <div className="mt-3 flex flex-wrap gap-1.5">
        {data.provider ? <span className="rounded-full border border-white/10 bg-black/20 px-2 py-1 text-[9px] text-slate-300">{titleize(data.provider)}</span> : null}
        {data.fallback ? <span className="rounded-full border border-amber-300/25 bg-amber-300/10 px-2 py-1 text-[9px] font-semibold text-amber-100">fallback used</span> : null}
      </div>
      <Handle type="source" position={Position.Bottom} className="!h-2 !w-2 !border-0 !bg-sky-300" />
    </div>
  );
}

const nodeTypes = { trace: TraceNode };

function edge(id: string, source: string, target: string, animated = false): Edge {
  return {
    id,
    source,
    target,
    animated,
    type: "smoothstep",
    markerEnd: { type: MarkerType.ArrowClosed, color: "#38bdf8" },
    style: { stroke: "#38bdf8", strokeOpacity: 0.5, strokeWidth: 1.5 },
  };
}

export function AgentTraceFlow({ workflow, plannerDecision, agentExecutions, toolCalls, outputs, critic, replayHistory }: Props) {
  const call = (step: string) => toolCalls.find((item) => item.step_name === step);
  const statusFor = (evidence: boolean, toolCall?: ToolCall, warning = false): NodeStatus => {
    if (toolCall?.status === "failed") return "failed";
    if (warning || toolCall?.fallback_used) return "warning";
    return evidence || toolCall?.status === "success" ? "completed" : "skipped";
  };
  const fromCall = (label: string, step: string, summary: string, evidence = false): TraceNodeData => {
    const toolCall = call(step);
    return { label, status: statusFor(evidence, toolCall), provider: toolCall?.provider, fallback: toolCall?.fallback_used, summary };
  };

  const errors = agentExecutions.filter((item) => item.status === "error").length;
  const executed = agentExecutions.filter((item) => item.status === "executed").length;
  const skipped = agentExecutions.filter((item) => item.status === "skipped").length;
  const memoryTrace = agentExecutions.find((item) => item.tool_name === "search_memory");
  const memoryCall = toolCalls.find((item) => item.tool_name === "search_memory");
  const latestReplay = replayHistory[0];

  const nodes: Node<TraceNodeData>[] = [
    { id: "input", type: "trace", position: { x: 500, y: 0 }, data: { label: "Input", status: "completed", summary: truncate(workflow.input_text) } },
    { id: "intent", type: "trace", position: { x: 500, y: 210 }, data: fromCall("Intent Router", "intent_router", `Classified as ${titleize(workflow.workflow_type)}.`) },
    { id: "extraction", type: "trace", position: { x: 500, y: 420 }, data: fromCall("Issue Extraction", "issue_extraction", "Structured customer issue data extracted.") },
    { id: "normalization", type: "trace", position: { x: 500, y: 630 }, data: fromCall("Issue Normalization", "issue_normalization", "Deterministic taxonomy and clarification applied.") },
    {
      id: "planner",
      type: "trace",
      position: { x: 500, y: 840 },
      data: {
        label: "Planner",
        status: statusFor(Boolean(plannerDecision), call("planner"), Boolean(plannerDecision?.used_fallback)),
        provider: plannerDecision?.planner_provider ?? call("planner")?.provider,
        fallback: plannerDecision?.used_fallback ?? call("planner")?.fallback_used,
        summary: plannerDecision ? `${titleize(plannerDecision.plan_type)} — ${truncate(plannerDecision.reasoning_summary, 60)}` : "No planner decision recorded.",
      },
    },
    {
      id: "executor",
      type: "trace",
      position: { x: 1220, y: 840 },
      data: {
        label: "Dynamic Tool Executor",
        status: errors ? "failed" : agentExecutions.length ? "completed" : "skipped",
        provider: agentExecutions.length ? "deterministic" : null,
        summary: agentExecutions.length ? `${executed} executed, ${skipped} skipped, ${errors} error(s).` : "No dynamic execution traces.",
      },
    },
    { id: "ticket", type: "trace", position: { x: 0, y: 1080 }, data: fromCall("Ticket Generation", "ticket_generation", outputs.tickets[0] ? `${truncate(outputs.tickets[0].title, 58)} · ${outputs.tickets[0].priority}` : "No ticket generated.", outputs.tickets.length > 0) },
    { id: "reply", type: "trace", position: { x: 310, y: 1080 }, data: fromCall("Customer Reply", "reply_generation", outputs.customer_replies[0] ? `${outputs.customer_replies[0].risk_level} risk reply draft created.` : "No reply generated.", outputs.customer_replies.length > 0) },
    {
      id: "evaluation",
      type: "trace",
      position: { x: 620, y: 1080 },
      data: {
        ...fromCall("Evaluation", "evaluation", outputs.evaluation?.quality_score != null ? `Quality score ${Math.round(outputs.evaluation.quality_score * 100)}%.` : "No evaluation result.", Boolean(outputs.evaluation)),
      },
    },
    {
      id: "memory",
      type: "trace",
      position: { x: 930, y: 1080 },
      data: {
        label: "Memory Search",
        status: memoryTrace?.status === "error" || memoryCall?.status === "failed" ? "failed" : memoryTrace?.status === "executed" || memoryCall?.status === "success" ? memoryCall?.fallback_used ? "warning" : "completed" : "skipped",
        provider: memoryCall?.provider ?? (memoryTrace ? "deterministic" : null),
        fallback: memoryCall?.fallback_used,
        summary: memoryTrace?.result_summary || "No memory search recorded.",
      },
    },
    {
      id: "critic",
      type: "trace",
      position: { x: 620, y: 1290 },
      data: {
        ...fromCall("Critic Review", "critic", critic ? `${titleize(critic.critic_status)} — ${truncate(critic.recommended_action, 55)}` : "No critic result.", Boolean(critic)),
        status: statusFor(Boolean(critic), call("critic"), critic?.critic_status === "warning"),
      },
    },
    {
      id: "replay",
      type: "trace",
      position: { x: 1220, y: 580 },
      data: {
        label: "Replay",
        status: latestReplay ? "completed" : "skipped",
        provider: latestReplay ? "deterministic" : null,
        summary: latestReplay ? `Replay #${latestReplay.replay_workflow_run_id}: ${truncate(latestReplay.diff_summary, 58)}` : "No replay history yet.",
      },
    },
  ];

  const edges: Edge[] = [
    edge("input-intent", "input", "intent"),
    edge("intent-extraction", "intent", "extraction"),
    edge("extraction-normalization", "extraction", "normalization"),
    edge("normalization-planner", "normalization", "planner"),
    edge("planner-executor", "planner", "executor", true),
    edge("planner-ticket", "planner", "ticket"),
    edge("planner-reply", "planner", "reply"),
    edge("planner-evaluation", "planner", "evaluation"),
    edge("planner-memory", "planner", "memory"),
    edge("evaluation-critic", "evaluation", "critic"),
  ];

  return (
    <section className="overflow-hidden rounded-3xl border border-white/10 bg-slate-950/65 shadow-2xl shadow-black/30 backdrop-blur-xl">
      <div className="flex flex-col gap-2 border-b border-white/10 px-6 py-5 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-sky-300/60">Interactive execution topology</p>
          <h2 className="mt-1 text-lg font-semibold tracking-tight text-white">Agent Trace Graph</h2>
        </div>
        <p className="text-xs text-slate-500">Drag, pan, zoom · derived from existing run APIs</p>
      </div>
      <div className="h-[760px] bg-[#060912]">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          nodeTypes={nodeTypes}
          fitView
          fitViewOptions={{ padding: 0.12 }}
          minZoom={0.35}
          maxZoom={1.6}
          nodesConnectable={false}
          nodesDraggable
          proOptions={{ hideAttribution: true }}
        >
          <Background color="#334155" gap={24} size={1} />
          <MiniMap
            pannable
            zoomable
            nodeColor={(node) => statusColor[(node.data as TraceNodeData).status]}
            maskColor="rgba(2, 6, 23, 0.72)"
            className="!border !border-white/10 !bg-slate-950/90"
          />
          <Controls className="!overflow-hidden !rounded-xl !border !border-white/10 !bg-slate-950/90 !shadow-xl" />
        </ReactFlow>
      </div>
    </section>
  );
}
