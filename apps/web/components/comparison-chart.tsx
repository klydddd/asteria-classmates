"use client";
import { useState } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import type { LegendPayload, TooltipProps } from "recharts";

interface ComparisonChartProps {
  baselineMetrics: { wer: number; cer: number } | null | undefined;
  previousFinetunedMetrics?: { wer: number; cer: number } | null | undefined;
  finetunedMetrics: { wer: number; cer: number } | null | undefined;
  datasetStats?: Record<string, number> | null;
}

type ChartKey = "Baseline" | "15 Speakers" | "30 Speakers" | "Predicted";

function chartKeyFromLegend(dataKey: LegendPayload["dataKey"]): ChartKey | null {
  switch (dataKey) {
    case "Baseline":
    case "15 Speakers":
    case "30 Speakers":
    case "Predicted":
      return dataKey;
    default:
      return null;
  }
}

type MetricTooltipFormatter = NonNullable<TooltipProps["formatter"]>;

export default function ComparisonChart({
  baselineMetrics,
  previousFinetunedMetrics,
  finetunedMetrics,
  datasetStats,
}: ComparisonChartProps) {
  const [hovered, setHovered] = useState<ChartKey | null>(null);

  if (!baselineMetrics && !previousFinetunedMetrics && !finetunedMetrics) {
    return null;
  }

  const targetSize = 1_000_000;
  const currentSize = datasetStats?.total_clips ?? 4_000;
  const scalingFactor = Math.pow(currentSize / targetSize, 0.3);

  const build = (metric: "wer" | "cer", name: string) => [
    {
      name,
      Baseline: baselineMetrics ? +(baselineMetrics[metric] * 100).toFixed(1) : null,
      "15 Speakers": previousFinetunedMetrics
        ? +(previousFinetunedMetrics[metric] * 100).toFixed(1)
        : null,
      "30 Speakers": finetunedMetrics ? +(finetunedMetrics[metric] * 100).toFixed(1) : null,
      Predicted: finetunedMetrics
        ? +(finetunedMetrics[metric] * scalingFactor * 100).toFixed(1)
        : null,
    },
  ];

  const opacity = (key: ChartKey) => (!hovered || hovered === key ? 1 : 0.2);

  const tooltip: MetricTooltipFormatter = (v, n) => [`${v}%`, n];

  const tooltipStyle = {
    backgroundColor: "#fffdf7",
    borderRadius: "8px",
    border: "1px solid #d7d0c0",
    boxShadow: "0 4px 12px rgba(0,0,0,0.07)",
    fontFamily: "inherit",
    fontSize: "12px",
  };

  const BAR = {
    radius: [3, 3, 3, 3] as [number, number, number, number],
    barSize: 32,
  };

  const CHART_PROPS = {
    layout: "vertical" as const,
    margin: { top: 4, right: 32, left: 4, bottom: 4 },
    barCategoryGap: "35%",
  };

  const AXIS_STYLE = { fontSize: 11, fill: "#6b5f52", fontFamily: "inherit" };

  const bars = (
    <>
      <Bar
        name="Baseline"
        dataKey="Baseline"
        fill="#17231b"
        fillOpacity={opacity("Baseline")}
        {...BAR}
        onMouseEnter={() => setHovered("Baseline")}
        onMouseLeave={() => setHovered(null)}
      />
      <Bar
        name="15 Speakers"
        dataKey="15 Speakers"
        fill="#7d5a3c"
        fillOpacity={opacity("15 Speakers")}
        {...BAR}
        onMouseEnter={() => setHovered("15 Speakers")}
        onMouseLeave={() => setHovered(null)}
      />
      <Bar
        name="30 Speakers"
        dataKey="30 Speakers"
        fill="#b33a2b"
        fillOpacity={opacity("30 Speakers")}
        {...BAR}
        onMouseEnter={() => setHovered("30 Speakers")}
        onMouseLeave={() => setHovered(null)}
      />
      <Bar
        name="Predicted"
        dataKey="Predicted"
        fill="#b33a2b"
        fillOpacity={hovered && hovered !== "Predicted" ? 0 : 0.12}
        stroke="#b33a2b"
        strokeDasharray="5 3"
        strokeWidth={1.5}
        strokeOpacity={opacity("Predicted")}
        {...BAR}
        onMouseEnter={() => setHovered("Predicted")}
        onMouseLeave={() => setHovered(null)}
      />
    </>
  );

  return (
    <div className="bg-surface rounded-xl border border-border p-6">
      <div className="flex items-start justify-between mb-6">
        <div>
          <h3 className="text-sm font-bold text-foreground font-serif">Model Performance</h3>
          <p className="text-xs text-muted-foreground font-sans mt-1">
            Error rates (%) — lower is better.{" "}
            <em>Predicted</em> extrapolates to {targetSize.toLocaleString()} clips via power-law
            scaling (α = 0.3).
          </p>
        </div>
      </div>

      <div className="flex flex-col gap-10">
        {/* WER */}
        <div>
          <p className="text-xs font-semibold font-sans text-muted-foreground uppercase tracking-widest mb-4">
            Word Error Rate
          </p>
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={build("wer", "WER")} {...CHART_PROPS}>
              <CartesianGrid
                strokeDasharray="3 3"
                opacity={0.12}
                horizontal={false}
                vertical={true}
              />
              <XAxis
                type="number"
                unit="%"
                domain={[0, "auto"]}
                axisLine={false}
                tickLine={false}
                tick={AXIS_STYLE}
              />
              <YAxis
                type="category"
                dataKey="name"
                axisLine={false}
                tickLine={false}
                tick={AXIS_STYLE}
                width={40}
              />
              <Tooltip
                formatter={tooltip}
                contentStyle={tooltipStyle}
                cursor={{ fill: "rgba(0,0,0,0.025)" }}
              />
              <Legend
                wrapperStyle={{ paddingTop: "20px", fontSize: "12px", fontFamily: "inherit" }}
                onMouseEnter={(o) => setHovered(chartKeyFromLegend(o.dataKey))}
                onMouseLeave={() => setHovered(null)}
              />
              {bars}
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* CER */}
        <div>
          <p className="text-xs font-semibold font-sans text-muted-foreground uppercase tracking-widest mb-4">
            Character Error Rate
          </p>
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={build("cer", "CER")} {...CHART_PROPS}>
              <CartesianGrid
                strokeDasharray="3 3"
                opacity={0.12}
                horizontal={false}
                vertical={true}
              />
              <XAxis
                type="number"
                unit="%"
                domain={[0, "auto"]}
                axisLine={false}
                tickLine={false}
                tick={AXIS_STYLE}
              />
              <YAxis
                type="category"
                dataKey="name"
                axisLine={false}
                tickLine={false}
                tick={AXIS_STYLE}
                width={40}
              />
              <Tooltip
                formatter={tooltip}
                contentStyle={tooltipStyle}
                cursor={{ fill: "rgba(0,0,0,0.025)" }}
              />
              <Legend
                wrapperStyle={{ paddingTop: "20px", fontSize: "12px", fontFamily: "inherit" }}
                onMouseEnter={(o) => setHovered(chartKeyFromLegend(o.dataKey))}
                onMouseLeave={() => setHovered(null)}
              />
              {bars}
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
