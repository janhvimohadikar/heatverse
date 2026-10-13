import type { ReactNode } from "react";
import type { RiskCategory } from "../types";

export const RISK_COLORS: Record<RiskCategory, string> = { Low: "#2F855A", Moderate: "#D69E2E", High: "#DD6B20", Extreme: "#C53030" };

export function PageHeader({ eyebrow, title, subtitle, actions }: { eyebrow?: string; title: string; subtitle?: string; actions?: ReactNode }) {
  return (
    <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
      <div>
        {eyebrow && <p className="text-xs font-semibold uppercase tracking-widest text-heat-orange">{eyebrow}</p>}
        <h1 className="text-2xl font-bold">{title}</h1>
        {subtitle && <p className="mt-1 max-w-3xl text-sm text-slate-600 dark:text-slate-400">{subtitle}</p>}
      </div>
      {actions}
    </div>
  );
}

export function Card({ title, subtitle, children, className = "", actions }: { title?: string; subtitle?: string; children: ReactNode; className?: string; actions?: ReactNode }) {
  return (
    <section className={`card ${className}`}>
      {(title || actions) && (
        <header className="mb-3 flex items-start justify-between gap-2">
          <div>
            {title && <h2 className="text-base font-semibold">{title}</h2>}
            {subtitle && <p className="text-xs text-slate-500 dark:text-slate-400">{subtitle}</p>}
          </div>
          {actions}
        </header>
      )}
      {children}
    </section>
  );
}

export function StatCard({ label, value, hint }: { label: string; value: ReactNode; hint?: string }) {
  return (
    <div className="card">
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">{label}</p>
      <p className="mt-1 text-2xl font-bold text-navy-900 dark:text-white">{value}</p>
      {hint && <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">{hint}</p>}
    </div>
  );
}

export function Spinner({ label = "Loading…" }: { label?: string }) {
  return (
    <div role="status" className="flex items-center gap-2 py-6 text-sm text-slate-500 dark:text-slate-400">
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-slate-300 border-t-heat-orange" />
      {label}
    </div>
  );
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div role="alert" className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-800 dark:border-red-900 dark:bg-red-950 dark:text-red-200">
      <p>{message}</p>
      {onRetry && <button className="btn-secondary mt-2" onClick={onRetry}>Try again</button>}
    </div>
  );
}

export function EmptyState({ children }: { children: ReactNode }) {
  return <p className="rounded-md border border-dashed border-slate-300 p-4 text-sm text-slate-500 dark:border-navy-600 dark:text-slate-400">{children}</p>;
}

export function Notice({ tone = "info", children }: { tone?: "info" | "demo" | "warn"; children: ReactNode }) {
  const styles = {
    info: "border-sky-200 bg-sky-50 text-sky-900 dark:border-sky-900 dark:bg-sky-950 dark:text-sky-100",
    demo: "border-amber-300 bg-amber-50 text-amber-900 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-100",
    warn: "border-red-200 bg-red-50 text-red-900 dark:border-red-900 dark:bg-red-950 dark:text-red-100",
  }[tone];
  return <div className={`rounded-md border px-3 py-2 text-sm ${styles}`}>{children}</div>;
}

export function RiskBadge({ category, score }: { category: RiskCategory | null | undefined; score?: number | null }) {
  if (!category) return <span className="rounded px-2 py-0.5 text-xs font-semibold bg-slate-200 text-slate-700 dark:bg-navy-700 dark:text-slate-200">No data</span>;
  return (
    <span className="inline-flex items-center gap-1 rounded px-2 py-0.5 text-xs font-semibold text-white" style={{ backgroundColor: RISK_COLORS[category] }}>
      {category}{score !== undefined && score !== null ? ` · ${score}` : ""}
    </span>
  );
}

const TYPE_STYLES: Record<string, string> = {
  observed: "bg-sky-100 text-sky-900 dark:bg-sky-950 dark:text-sky-200",
  derived: "bg-indigo-100 text-indigo-900 dark:bg-indigo-950 dark:text-indigo-200",
  live: "bg-emerald-100 text-emerald-900 dark:bg-emerald-950 dark:text-emerald-200",
  demo: "bg-amber-200 text-amber-900 dark:bg-amber-900 dark:text-amber-100",
  interpolated: "bg-purple-100 text-purple-900 dark:bg-purple-950 dark:text-purple-200",
  predicted: "bg-fuchsia-100 text-fuchsia-900 dark:bg-fuchsia-950 dark:text-fuchsia-200",
};

/** Always shows WHERE a number came from: observed, derived, live, demo, interpolated or predicted. */
export function DataBadge({ type }: { type: keyof typeof TYPE_STYLES | string }) {
  const label = type === "demo" ? "DEMO data" : type.charAt(0).toUpperCase() + type.slice(1);
  return <span className={`rounded px-2 py-0.5 text-xs font-semibold ${TYPE_STYLES[type] ?? TYPE_STYLES.observed}`}>{label}</span>;
}

export function ScoreBar({ score, category }: { score: number | null; category: RiskCategory | null }) {
  return (
    <div className="w-full" role="img" aria-label={score === null ? "No score" : `Score ${score} of 100`}>
      <div className="h-2.5 w-full overflow-hidden rounded-full bg-slate-200 dark:bg-navy-700">
        <div className="h-full rounded-full" style={{ width: `${score ?? 0}%`, backgroundColor: category ? RISK_COLORS[category] : "#94a3b8" }} />
      </div>
    </div>
  );
}

export const fmt = (v: number | null | undefined, digits = 1, unit = ""): string =>
  v === null || v === undefined || Number.isNaN(v) ? "—" : `${v.toFixed(digits)}${unit}`;

export const fmtDate = (iso: string | null | undefined): string => {
  if (!iso) return "—";
  const d = new Date(iso.length === 10 ? `${iso}T00:00:00` : iso);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" });
};
