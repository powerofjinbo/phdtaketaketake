import type { RunStatus } from "@/lib/store";

const styles: Record<RunStatus, string> = {
  researching: "bg-indigo-500/12 text-indigo-200 border-indigo-400/30",
  scoring: "bg-violet-500/12 text-violet-200 border-violet-400/30",
  done: "bg-emerald-500/12 text-emerald-200 border-emerald-400/30",
  error: "bg-rose-500/12 text-rose-200 border-rose-400/30",
};

const dots: Record<RunStatus, string> = {
  researching: "bg-indigo-300",
  scoring: "bg-violet-300",
  done: "bg-emerald-300",
  error: "bg-rose-300",
};

const labels: Record<RunStatus, string> = {
  researching: "Researching",
  scoring: "Scoring",
  done: "Done",
  error: "Error",
};

export const ACTIVE_STATUSES: RunStatus[] = ["researching", "scoring"];

export default function StatusChip({ status }: { status: RunStatus }) {
  const active = ACTIVE_STATUSES.includes(status);
  return (
    <span
      className={`inline-flex shrink-0 items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium backdrop-blur ${styles[status]}`}
    >
      <span className="relative flex h-1.5 w-1.5">
        {active && (
          <span className={`pulse-ring absolute inline-flex h-full w-full rounded-full ${dots[status]}`} />
        )}
        <span className={`relative inline-flex h-1.5 w-1.5 rounded-full ${dots[status]}`} />
      </span>
      {labels[status]}
    </span>
  );
}
