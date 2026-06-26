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

export default function DemoStepper({ step, error, onRetry }: DemoStepperProps) {
  return (
    <div className="space-y-4">
      {/* Step indicators */}
      <div className="flex items-center justify-center gap-2">
        {STEPS.map(({ key, label }, i) => {
          const status = stepStatus(key, step);
          return (
            <div key={key} className="flex items-center gap-2">
              <div className="flex flex-col items-center gap-1">
                <div
                  data-testid={`step-${key}-${status}`}
                  className={`flex items-center justify-center w-8 h-8 rounded-full text-xs font-bold transition-colors ${
                    status === "done"
                      ? "bg-accent text-accent-foreground"
                      : status === "active"
                      ? "bg-accent/20 text-accent ring-2 ring-accent"
                      : status === "error"
                      ? "bg-destructive text-white"
                      : "bg-muted text-muted-foreground"
                  }`}
                >
                  {status === "done" ? "✓" : status === "error" ? "!" : i + 1}
                </div>
                <span className="text-xs text-muted-foreground">{label}</span>
              </div>
              {i < STEPS.length - 1 && (
                <div
                  className={`w-12 h-0.5 mb-5 ${
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

      {/* Error message */}
      {step === "error" && error && (
        <div className="rounded-lg border border-destructive/40 bg-destructive/10 px-4 py-3 flex items-center justify-between">
          <p className="text-sm text-destructive">{error}</p>
          <Button variant="outline" size="sm" onClick={onRetry}>
            Try again
          </Button>
        </div>
      )}
    </div>
  );
}
