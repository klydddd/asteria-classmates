"use client";

import { Button } from "@/components/ui/button";

type StepStatus = "pending" | "active" | "done" | "error";

interface DemoStepperProps {
  step: "uploading" | "transcribing" | "done" | "error";
  error?: string;
  onRetry: () => void;
}

const STEPS = [
  { key: "uploading", label: "Upload" },
  { key: "transcribing", label: "Transcribe" },
  { key: "done", label: "Done" },
] as const;

function stepStatus(
  stepKey: string,
  current: DemoStepperProps["step"]
): StepStatus {
  const order = ["uploading", "transcribing", "done"];
  const ci = order.indexOf(current === "error" ? "transcribing" : current);
  const si = order.indexOf(stepKey);
  if (current === "error" && stepKey === "transcribing") return "error";
  if (si < ci) return "done";
  if (si === ci) return "active";
  return "pending";
}

function StepIcon({ status, index }: { status: StepStatus; index: number }) {
  if (status === "done") {
    return (
      <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
        <path d="M3 8l3.5 3.5L13 4.5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    );
  }
  if (status === "error") {
    return (
      <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
        <path d="M7 4v4M7 10h.01" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
      </svg>
    );
  }
  if (status === "active") {
    return (
      <span className="relative flex h-3 w-3">
        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-accent opacity-60" />
        <span className="relative inline-flex rounded-full h-3 w-3 bg-accent" />
      </span>
    );
  }
  return <span className="text-xs font-semibold font-sans">{index + 1}</span>;
}

export default function DemoStepper({ step, error, onRetry }: DemoStepperProps) {
  return (
    <div className="space-y-5">
      <div className="flex items-center justify-center">
        {STEPS.map(({ key, label }, i) => {
          const status = stepStatus(key, step);
          return (
            <div key={key} className="flex items-center">
              {/* Step node */}
              <div className="flex flex-col items-center gap-1.5">
                <div
                  data-testid={`step-${key}-${status}`}
                  className={`flex items-center justify-center w-9 h-9 rounded-full transition-all duration-300 ${
                    status === "done"
                      ? "bg-accent text-accent-foreground"
                      : status === "active"
                      ? "bg-surface border-2 border-accent text-accent"
                      : status === "error"
                      ? "bg-destructive/10 border-2 border-destructive text-destructive"
                      : "bg-muted border border-border text-muted-foreground"
                  }`}
                >
                  <StepIcon status={status} index={i} />
                </div>
                <span
                  className={`text-xs font-sans transition-colors ${
                    status === "active"
                      ? "text-foreground font-medium"
                      : status === "done"
                      ? "text-muted-foreground"
                      : status === "error"
                      ? "text-destructive font-medium"
                      : "text-muted-foreground/50"
                  }`}
                >
                  {label}
                </span>
              </div>

              {/* Connector */}
              {i < STEPS.length - 1 && (
                <div
                  className={`w-16 h-0.5 mb-5 mx-2 transition-colors duration-500 ${
                    stepStatus(STEPS[i + 1].key, step) !== "pending"
                      ? "bg-accent"
                      : "bg-border"
                  }`}
                />
              )}
            </div>
          );
        })}
      </div>

      {/* Error panel */}
      {step === "error" && error && (
        <div className="rounded-xl border border-destructive/30 bg-destructive/5 px-5 py-4 flex items-center justify-between gap-4">
          <p className="text-sm text-destructive font-sans">{error}</p>
          <Button variant="outline" size="sm" onClick={onRetry} className="shrink-0 font-sans">
            Try again
          </Button>
        </div>
      )}
    </div>
  );
}
