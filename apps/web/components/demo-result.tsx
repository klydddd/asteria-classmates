"use client";

import { Badge } from "@/components/ui/badge";
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
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-bold text-foreground font-serif">
            {filename}
          </h2>
          <p className="text-sm text-muted-foreground">{result.model_label}</p>
        </div>
      </div>

      {/* Audio player */}
      {audioUrl && (
        <audio
          data-testid="audio-player"
          controls
          src={audioUrl}
          className="w-full"
        />
      )}

      {/* Transcript */}
      <div className="rounded-lg border border-border bg-surface p-4">
        <p className="text-sm text-muted-foreground mb-1 font-medium">
          Transcript
        </p>
        <p className="text-foreground font-serif leading-relaxed whitespace-pre-wrap">
          {result.prediction}
        </p>
      </div>

      {/* Metrics */}
      {(result.wer != null || result.cer != null) && (
        <div className="flex gap-2">
          {result.wer != null && (
            <Badge variant="secondary">
              WER: {(result.wer * 100).toFixed(1)}%
            </Badge>
          )}
          {result.cer != null && (
            <Badge variant="secondary">
              CER: {(result.cer * 100).toFixed(1)}%
            </Badge>
          )}
        </div>
      )}

      {/* Reset */}
      <Button variant="outline" onClick={onReset} className="w-full">
        Try another file
      </Button>
    </div>
  );
}
