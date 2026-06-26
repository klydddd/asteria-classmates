"use client";

import { useEffect, useState, useCallback } from "react";
import { getProjectStatus, type ProjectStatus } from "@/lib/api";
import StatusCard from "@/components/status-card";
import { Button } from "@/components/ui/button";

import ComparisonChart from "@/components/comparison-chart";

const POLL_INTERVAL = 10_000;

function fmt(n: number | undefined | null, suffix?: string): string | null {
  if (n == null) return null;
  return suffix ? `${n}${suffix}` : String(n);
}

function pct(n: number | undefined | null): string | null {
  if (n == null) return null;
  return `${(n * 100).toFixed(1)}%`;
}

export default function DashboardGrid() {
  const [status, setStatus] = useState<ProjectStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [updatedAt, setUpdatedAt] = useState<string | null>(null);

  const fetchStatus = useCallback(async () => {
    try {
      const data = await getProjectStatus();
      setStatus(data);
      setError(null);
      setUpdatedAt(new Date().toLocaleTimeString());
    } catch {
      setError("Could not reach the API. Is the backend running?");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchStatus();
    const id = setInterval(fetchStatus, POLL_INTERVAL);
    return () => clearInterval(id);
  }, [fetchStatus]);

  const cards = [
    { label: "Dataset Clips", value: fmt(status?.dataset_stats?.total_clips) },
    { label: "Baseline WER", value: pct(status?.baseline_metrics?.wer) },
    { label: "Fine-tuned WER", value: pct(status?.finetuned_metrics?.wer) },
    { label: "Model Version", value: status?.model_version ?? null },
  ];

  return (
    <section>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-foreground font-serif">Pipeline Dashboard</h1>
        {updatedAt && (
          <span className="text-xs text-muted-foreground">Last updated {updatedAt}</span>
        )}
      </div>

      {error && (
        <div className="mb-6 rounded-lg border border-destructive/40 bg-destructive/10 px-4 py-3 flex items-center justify-between">
          <p className="text-sm text-destructive">{error}</p>
          <Button variant="outline" size="sm" onClick={fetchStatus}>
            Retry
          </Button>
        </div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {cards.map((c) => (
          <StatusCard key={c.label} label={c.label} value={c.value} loading={loading && !error} />
        ))}
      </div>

      {(!loading || status) && (
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
          <ComparisonChart
            baselineMetrics={status?.baseline_metrics}
            finetunedMetrics={status?.finetuned_metrics}
            datasetStats={status?.dataset_stats}
          />
        </div>
      )}
    </section>
  );
}
