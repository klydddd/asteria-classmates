"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import {
  getDemoOptions,
  submitDemo,
  getJob,
  type DemoOptions,
  type DemoTranscriptionResult,
} from "@/lib/api";
import DemoForm from "@/components/demo-form";
import DemoStepper from "@/components/demo-stepper";
import DemoResult from "@/components/demo-result";
import { Skeleton } from "@/components/ui/skeleton";

type Phase =
  | { kind: "form" }
  | { kind: "polling"; jobId: string; filename: string }
  | { kind: "result"; result: DemoTranscriptionResult; filename: string }
  | { kind: "error"; message: string; filename: string };

const POLL_MS = 2_000;

export default function DemoPage() {
  const [options, setOptions] = useState<DemoOptions | null>(null);
  const [optionsError, setOptionsError] = useState<string | null>(null);
  const [phase, setPhase] = useState<Phase>({ kind: "form" });
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    getDemoOptions()
      .then(setOptions)
      .catch(() => setOptionsError("Could not load demo options. Is the API running?"));
  }, []);

  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, []);

  const startPolling = useCallback((jobId: string, filename: string) => {
    if (pollRef.current) clearInterval(pollRef.current);
    pollRef.current = setInterval(async () => {
      try {
        const job = await getJob(jobId);
        if (job.status === "succeeded" && job.result) {
          clearInterval(pollRef.current!);
          pollRef.current = null;
          setPhase({ kind: "result", result: job.result, filename });
        } else if (job.status === "failed") {
          clearInterval(pollRef.current!);
          pollRef.current = null;
          setPhase({
            kind: "error",
            message: job.error ?? "Transcription failed",
            filename,
          });
        }
      } catch {
        clearInterval(pollRef.current!);
        pollRef.current = null;
        setPhase({
          kind: "error",
          message: "Lost connection to the API while polling",
          filename,
        });
      }
    }, POLL_MS);
  }, []);

  async function handleSubmit(form: FormData, filename: string) {
    const audioFile = form.get("audio") as File | null;
    if (audioFile) {
      if (audioUrl) URL.revokeObjectURL(audioUrl);
      setAudioUrl(URL.createObjectURL(audioFile));
    }

    setPhase({ kind: "polling", jobId: "", filename });
    try {
      const job = await submitDemo(form);
      setPhase({ kind: "polling", jobId: job.id, filename });
      startPolling(job.id, filename);
    } catch {
      setPhase({
        kind: "error",
        message: "Failed to submit transcription request",
        filename,
      });
    }
  }

  function handleReset() {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
    if (audioUrl) URL.revokeObjectURL(audioUrl);
    setAudioUrl(null);
    setPhase({ kind: "form" });
  }

  const stepperStep =
    phase.kind === "polling"
      ? phase.jobId
        ? "transcribing"
        : "uploading"
      : phase.kind === "result"
      ? "done"
      : phase.kind === "error"
      ? "error"
      : null;

  return (
    <section className="max-w-2xl mx-auto">
      {/* Page hero */}
      <div className="pb-6 mb-8 border-b border-border">
        <h1 className="text-3xl font-bold text-foreground font-serif mb-2">Live Demo</h1>
        <p className="text-sm text-muted-foreground font-sans">
          Upload a Kapampangan audio clip and get an instant transcription from the BosesPH model.
        </p>
      </div>

      {/* Stepper — visible once out of form state */}
      {stepperStep && (
        <div className="mb-8">
          <DemoStepper
            step={stepperStep}
            error={
              phase.kind === "error"
                ? (phase as Extract<Phase, { kind: "error" }>).message
                : undefined
            }
            onRetry={handleReset}
          />
        </div>
      )}

      {/* Options loading */}
      {!options && !optionsError && (
        <div className="space-y-4">
          <Skeleton className="h-32 w-full rounded-xl" />
          <div className="grid grid-cols-2 gap-4">
            <Skeleton className="h-10 w-full rounded-lg" />
            <Skeleton className="h-10 w-full rounded-lg" />
          </div>
          <Skeleton className="h-20 w-full rounded-lg" />
          <Skeleton className="h-10 w-full rounded-lg" />
        </div>
      )}

      {/* Options error */}
      {optionsError && (
        <div className="rounded-xl border border-destructive/30 bg-destructive/5 px-5 py-4">
          <p className="text-sm text-destructive font-sans">{optionsError}</p>
        </div>
      )}

      {/* Form */}
      {options && phase.kind === "form" && (
        <DemoForm options={options} onSubmit={handleSubmit} />
      )}

      {/* Result */}
      {phase.kind === "result" && (
        <div className="mt-2">
          <DemoResult
            result={phase.result}
            filename={phase.filename}
            audioUrl={audioUrl ?? undefined}
            onReset={handleReset}
          />
        </div>
      )}
    </section>
  );
}
