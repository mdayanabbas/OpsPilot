"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

type ApprovalActionsProps = {
  workflowRunId: number;
  itemType: "ticket" | "reply";
  itemId: number;
};

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export function ApprovalActions({ workflowRunId, itemType, itemId }: ApprovalActionsProps) {
  const router = useRouter();
  const [pendingDecision, setPendingDecision] = useState<"approve" | "reject" | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function submitDecision(decision: "approve" | "reject") {
    setPendingDecision(decision);
    setError(null);

    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/approvals/${decision}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          workflow_run_id: workflowRunId,
          item_type: itemType,
          item_id: itemId,
          reviewer_note: null,
        }),
      });

      if (!response.ok) {
        const message = await response.text();
        throw new Error(message || `Approval request failed with status ${response.status}`);
      }

      router.refresh();
      setPendingDecision(null);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to submit approval decision.");
      setPendingDecision(null);
    }
  }

  const isLoading = pendingDecision !== null;

  return (
    <div className="mt-5 border-t border-white/10 pt-5">
      <div className="flex flex-col gap-3 sm:flex-row">
        <button
          type="button"
          disabled={isLoading}
          onClick={() => submitDecision("approve")}
          className="inline-flex min-h-11 flex-1 items-center justify-center rounded-2xl border border-emerald-300/25 bg-emerald-300/10 px-4 py-2 text-sm font-bold text-emerald-100 shadow-lg shadow-emerald-950/20 transition hover:bg-emerald-300/15 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {pendingDecision === "approve" ? "Approving..." : "Approve"}
        </button>
        <button
          type="button"
          disabled={isLoading}
          onClick={() => submitDecision("reject")}
          className="inline-flex min-h-11 flex-1 items-center justify-center rounded-2xl border border-rose-300/25 bg-rose-300/10 px-4 py-2 text-sm font-bold text-rose-100 shadow-lg shadow-rose-950/20 transition hover:bg-rose-300/15 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {pendingDecision === "reject" ? "Rejecting..." : "Reject"}
        </button>
      </div>

      {error ? (
        <div className="mt-3 rounded-2xl border border-rose-400/25 bg-rose-400/10 p-3 text-xs leading-5 text-rose-100">
          {error}
        </div>
      ) : null}
    </div>
  );
}
