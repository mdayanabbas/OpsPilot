"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { type ReactNode, useEffect, useMemo, useState } from "react";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

const NAV_ITEMS = [
  ["Overview", "/", "01"],
  ["Executive", "/dashboard", "02"],
  ["New workflow", "/workflows/new", "03"],
  ["Runs", "/runs", "04"],
  ["Approvals", "/approvals", "05"],
  ["Benchmarks", "/benchmarks", "06"],
  ["Monitoring", "/monitoring", "07"],
  ["Incidents", "/incidents", "08"],
] as const;

function isActive(pathname: string, href: string) {
  if (href === "/") return pathname === "/";
  if (href === "/workflows/new") return pathname.startsWith("/workflows");
  return pathname === href || pathname.startsWith(`${href}/`);
}

function routeName(pathname: string) {
  if (pathname === "/dashboard") return "Executive control center";
  if (pathname.startsWith("/workflows")) return "Workflow launcher";
  if (pathname.startsWith("/runs/live")) return "Live execution";
  if (pathname.startsWith("/runs/")) return "Run intelligence";
  if (pathname.startsWith("/runs")) return "Execution ledger";
  if (pathname.startsWith("/approvals")) return "Human approval center";
  if (pathname.startsWith("/benchmarks")) return "Regression laboratory";
  if (pathname.startsWith("/monitoring")) return "System telemetry";
  if (pathname.startsWith("/incidents")) return "Incident command";
  return "Operations workspace";
}

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const [pendingApprovals, setPendingApprovals] = useState(0);
  const [apiConnected, setApiConnected] = useState(true);

  useEffect(() => {
    if (pathname === "/") return;

    let active = true;
    fetch(`${API_BASE_URL}/api/v1/approvals/stats`, { cache: "no-store" })
      .then((response) => {
        if (!response.ok) throw new Error("Approval stats unavailable");
        return response.json() as Promise<{ pending_count: number }>;
      })
      .then((stats) => {
        if (active) {
          setPendingApprovals(stats.pending_count);
          setApiConnected(true);
        }
      })
      .catch(() => {
        if (active) setApiConnected(false);
      });

    return () => {
      active = false;
    };
  }, [pathname]);

  const activeIndex = useMemo(
    () => NAV_ITEMS.find(([, href]) => isActive(pathname, href))?.[2] ?? "00",
    [pathname],
  );

  if (pathname === "/") return children;

  return (
    <div className="opspilot-route-shell min-h-screen bg-[#07090d] text-slate-100 selection:bg-lime-200 selection:text-slate-950">
      <div className="pointer-events-none fixed inset-0 opacity-[0.035] [background-image:linear-gradient(rgba(255,255,255,.8)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,.8)_1px,transparent_1px)] [background-size:48px_48px]" />

      <aside className="fixed inset-y-0 left-0 z-30 hidden w-64 border-r border-white/[0.08] bg-[#080a0e]/95 px-5 py-6 backdrop-blur-xl lg:flex lg:flex-col">
        <Link href="/" className="flex items-center gap-3">
          <span className="grid h-9 w-9 place-items-center border border-lime-200/30 bg-lime-200 text-sm font-black text-[#080a0e]">OP</span>
          <span>
            <strong className="block text-sm tracking-tight text-[#f4f2eb]">OpsPilot</strong>
            <small className="text-[10px] uppercase tracking-[0.19em] text-slate-600">Control system</small>
          </span>
        </Link>

        <div className="mt-10 text-[9px] font-semibold uppercase tracking-[0.22em] text-slate-700">Workspace / Primary</div>
        <nav className="mt-3 space-y-0.5">
          {NAV_ITEMS.map(([name, href, index]) => {
            const active = isActive(pathname, href);
            return (
              <Link key={href} href={href} className={`group flex items-center gap-3 border-l-2 px-3 py-2.5 text-sm transition ${active ? "border-lime-200 bg-lime-200/[0.07] text-[#f4f2eb]" : "border-transparent text-slate-500 hover:border-slate-600 hover:bg-white/[0.025] hover:text-slate-200"}`}>
                <span className={`font-mono text-[9px] ${active ? "text-lime-200" : "text-slate-700"}`}>{index}</span>
                <span>{name}</span>
                {name === "Approvals" && pendingApprovals ? <span className="ml-auto min-w-5 bg-amber-300 px-1.5 py-0.5 text-center font-mono text-[9px] font-bold text-amber-950">{pendingApprovals}</span> : null}
              </Link>
            );
          })}
        </nav>

        <div className="mt-auto border-t border-white/[0.08] pt-5">
          <div className="flex items-center gap-2 text-xs text-slate-500"><span className={`h-1.5 w-1.5 rounded-full ${apiConnected ? "animate-pulse bg-emerald-300" : "bg-rose-300"}`} />{apiConnected ? "API connected" : "API unavailable"}</div>
          <p className="mt-2 font-mono text-[9px] uppercase tracking-[0.16em] text-slate-700">Deterministic policies active</p>
        </div>
      </aside>

      <div className="relative min-h-screen lg:pl-64">
        <header className="sticky top-0 z-20 border-b border-white/[0.08] bg-[#07090d]/90 px-4 py-3 backdrop-blur-xl sm:px-7">
          <div className="mx-auto flex max-w-[1500px] items-center justify-between gap-4">
            <div className="flex min-w-0 items-center gap-3"><span className="font-mono text-[10px] uppercase tracking-[0.18em] text-slate-600">OP / {activeIndex}</span><span className="h-3 w-px bg-white/10" /><span className="truncate text-xs text-slate-400">{routeName(pathname)}</span></div>
            <div className="flex items-center gap-2"><Link href="/approvals" className="hidden border border-white/10 px-3 py-2 font-mono text-[10px] uppercase tracking-wider text-slate-400 transition hover:border-amber-200/30 hover:text-amber-100 sm:block">Approvals{pendingApprovals ? ` · ${pendingApprovals}` : ""}</Link><Link href="/workflows/new" className="bg-lime-200 px-4 py-2 text-xs font-bold text-[#0a0c10] transition hover:bg-lime-100">Run workflow +</Link></div>
          </div>
        </header>

        <div className="flex gap-2 overflow-x-auto border-b border-white/[0.06] px-4 py-3 lg:hidden">{NAV_ITEMS.map(([name, href]) => <Link key={href} href={href} className={`shrink-0 border px-3 py-2 text-xs ${isActive(pathname, href) ? "border-lime-200/40 bg-lime-200/10 text-lime-100" : "border-white/10 text-slate-500"}`}>{name}</Link>)}</div>

        <div className="opspilot-route-content relative">{children}</div>
      </div>
    </div>
  );
}
