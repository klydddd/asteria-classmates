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
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

interface ComparisonChartProps {
  baselineMetrics: { wer: number; cer: number } | null | undefined;
  finetunedMetrics: { wer: number; cer: number } | null | undefined;
  datasetStats?: Record<string, number> | null;
}

export default function ComparisonChart({
  baselineMetrics,
  finetunedMetrics,
  datasetStats,
}: ComparisonChartProps) {
  const [hoveredBar, setHoveredBar] = useState<string | null>(null);

  if (!baselineMetrics && !finetunedMetrics) {
    return null;
  }

  // Power law scaling prediction: Error(D_target) = Error(D_current) * (D_current / D_target)^alpha
  // Assuming a target dataset of 100,000 clips and an empirical scaling exponent of 0.3
  const targetSize = 100000;
  const currentSize = datasetStats?.total_clips ?? 4000;
  const alpha = 0.3;
  const scalingFactor = Math.pow(currentSize / targetSize, alpha);

  const werData = [
    {
      name: "WER",
      Baseline: baselineMetrics ? Number((baselineMetrics.wer * 100).toFixed(1)) : 0,
      "Fine-tuned": finetunedMetrics ? Number((finetunedMetrics.wer * 100).toFixed(1)) : 0,
      "Predicted": finetunedMetrics ? Number((finetunedMetrics.wer * scalingFactor * 100).toFixed(1)) : null,
    }
  ];

  const cerData = [
    {
      name: "CER",
      Baseline: baselineMetrics ? Number((baselineMetrics.cer * 100).toFixed(1)) : 0,
      "Fine-tuned": finetunedMetrics ? Number((finetunedMetrics.cer * 100).toFixed(1)) : 0,
      "Predicted": finetunedMetrics ? Number((finetunedMetrics.cer * scalingFactor * 100).toFixed(1)) : null,
    }
  ];

  const getOpacity = (dataKey: string) => {
    if (!hoveredBar) return 1;
    return hoveredBar === dataKey ? 1 : 0.3;
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
            <BarChart data={werData} layout="vertical" margin={{ top: 20, right: 30, left: 10, bottom: 5 }} barCategoryGap="25%">
              <CartesianGrid strokeDasharray="3 3" opacity={0.2} horizontal={true} vertical={false} />
              <XAxis type="number" unit="%" domain={[0, 'auto']} axisLine={false} tickLine={false} />
              <YAxis type="category" dataKey="name" axisLine={false} tickLine={false} />
              <Tooltip
                formatter={(value: any, name: any) => [`${value}%`, name]}
                contentStyle={{ backgroundColor: "#fffdf7", borderRadius: "8px", border: "1px solid #d7d0c0" }}
                cursor={{ fill: "transparent" }}
              />
              <Legend wrapperStyle={{ paddingTop: "20px" }} onMouseEnter={(o) => setHoveredBar(o.dataKey)} onMouseLeave={() => setHoveredBar(null)} />
              <Bar
                name="Baseline"
                dataKey="Baseline"
                fill="#17231b"
                radius={[0, 4, 4, 0]}
                barSize={40}
                fillOpacity={getOpacity("Baseline")}
                onMouseEnter={() => setHoveredBar("Baseline")}
                onMouseLeave={() => setHoveredBar(null)}
              />
              <Bar
                name="Fine-tuned"
                dataKey="Fine-tuned"
                fill="#b33a2b"
                radius={[0, 4, 4, 0]}
                barSize={40}
                fillOpacity={getOpacity("Fine-tuned")}
                onMouseEnter={() => setHoveredBar("Fine-tuned")}
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
                radius={[0, 4, 4, 0]}
                barSize={40}
                strokeOpacity={getOpacity("Predicted")}
                onMouseEnter={() => setHoveredBar("Predicted")}
                onMouseLeave={() => setHoveredBar(null)}
              />
            </BarChart>
          </ResponsiveContainer>

          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={cerData} layout="vertical" margin={{ top: 20, right: 30, left: 10, bottom: 5 }} barCategoryGap="25%">
              <CartesianGrid strokeDasharray="3 3" opacity={0.2} horizontal={true} vertical={false} />
              <XAxis type="number" unit="%" domain={[0, 'auto']} axisLine={false} tickLine={false} />
              <YAxis type="category" dataKey="name" axisLine={false} tickLine={false} />
              <Tooltip
                formatter={(value: any, name: any) => [`${value}%`, name]}
                contentStyle={{ backgroundColor: "#fffdf7", borderRadius: "8px", border: "1px solid #d7d0c0" }}
                cursor={{ fill: "transparent" }}
              />
              <Legend wrapperStyle={{ paddingTop: "20px" }} onMouseEnter={(o) => setHoveredBar(o.dataKey)} onMouseLeave={() => setHoveredBar(null)} />
              <Bar
                name="Baseline"
                dataKey="Baseline"
                fill="#17231b"
                radius={[0, 4, 4, 0]}
                barSize={40}
                fillOpacity={getOpacity("Baseline")}
                onMouseEnter={() => setHoveredBar("Baseline")}
                onMouseLeave={() => setHoveredBar(null)}
              />
              <Bar
                name="Fine-tuned"
                dataKey="Fine-tuned"
                fill="#b33a2b"
                radius={[0, 4, 4, 0]}
                barSize={40}
                fillOpacity={getOpacity("Fine-tuned")}
                onMouseEnter={() => setHoveredBar("Fine-tuned")}
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
                radius={[0, 4, 4, 0]}
                barSize={40}
                strokeOpacity={getOpacity("Predicted")}
                onMouseEnter={() => setHoveredBar("Predicted")}
                onMouseLeave={() => setHoveredBar(null)}
              />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}
