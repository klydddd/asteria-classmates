import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import DemoResult from "@/components/demo-result";
import type { DemoTranscriptionResult } from "@/lib/api";

const result: DemoTranscriptionResult = {
  prediction: "Masanting ya ing aldo ngeni",
  model_id: "finetuned",
  model_label: "BosesPH v1",
  language_id: "pam",
  wer: 0.123,
  cer: 0.045,
};

describe("DemoResult", () => {
  it("renders filename and model label", () => {
    render(<DemoResult result={result} filename="test.wav" onReset={vi.fn()} />);
    expect(screen.getByText("test.wav")).toBeInTheDocument();
    expect(screen.getByText("BosesPH v1")).toBeInTheDocument();
  });

  it("renders transcript", () => {
    render(<DemoResult result={result} filename="test.wav" onReset={vi.fn()} />);
    expect(screen.getByText("Masanting ya ing aldo ngeni")).toBeInTheDocument();
  });

  it("renders WER and CER badges", () => {
    render(<DemoResult result={result} filename="test.wav" onReset={vi.fn()} />);
    expect(screen.getByText("WER: 12.3%")).toBeInTheDocument();
    expect(screen.getByText("CER: 4.5%")).toBeInTheDocument();
  });

  it("hides badges when wer/cer are null", () => {
    const noMetrics = { ...result, wer: null, cer: null };
    render(<DemoResult result={noMetrics} filename="test.wav" onReset={vi.fn()} />);
    expect(screen.queryByText(/WER:/)).not.toBeInTheDocument();
    expect(screen.queryByText(/CER:/)).not.toBeInTheDocument();
  });

  it("renders audio player when audioUrl is provided", () => {
    render(
      <DemoResult
        result={result}
        filename="test.wav"
        audioUrl="blob:http://localhost/abc"
        onReset={vi.fn()}
      />
    );
    expect(screen.getByTestId("audio-player")).toBeInTheDocument();
  });

  it("calls onReset when button is clicked", async () => {
    const onReset = vi.fn();
    render(<DemoResult result={result} filename="test.wav" onReset={onReset} />);
    await userEvent.click(screen.getByRole("button", { name: /try another/i }));
    expect(onReset).toHaveBeenCalledTimes(1);
  });
});
