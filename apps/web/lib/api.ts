export interface ProjectStatus {
  dataset_available: boolean;
  dataset_stats: Record<string, number> | null;
  baseline_metrics: { wer: number; cer: number } | null;
  finetuned_metrics: { wer: number; cer: number } | null;
  model_available: boolean;
  model_dir: string | null;
  model_version: string | null;
}

export interface DemoLanguageOption {
  id: string;
  label: string;
  description: string;
}

export interface DemoModelOption {
  id: string;
  label: string;
  model_path: string;
  available: boolean;
  unavailable_reason: string | null;
}

export interface DemoOptions {
  languages: DemoLanguageOption[];
  models: DemoModelOption[];
  default_language_id: string;
  default_model_id: string;
}

export interface DemoTranscriptionResult {
  prediction: string;
  model_id: string;
  model_label: string;
  language_id: string;
  wer: number | null;
  cer: number | null;
}

export interface Job {
  id: string;
  type: string;
  status: "queued" | "running" | "succeeded" | "failed";
  progress: string | null;
  result: DemoTranscriptionResult | null;
  error: string | null;
  created_at: string;
  updated_at: string;
}

const base = (): string =>
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${base()}${path}`, init);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json() as Promise<T>;
}

export function getProjectStatus(): Promise<ProjectStatus> {
  return request<ProjectStatus>("/project-status");
}

export function getDemoOptions(): Promise<DemoOptions> {
  return request<DemoOptions>("/demo/options");
}

export function submitDemo(form: FormData): Promise<Job> {
  return request<Job>("/demo/transcribe", { method: "POST", body: form });
}

export function getJob(id: string): Promise<Job> {
  return request<Job>(`/jobs/${id}`);
}
