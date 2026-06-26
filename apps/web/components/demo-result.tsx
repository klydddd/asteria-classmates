"use client";

import { Button } from "@/components/ui/button";
import type { DemoTranscriptionResult } from "@/lib/api";

interface DemoResultProps {
  result: DemoTranscriptionResult;
  filename: string;
  audioUrl?: string;
  onReset: () => void;
}

export default function DemoResult({
  result,
  filename,
  audioUrl,
  onReset,
}: DemoResultProps) {
  return (
    <div className="space-y-6">
      {/* File + model info */}
      <div className="flex items-start justify-between gap-4 pb-5 border-b border-border">
        <div>
          <h2 className="text-lg font-bold text-foreground font-serif leading-snug">{filename}</h2>
          <p className="text-xs text-muted-foreground font-sans mt-0.5">{result.model_label}</p>
        </div>
        {(result.wer != null || result.cer != null) && (
          <div className="flex items-center gap-2 shrink-0">
            {result.wer != null && (
              <div className="rounded-lg bg-muted px-3 py-1.5 text-center">
                <p className="text-xs font-semibold font-sans text-muted-foreground uppercase tracking-widest leading-none mb-0.5">WER</p>
                <p className="text-lg font-bold font-serif tabular-nums text-foreground leading-none">
                  {(result.wer * 100).toFixed(1)}%
                </p>
              </div>
            )}
            {result.cer != null && (
              <div className="rounded-lg bg-muted px-3 py-1.5 text-center">
                <p className="text-xs font-semibold font-sans text-muted-foreground uppercase tracking-widest leading-none mb-0.5">CER</p>
                <p className="text-lg font-bold font-serif tabular-nums text-foreground leading-none">
                  {(result.cer * 100).toFixed(1)}%
                </p>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Audio player */}
      {audioUrl && (
        <div className="space-y-1.5">
          <p className="text-xs font-semibold font-sans text-muted-foreground uppercase tracking-widest">
            Audio
          </p>
          <audio
            data-testid="audio-player"
            controls
            src={audioUrl}
            className="w-full h-10 rounded-lg"
          />
        </div>
      )}

      {/* Transcript */}
      <div className="space-y-1.5">
        <p className="text-xs font-semibold font-sans text-muted-foreground uppercase tracking-widest">
          Transcript
        </p>
        <div className="rounded-xl border border-border bg-surface p-5">
          <p className="text-foreground font-serif leading-relaxed whitespace-pre-wrap text-[15px]">
            {result.prediction}
          </p>
        </div>
      </div>

      {/* Reset */}
      <Button
        variant="outline"
        onClick={onReset}
        className="w-full font-sans"
      >
        Try another file
      </Button>
    </div>
  );
}
