import "./globals.css";
import type { ReactNode } from "react";
import { AppShell } from "../components/layout/AppShell";

export const metadata = {
  title: "OpsPilot",
  description: "Measured agentic AI for customer feedback triage",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className="bg-[#05070b] text-slate-100 antialiased"><AppShell>{children}</AppShell></body>
    </html>
  );
}
