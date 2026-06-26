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
    <form onSubmit={handleSubmit} className="space-y-6">
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
        className={`relative flex flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed p-8 cursor-pointer transition-colors ${
          dragOver
            ? "border-accent bg-accent/5"
            : "border-border hover:border-accent/40"
        }`}
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          width="32"
          height="32"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
          strokeLinecap="round"
          strokeLinejoin="round"
          className="text-muted-foreground"
        >
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
          <polyline points="17 8 12 3 7 8" />
          <line x1="12" y1="3" x2="12" y2="15" />
        </svg>
        <p className="text-sm text-muted-foreground">
          {file ? file.name : "Drop an audio file here, or click to browse"}
        </p>
        <input
          ref={inputRef}
          data-testid="audio-input"
          type="file"
          accept=".wav,.mp3,.flac,.ogg"
          className="sr-only"
          onChange={(e) => handleFile(e.target.files?.[0] ?? null)}
        />
      </div>

      {/* Language */}
      <div className="space-y-2">
        <label className="text-sm font-medium text-foreground">Language</label>
        <Select value={languageId} onValueChange={(v) => v && setLanguageId(v)}>
          <SelectTrigger data-testid="language-select">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {options.languages.map((lang) => (
              <SelectItem key={lang.id} value={lang.id}>
                {lang.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Model */}
      <div className="space-y-2">
        <label className="text-sm font-medium text-foreground">Model</label>
        <Select value={modelId} onValueChange={(v) => v && setModelId(v)}>
          <SelectTrigger data-testid="model-select">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {options.models.map((m) => (
              <SelectItem key={m.id} value={m.id} disabled={!m.available}>
                {m.label}
                {!m.available && m.unavailable_reason
                  ? ` (${m.unavailable_reason})`
                  : ""}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Reference transcript */}
      <div className="space-y-2">
        <label className="text-sm font-medium text-foreground">
          Reference transcript{" "}
          <span className="text-muted-foreground">(optional — enables WER/CER)</span>
        </label>
        <Textarea
          data-testid="reference-input"
          placeholder="Paste the expected transcript here..."
          value={reference}
          onChange={(e) => setReference(e.target.value)}
          rows={3}
        />
      </div>

      {/* Submit */}
      <Button
        type="submit"
        disabled={!file}
        className="w-full bg-accent text-accent-foreground hover:bg-accent/90"
      >
        Transcribe
      </Button>
    </form>
  );
}
