import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import ComparisonChart from "@/components/comparison-chart";

const metrics = {
  baselineMetrics: { wer: 0.342, cer: 0.145 },
  previousFinetunedMetrics: { wer: 0.256, cer: 0.112 },
  finetunedMetrics: { wer: 0.198, cer: 0.091 },
  datasetStats: { total_clips: 50 },
};

describe("ComparisonChart", () => {
  it("stacks WER and CER chart sections vertically", () => {
    render(<ComparisonChart {...metrics} />);

    const werSection = screen.getByText("Word Error Rate").parentElement;
    const chartStack = werSection?.parentElement;

    expect(screen.getByText("Character Error Rate")).toBeInTheDocument();
    expect(chartStack).toHaveClass("flex", "flex-col");
    expect(chartStack).not.toHaveClass("md:grid-cols-2");
  });
});
