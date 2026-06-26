import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

interface StatusCardProps {
  label: string;
  value: string | null;
  loading: boolean;
}

export default function StatusCard({ label, value, loading }: StatusCardProps) {
  return (
    <Card className="bg-surface border-border">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium text-foreground/70 font-serif">
          {label}
        </CardTitle>
      </CardHeader>
      <CardContent>
        {loading ? (
          <Skeleton data-testid="status-card-skeleton" className="h-8 w-24" />
        ) : (
          <p className="text-2xl font-bold text-foreground font-serif">
            {value ?? "—"}
          </p>
        )}
      </CardContent>
    </Card>
  );
}
