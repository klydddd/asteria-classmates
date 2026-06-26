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
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

interface ComparisonChartProps {
  baselineMetrics: { wer: number; cer: number } | null | undefined;
  previousFinetunedMetrics?: { wer: number; cer: number } | null | undefined;
  finetunedMetrics: { wer: number; cer: number } | null | undefined;
  datasetStats?: Record<string, number> | null;
}

type ChartKey = "Baseline" | "15 Speakers" | "30 Speakers" | "Predicted";
type MetricTooltipFormatter = NonNullable<TooltipProps["formatter"]>;

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

export default function ComparisonChart({
  baselineMetrics,
  previousFinetunedMetrics,
  finetunedMetrics,
  datasetStats,
}: ComparisonChartProps) {
  const [hoveredBar, setHoveredBar] = useState<ChartKey | null>(null);

  if (!baselineMetrics && !previousFinetunedMetrics && !finetunedMetrics) {
    return null;
  }

  // Power law scaling prediction: Error(D_target) = Error(D_current) * (D_current / D_target)^alpha
  // Assuming a target dataset of 100,000 clips and an empirical scaling exponent of 0.3
  const targetSize = 1000000;
  const currentSize = datasetStats?.total_clips ?? 4000;
  const alpha = 0.3;
  const scalingFactor = Math.pow(currentSize / targetSize, alpha);

  const werData = [
    {
      name: "WER",
      Baseline: baselineMetrics ? Number((baselineMetrics.wer * 100).toFixed(1)) : 0,
      "15 Speakers": previousFinetunedMetrics ? Number((previousFinetunedMetrics.wer * 100).toFixed(1)) : null,
      "30 Speakers": finetunedMetrics ? Number((finetunedMetrics.wer * 100).toFixed(1)) : 0,
      "Predicted": finetunedMetrics ? Number((finetunedMetrics.wer * scalingFactor * 100).toFixed(1)) : null,
    }
  ];

  const cerData = [
    {
      name: "CER",
      Baseline: baselineMetrics ? Number((baselineMetrics.cer * 100).toFixed(1)) : 0,
      "15 Speakers": previousFinetunedMetrics ? Number((previousFinetunedMetrics.cer * 100).toFixed(1)) : null,
      "30 Speakers": finetunedMetrics ? Number((finetunedMetrics.cer * 100).toFixed(1)) : 0,
      "Predicted": finetunedMetrics ? Number((finetunedMetrics.cer * scalingFactor * 100).toFixed(1)) : null,
    }
  ];

  const getOpacity = (dataKey: ChartKey) => {
    if (!hoveredBar) return 1;
    return hoveredBar === dataKey ? 1 : 0.3;
  };

  const formatTooltip: MetricTooltipFormatter = (value, name) => [`${value}%`, name];

  const sharedBarProps = {
    radius: [0, 4, 4, 0] as [number, number, number, number],
    barSize: 30,
  };

  const renderBars = () => (
    <>
      <Bar
        name="Baseline"
        dataKey="Baseline"
        fill="#17231b"
        {...sharedBarProps}
        fillOpacity={getOpacity("Baseline")}
        onMouseEnter={() => setHoveredBar("Baseline")}
        onMouseLeave={() => setHoveredBar(null)}
      />
      <Bar
        name="15 Speakers"
        dataKey="15 Speakers"
        fill="#7d5a3c"
        {...sharedBarProps}
        fillOpacity={getOpacity("15 Speakers")}
        onMouseEnter={() => setHoveredBar("15 Speakers")}
        onMouseLeave={() => setHoveredBar(null)}
      />
      <Bar
        name="30 Speakers"
        dataKey="30 Speakers"
        fill="#b33a2b"
        {...sharedBarProps}
        fillOpacity={getOpacity("30 Speakers")}
        onMouseEnter={() => setHoveredBar("30 Speakers")}
        onMouseLeave={() => setHoveredBar(null)}
      />
      <Bar
        name="Predicted"
        dataKey="Predicted"
        fill="#b33a2b"
        fillOpacity={hoveredBar && hoveredBar !== "Predicted" ? 0 : 0.15}
        stroke="#b33a2b"
        strokeDasharray="4 4"
        strokeWidth={2}
        {...sharedBarProps}
        strokeOpacity={getOpacity("Predicted")}
        onMouseEnter={() => setHoveredBar("Predicted")}
        onMouseLeave={() => setHoveredBar(null)}
      />
    </>
  );

  const sharedChartProps = {
    layout: "vertical" as const,
    margin: { top: 20, right: 30, left: 10, bottom: 5 },
    barCategoryGap: "25%",
  };

  return (
    <Card className="col-span-1 lg:col-span-4 h-[600px]">
      <CardHeader>
        <CardTitle>Model Performance</CardTitle>
        <CardDescription>
          Error Rates (%) — Lower is better. Target is mathematically predicted based on scaling power laws (projected to {targetSize.toLocaleString()} clips).
        </CardDescription>
      </CardHeader>
      <CardContent className="h-[500px]">
        <div className="flex flex-col gap-8 h-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={werData} {...sharedChartProps}>
              <CartesianGrid strokeDasharray="3 3" opacity={0.2} horizontal={true} vertical={false} />
              <XAxis type="number" unit="%" domain={[0, 'auto']} axisLine={false} tickLine={false} />
              <YAxis type="category" dataKey="name" axisLine={false} tickLine={false} />
              <Tooltip
                formatter={formatTooltip}
                contentStyle={{ backgroundColor: "#fffdf7", borderRadius: "8px", border: "1px solid #d7d0c0" }}
                cursor={{ fill: "transparent" }}
              />
              <Legend
                wrapperStyle={{ paddingTop: "20px" }}
                onMouseEnter={(o) => setHoveredBar(chartKeyFromLegend(o.dataKey))}
                onMouseLeave={() => setHoveredBar(null)}
              />
              {renderBars()}
            </BarChart>
          </ResponsiveContainer>

          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={cerData} {...sharedChartProps}>
              <CartesianGrid strokeDasharray="3 3" opacity={0.2} horizontal={true} vertical={false} />
              <XAxis type="number" unit="%" domain={[0, 'auto']} axisLine={false} tickLine={false} />
              <YAxis type="category" dataKey="name" axisLine={false} tickLine={false} />
              <Tooltip
                formatter={formatTooltip}
                contentStyle={{ backgroundColor: "#fffdf7", borderRadius: "8px", border: "1px solid #d7d0c0" }}
                cursor={{ fill: "transparent" }}
              />
              <Legend
                wrapperStyle={{ paddingTop: "20px" }}
                onMouseEnter={(o) => setHoveredBar(chartKeyFromLegend(o.dataKey))}
                onMouseLeave={() => setHoveredBar(null)}
              />
              {renderBars()}
            </BarChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}
