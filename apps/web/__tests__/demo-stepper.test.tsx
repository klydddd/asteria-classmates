import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import DemoStepper from "@/components/demo-stepper";

describe("DemoStepper", () => {
  it("shows upload as active when step is uploading", () => {
    render(<DemoStepper step="uploading" onRetry={vi.fn()} />);
    expect(screen.getByTestId("step-uploading-active")).toBeInTheDocument();
    expect(screen.getByTestId("step-transcribing-pending")).toBeInTheDocument();
    expect(screen.getByTestId("step-done-pending")).toBeInTheDocument();
  });

  it("shows transcribing as active with upload done", () => {
    render(<DemoStepper step="transcribing" onRetry={vi.fn()} />);
    expect(screen.getByTestId("step-uploading-done")).toBeInTheDocument();
    expect(screen.getByTestId("step-transcribing-active")).toBeInTheDocument();
    expect(screen.getByTestId("step-done-pending")).toBeInTheDocument();
  });

  it("shows all steps done", () => {
    render(<DemoStepper step="done" onRetry={vi.fn()} />);
    expect(screen.getByTestId("step-uploading-done")).toBeInTheDocument();
    expect(screen.getByTestId("step-transcribing-done")).toBeInTheDocument();
    expect(screen.getByTestId("step-done-active")).toBeInTheDocument();
  });

  it("shows error state on transcribing step", () => {
    render(
      <DemoStepper step="error" error="Model crashed" onRetry={vi.fn()} />
    );
    expect(screen.getByTestId("step-transcribing-error")).toBeInTheDocument();
    expect(screen.getByText("Model crashed")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /try again/i })).toBeInTheDocument();
  });

  it("calls onRetry when try again is clicked", async () => {
    const onRetry = vi.fn();
    const { default: userEvent } = await import("@testing-library/user-event");
    render(<DemoStepper step="error" error="oops" onRetry={onRetry} />);
    await userEvent.click(screen.getByRole("button", { name: /try again/i }));
    expect(onRetry).toHaveBeenCalledTimes(1);
  });
});
