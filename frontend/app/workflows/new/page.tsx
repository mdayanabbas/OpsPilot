"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { API_BASE_URL, withDemoApiKey } from "../../../lib/api";

const API_URL = `${API_BASE_URL}/api/v1/workflows/run`;
const SAMPLE_PROMPT =
  "Acme Corp says invoice still shows unpaid after successful payment. Support suspects billing sync failure.";
type WorkflowRunResponse = {
  id: number;
};

export default function NewWorkflowPage() {
  const router = useRouter();
  const [inputText, setInputText] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const trimmedInput = inputText.trim();
    if (!trimmedInput) {
      setError("Add customer feedback before running the agent.");
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      const response = await fetch(API_URL, {
        method: "POST",
        headers: withDemoApiKey({
          "Content-Type": "application/json",
        }),
        body: JSON.stringify({ input_text: trimmedInput }),
      });

      if (!response.ok) {
        const message = await response.text();
        throw new Error(message || `Request failed with status ${response.status}`);
      }

      const workflowRun = (await response.json()) as WorkflowRunResponse;
      router.push(`/runs/live/${workflowRun.id}`);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to run OpsPilot agent.");
      setIsSubmitting(false);
    }
  }

  return (
    <main className="min-h-screen bg-[#05070b] text-slate-100">
      <div className="fixed inset-0 bg-[linear-gradient(180deg,rgba(15,23,42,0.72),rgba(2,6,23,0.96)),radial-gradient(circle_at_20%_0%,rgba(14,165,233,0.18),transparent_34%),radial-gradient(circle_at_90%_4%,rgba(168,85,247,0.16),transparent_30%)]" />
      <div className="fixed inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-sky-300/40 to-transparent" />

      <div className="relative flex min-h-screen">
        <section className="flex w-full flex-col">
          <div className="mx-auto flex w-full max-w-5xl flex-col gap-6 px-4 py-5 sm:px-6 lg:px-8 lg:py-8">
            <header className="overflow-hidden rounded-3xl border border-white/10 bg-slate-950/70 shadow-2xl shadow-black/30 backdrop-blur-xl">
              <div className="border-b border-white/10 bg-white/[0.035] px-6 py-4">
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-2xl border border-white/10 bg-white/[0.06] text-sm font-bold text-sky-200 lg:hidden">
                    OP
                  </div>
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-500">
                      Workflow Launcher
                    </p>
                    <h1 className="mt-1 text-2xl font-semibold tracking-tight text-white sm:text-3xl">
                      New OpsPilot Run
                    </h1>
                  </div>
                </div>
              </div>

              <div className="px-6 py-6">
                <p className="max-w-3xl text-sm leading-7 text-slate-300">
                  Start with raw customer feedback. OpsPilot will classify intent, extract an actionable issue,
                  generate a draft ticket and reply, then route you to the run details page.
                </p>
              </div>
            </header>

            <form
              onSubmit={handleSubmit}
              className="rounded-3xl border border-white/10 bg-slate-950/55 p-6 shadow-2xl shadow-black/25 backdrop-blur-xl"
            >
              <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">
                    Customer Feedback
                  </p>
                  <h2 className="mt-1 text-lg font-semibold text-white">Paste the support signal</h2>
                </div>

                <button
                  type="button"
                  onClick={() => {
                    setInputText(SAMPLE_PROMPT);
                    setError(null);
                  }}
                  className="rounded-2xl border border-sky-300/20 bg-sky-300/10 px-4 py-2 text-sm font-semibold text-sky-100 shadow-lg shadow-sky-950/20 transition hover:bg-sky-300/15"
                >
                  Use sample prompt
                </button>
              </div>

              <textarea
                value={inputText}
                onChange={(event) => setInputText(event.target.value)}
                placeholder="Example: Acme Corp says invoice still shows unpaid after successful payment..."
                className="mt-5 min-h-56 w-full resize-y rounded-3xl border border-white/10 bg-black/25 px-5 py-4 text-sm leading-7 text-slate-100 outline-none shadow-inner shadow-black/20 transition placeholder:text-slate-600 focus:border-sky-300/45 focus:bg-black/35 focus:ring-4 focus:ring-sky-300/10"
              />

              {error ? (
                <div className="mt-4 rounded-2xl border border-rose-400/25 bg-rose-400/10 p-4 text-sm leading-6 text-rose-200">
                  {error}
                </div>
              ) : null}

              <div className="mt-5 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">

                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="inline-flex items-center justify-center rounded-2xl bg-gradient-to-r from-sky-300 to-violet-400 px-5 py-3 text-sm font-bold text-slate-950 shadow-xl shadow-sky-950/30 transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {isSubmitting ? "Running OpsPilot..." : "Run OpsPilot Agent"}
                </button>
              </div>
            </form>
          </div>
        </section>
      </div>
    </main>
  );
}
