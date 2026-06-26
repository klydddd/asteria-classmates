"use client";

import { useEffect, useState, useCallback } from "react";
import { getProjectStatus, type ProjectStatus } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import ComparisonChart from "@/components/comparison-chart";
import Mermaid from "@/components/mermaid";

const PIPELINE_DIAGRAM = `
flowchart LR
    subgraph core[BosesPH Core Pipeline]
        A[Raw Audio & Transcripts] --> B(Ingest & Validate)
        B --> C(Normalize & Review)
        C --> D(Build Dataset)
        D --> E(Transcribe & Evaluate)
        E --> F[ASR Benchmark]
        D --> G(Fine-tune ASR)
        G --> H[Fine-tuned Model]
    end
`;
const POLL_INTERVAL = 10_000;

function pct(n: number | null | undefined): string | null {
  if (n == null) return null;
  return `${(n * 100).toFixed(1)}%`;
}

function fmt(n: number | null | undefined): string | null {
  if (n == null) return null;
  return String(n);
}

function MetricCard({
  label,
  value,
  loading,
  sub,
}: {
  label: string;
  value: string | null;
  loading: boolean;
  sub?: string;
}) {
  return (
    <div className="bg-surface rounded-xl border border-border p-5 flex flex-col justify-between h-full">
      <span className="text-xs font-semibold font-sans text-muted-foreground uppercase tracking-widest">
        {label}
      </span>
      <div>
        {loading ? (
          <Skeleton className="h-10 w-24 mt-3" />
        ) : (
          <span className="block text-4xl font-bold font-serif tabular-nums text-foreground leading-none mt-3">
            {value ?? "—"}
          </span>
        )}
        {sub && (
          <span className="block text-xs font-sans text-muted-foreground mt-2">{sub}</span>
        )}
      </div>
    </div>
  );
}

function WerHeroCard({
  baseline,
  finetuned,
  loading,
}: {
  baseline: number | null | undefined;
  finetuned: number | null | undefined;
  loading: boolean;
}) {
  const reductionFraction =
    baseline != null && finetuned != null && baseline > 0
      ? (baseline - finetuned) / baseline
      : null;
  const ppImprovement =
    baseline != null && finetuned != null
      ? ((baseline - finetuned) * 100).toFixed(1)
      : null;

  return (
    <div className="bg-surface rounded-xl border border-border p-6 col-span-2 flex flex-col justify-between">
      {/* Header */}
      <div className="flex items-start justify-between">
        <span className="text-xs font-semibold font-sans text-muted-foreground uppercase tracking-widest">
          Word Error Rate
        </span>
        {reductionFraction != null && (
          <span className="text-xs font-semibold font-sans text-accent bg-accent/10 rounded-md px-2.5 py-1">
            −{(reductionFraction * 100).toFixed(0)}% reduction
          </span>
        )}
      </div>

      {/* Numbers */}
      <div className="flex items-end gap-6 my-6">
        <div>
          <p className="text-xs font-sans text-muted-foreground mb-2">Baseline</p>
          {loading ? (
            <Skeleton className="h-12 w-28" />
          ) : (
            <p className="text-5xl font-bold font-serif tabular-nums text-foreground/40 leading-none">
              {pct(baseline) ?? "—"}
            </p>
          )}
        </div>

        <svg
          width="28"
          height="20"
          viewBox="0 0 28 20"
          fill="none"
          className="text-muted-foreground/25 mb-2 shrink-0"
        >
          <path
            d="M2 10h22M16 4l8 6-8 6"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>

        <div>
          <p className="text-xs font-sans text-muted-foreground mb-2">Fine-tuned</p>
          {loading ? (
            <Skeleton className="h-12 w-28" />
          ) : (
            <p className="text-5xl font-bold font-serif tabular-nums text-accent leading-none">
              {pct(finetuned) ?? "—"}
            </p>
          )}
        </div>
      </div>

      {/* Progress bar + label */}
      <div>
        {reductionFraction != null ? (
          <div className="h-1.5 rounded-full bg-muted overflow-hidden mb-2">
            <div
              className="h-full bg-accent rounded-full transition-all duration-1000 ease-out"
              style={{ width: `${reductionFraction * 100}%` }}
            />
          </div>
        ) : (
          <div className="h-1.5 rounded-full bg-muted mb-2" />
        )}
        <p className="text-xs font-sans text-muted-foreground">
          {ppImprovement != null
            ? `${ppImprovement} percentage-point improvement over baseline`
            : "Awaiting model evaluation"}
        </p>
      </div>
    </div>
  );
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
    const t = window.setTimeout(fetchStatus, 0);
    const id = setInterval(fetchStatus, POLL_INTERVAL);
    return () => {
      window.clearTimeout(t);
      clearInterval(id);
    };
  }, [fetchStatus]);

  return (
    <section className="space-y-8 h-full">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-foreground font-serif">
          Pipeline Dashboard
        </h1>
        {updatedAt && (
          <span className="text-xs text-muted-foreground font-sans tabular-nums">
            Updated {updatedAt}
          </span>
        )}
      </div>

      {/* API error */}
      {error && (
        <div className="rounded-xl border border-destructive/30 bg-destructive/5 px-5 py-4 flex items-center justify-between gap-4">
          <p className="text-sm text-destructive font-sans">{error}</p>
          <Button
            variant="outline"
            size="sm"
            onClick={fetchStatus}
            className="shrink-0 font-sans"
          >
            Retry
          </Button>
        </div>
      )}

      {/* Metrics row: hero WER card (50%) + 2 supporting cards (25% each) */}
      <div className="grid grid-cols-4 gap-4 auto-rows-fr">
        <WerHeroCard
          baseline={status?.baseline_metrics?.wer}
          finetuned={status?.finetuned_metrics?.wer}
          loading={loading && !error}
        />
        <MetricCard
          label="Training Speakers"
          value={fmt(status?.dataset_stats?.total_speakers)}
          loading={loading && !error}
          sub="Kapampangan native speakers"
        />
        <MetricCard
          label="Fine-tuned CER"
          value={pct(status?.finetuned_metrics?.cer)}
          loading={loading && !error}
          sub="Character error rate"
        />
      </div>

      {/* Chart section */}
      {(!loading || status) && (
        <div className="space-y-3">
          <p className="text-xs font-semibold font-sans text-muted-foreground uppercase tracking-widest">
            Model Progression
          </p>
          <ComparisonChart
            baselineMetrics={status?.baseline_metrics}
            previousFinetunedMetrics={status?.previous_finetuned_metrics}
            finetunedMetrics={status?.finetuned_metrics}
            datasetStats={status?.dataset_stats}
          />
        </div>
      )}

      {/* Pipeline Diagram */}
      <div className="space-y-3 pt-4">
        <p className="text-xs font-semibold font-sans text-muted-foreground uppercase tracking-widest">
          Pipeline Architecture
        </p>
        <div className="bg-surface rounded-xl border border-border p-6 flex flex-col items-center justify-center min-h-[160px]">
          <Mermaid chart={PIPELINE_DIAGRAM} />
        </div>
      </div>
    </section>
  );
}
