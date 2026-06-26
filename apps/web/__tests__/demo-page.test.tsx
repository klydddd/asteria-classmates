import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import DemoPage from "@/components/demo-page";
import type { DemoOptions, Job } from "@/lib/api";

vi.mock("@/lib/api", () => ({
  getDemoOptions: vi.fn(),
  submitDemo: vi.fn(),
  getJob: vi.fn(),
}));

import { getDemoOptions, submitDemo, getJob } from "@/lib/api";

const mockOptions: DemoOptions = {
  languages: [
    { id: "pam", label: "Kapampangan", description: "Central Luzon" },
  ],
  models: [
    { id: "baseline", label: "Whisper Small", model_path: "openai/whisper-small", available: true, unavailable_reason: null },
  ],
  default_language_id: "pam",
  default_model_id: "baseline",
};

afterEach(() => {
  vi.restoreAllMocks();
});

describe("DemoPage", () => {
  it("shows loading skeleton while options load", () => {
    vi.mocked(getDemoOptions).mockReturnValue(new Promise(() => {}));
    render(<DemoPage />);
    // Should show skeleton placeholders
    expect(screen.queryByTestId("audio-input")).not.toBeInTheDocument();
  });

  it("shows error when options fail to load", async () => {
    vi.mocked(getDemoOptions).mockRejectedValue(new Error("fail"));
    render(<DemoPage />);
    expect(await screen.findByText(/could not load demo options/i)).toBeInTheDocument();
  });

  it("renders form after options load", async () => {
    vi.mocked(getDemoOptions).mockResolvedValue(mockOptions);
    render(<DemoPage />);
    expect(await screen.findByTestId("audio-input")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /transcribe/i })).toBeInTheDocument();
  });

  it("transitions through full flow: form → polling → result", async () => {
    vi.mocked(getDemoOptions).mockResolvedValue(mockOptions);
    const runningJob: Job = {
      id: "j1", type: "transcribe", status: "running",
      progress: null, result: null, error: null,
      created_at: "", updated_at: "",
    };
    const doneJob: Job = {
      id: "j1", type: "transcribe", status: "succeeded",
      progress: null,
      result: {
        prediction: "Masanting ya",
        model_id: "baseline",
        model_label: "Whisper Small",
        language_id: "pam",
        wer: null,
        cer: null,
      },
      error: null,
      created_at: "", updated_at: "",
    };
    vi.mocked(submitDemo).mockResolvedValue(runningJob);
    vi.mocked(getJob)
      .mockResolvedValueOnce(runningJob)
      .mockResolvedValue(doneJob);

    render(<DemoPage />);
    await screen.findByTestId("audio-input");

    // Upload file and submit
    const file = new File(["audio"], "clip.wav", { type: "audio/wav" });
    await userEvent.upload(screen.getByTestId("audio-input"), file);
    await userEvent.click(screen.getByRole("button", { name: /transcribe/i }));

    // Should eventually show the result
    await waitFor(() => {
      expect(screen.getByText("Masanting ya")).toBeInTheDocument();
    }, { timeout: 10_000 });

    expect(screen.getByRole("button", { name: /try another/i })).toBeInTheDocument();
  });
});
