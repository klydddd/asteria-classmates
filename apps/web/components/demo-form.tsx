"use client";

import { useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import type { DemoOptions } from "@/lib/api";

interface DemoFormProps {
  options: DemoOptions;
  onSubmit: (form: FormData, filename: string) => void;
}

export default function DemoForm({ options, onSubmit }: DemoFormProps) {
  const [file, setFile] = useState<File | null>(null);
  const [languageId, setLanguageId] = useState(options.default_language_id);
  const [modelId, setModelId] = useState(options.default_model_id);
  const [reference, setReference] = useState("");
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  function handleFile(f: File | null) {
    setFile(f);
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    setDragOver(false);
    const f = e.dataTransfer.files[0] ?? null;
    if (f) handleFile(f);
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!file) return;
    const form = new FormData();
    form.append("audio", file);
    form.append("language_id", languageId);
    form.append("model_id", modelId);
    if (reference.trim()) form.append("reference", reference.trim());
    onSubmit(form, file.name);
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      {/* Drop zone */}
      <div
        role="region"
        aria-label="Audio upload"
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
        className={`relative flex flex-col items-center justify-center gap-3 rounded-xl border-2 border-dashed p-10 cursor-pointer transition-all duration-200 ${
          dragOver
            ? "border-accent bg-accent/5 scale-[1.01]"
            : file
            ? "border-accent/50 bg-accent/3"
            : "border-border hover:border-accent/40 hover:bg-muted/30"
        }`}
      >
        {/* Waveform icon */}
        <svg
          width="40"
          height="28"
          viewBox="0 0 40 28"
          fill="none"
          className={`transition-colors ${file ? "text-accent" : "text-muted-foreground/50"}`}
        >
          <rect x="0" y="10" width="3" height="8" rx="1.5" fill="currentColor" />
          <rect x="5" y="6" width="3" height="16" rx="1.5" fill="currentColor" />
          <rect x="10" y="2" width="3" height="24" rx="1.5" fill="currentColor" />
          <rect x="15" y="7" width="3" height="14" rx="1.5" fill="currentColor" />
          <rect x="20" y="4" width="3" height="20" rx="1.5" fill="currentColor" />
          <rect x="25" y="8" width="3" height="12" rx="1.5" fill="currentColor" />
          <rect x="30" y="5" width="3" height="18" rx="1.5" fill="currentColor" />
          <rect x="35" y="11" width="3" height="6" rx="1.5" fill="currentColor" />
        </svg>

        {file ? (
          <div className="text-center">
            <p className="text-sm font-medium text-foreground font-sans">{file.name}</p>
            <p className="text-xs text-muted-foreground font-sans mt-0.5">
              {(file.size / 1024).toFixed(0)} KB · Click to change
            </p>
          </div>
        ) : (
          <div className="text-center">
            <p className="text-sm text-muted-foreground font-sans">
              Drop an audio file here, or{" "}
              <span className="text-foreground underline underline-offset-2">click to browse</span>
            </p>
            <p className="text-xs text-muted-foreground/60 font-sans mt-1">
              .wav · .mp3 · .flac · .ogg
            </p>
          </div>
        )}

        <input
          ref={inputRef}
          data-testid="audio-input"
          type="file"
          accept=".wav,.mp3,.flac,.ogg"
          className="sr-only"
          onChange={(e) => handleFile(e.target.files?.[0] ?? null)}
        />
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {/* Language */}
        <div className="space-y-1.5">
          <label className="text-xs font-semibold font-sans text-muted-foreground uppercase tracking-widest">
            Language
          </label>
          <Select value={languageId} onValueChange={(v) => v && setLanguageId(v)}>
            <SelectTrigger data-testid="language-select" className="font-sans">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {options.languages.map((lang) => (
                <SelectItem key={lang.id} value={lang.id} className="font-sans">
                  {lang.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Model */}
        <div className="space-y-1.5">
          <label className="text-xs font-semibold font-sans text-muted-foreground uppercase tracking-widest">
            Model
          </label>
          <Select value={modelId} onValueChange={(v) => v && setModelId(v)}>
            <SelectTrigger data-testid="model-select" className="font-sans">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {options.models.map((m) => (
                <SelectItem key={m.id} value={m.id} disabled={!m.available} className="font-sans">
                  {m.label}
                  {!m.available && m.unavailable_reason ? ` (${m.unavailable_reason})` : ""}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Reference transcript */}
      <div className="space-y-1.5">
        <label className="text-xs font-semibold font-sans text-muted-foreground uppercase tracking-widest">
          Reference transcript{" "}
          <span className="normal-case tracking-normal font-normal text-muted-foreground/60">
            — optional, enables WER/CER
          </span>
        </label>
        <Textarea
          data-testid="reference-input"
          placeholder="Paste the expected transcript here..."
          value={reference}
          onChange={(e) => setReference(e.target.value)}
          rows={3}
          className="font-serif resize-none"
        />
      </div>

      {/* Submit */}
      <Button
        type="submit"
        disabled={!file}
        className="w-full h-10 bg-accent text-accent-foreground hover:bg-accent/90 font-sans font-medium tracking-wide"
      >
        Transcribe
      </Button>
    </form>
  );
}
