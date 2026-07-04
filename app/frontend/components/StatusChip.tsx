import type { RunStatus } from "@/lib/api";

const styles: Record<RunStatus, string> = {
  queued: "bg-zinc-500/15 text-zinc-300 border-zinc-500/30",
  researching: "bg-indigo-500/15 text-indigo-300 border-indigo-500/30",
  scoring: "bg-violet-500/15 text-violet-300 border-violet-500/30",
  done: "bg-emerald-500/15 text-emerald-300 border-emerald-500/30",
  error: "bg-red-500/15 text-red-300 border-red-500/30",
};

const labels: Record<RunStatus, string> = {
  queued: "Queued",
  researching: "Researching",
  scoring: "Scoring",
  done: "Done",
  error: "Error",
};

export const ACTIVE_STATUSES: RunStatus[] = ["queued", "researching", "scoring"];

export default function StatusChip({ status }: { status: RunStatus }) {
  const active = ACTIVE_STATUSES.includes(status);
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium ${styles[status]}`}
    >
      {active && (
        <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-current" />
      )}
      {labels[status]}
    </span>
  );
}
