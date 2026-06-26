import { describe, it, expect, vi, beforeEach } from "vitest";
import {
  getProjectStatus,
  getDemoOptions,
  submitDemo,
  getJob,
} from "@/lib/api";

const BASE = "http://localhost:8000";

beforeEach(() => {
  vi.stubGlobal("fetch", vi.fn());
  process.env.NEXT_PUBLIC_API_BASE_URL = BASE;
});

function mockFetch(data: unknown, status = 200) {
  vi.mocked(fetch).mockResolvedValueOnce(
    new Response(JSON.stringify(data), { status })
  );
}

describe("getProjectStatus", () => {
  it("fetches /project-status and returns the parsed body", async () => {
    const payload = { dataset_available: true, dataset_stats: { total_clips: 100 } };
    mockFetch(payload);
    const result = await getProjectStatus();
    expect(fetch).toHaveBeenCalledWith(`${BASE}/project-status`, undefined);
    expect(result).toEqual(payload);
  });

  it("throws on non-2xx response", async () => {
    mockFetch({ detail: "not found" }, 404);
    await expect(getProjectStatus()).rejects.toThrow("404");
  });
});

describe("getDemoOptions", () => {
  it("fetches /demo/options", async () => {
    const payload = { languages: [], models: [], default_language_id: "pam", default_model_id: "baseline" };
    mockFetch(payload);
    const result = await getDemoOptions();
    expect(fetch).toHaveBeenCalledWith(`${BASE}/demo/options`, undefined);
    expect(result).toEqual(payload);
  });
});

describe("submitDemo", () => {
  it("POSTs /demo/transcribe with the FormData body", async () => {
    const job = { id: "abc123", type: "demo-transcribe", status: "queued" };
    mockFetch(job);
    const form = new FormData();
    const result = await submitDemo(form);
    expect(fetch).toHaveBeenCalledWith(
      `${BASE}/demo/transcribe`,
      expect.objectContaining({ method: "POST", body: form })
    );
    expect(result).toEqual(job);
  });
});

describe("getJob", () => {
  it("fetches /jobs/{id}", async () => {
    const job = { id: "abc123", status: "succeeded", result: { prediction: "hello" } };
    mockFetch(job);
    const result = await getJob("abc123");
    expect(fetch).toHaveBeenCalledWith(`${BASE}/jobs/abc123`, undefined);
    expect(result).toEqual(job);
  });
});
