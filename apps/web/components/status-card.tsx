import { Skeleton } from "@/components/ui/skeleton";

interface StatusCardProps {
  label: string;
  value: string | null;
  loading: boolean;
}

export default function StatusCard({ label, value, loading }: StatusCardProps) {
  return (
    <div className="bg-surface rounded-xl border border-border p-5 flex flex-col gap-2">
      <span className="text-xs font-semibold font-sans text-muted-foreground uppercase tracking-widest">
        {label}
      </span>
      {loading ? (
        <Skeleton data-testid="status-card-skeleton" className="h-9 w-28 mt-1" />
      ) : (
        <span className="text-3xl font-bold text-foreground font-serif tabular-nums leading-none mt-1">
          {value ?? "—"}
        </span>
      )}
    </div>
  );
}
