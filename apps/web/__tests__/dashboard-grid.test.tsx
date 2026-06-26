import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, waitFor, act } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import DashboardGrid from "@/components/dashboard-grid";
import type { ProjectStatus } from "@/lib/api";

vi.mock("@/lib/api", () => ({
  getProjectStatus: vi.fn(),
}));

import { getProjectStatus } from "@/lib/api";

const mockStatus: ProjectStatus = {
  dataset_available: true,
  dataset_stats: {
    total_clips: 50,
    approved_clips: 40,
    num_speakers: 5,
    total_speakers: 30,
    total_duration_minutes: 12.3,
  },
  baseline_metrics: { wer: 0.342, cer: 0.145 },
  previous_finetuned_metrics: { wer: 0.256, cer: 0.112 },
  finetuned_metrics: { wer: 0.198, cer: 0.091 },
  model_available: true,
  model_dir: "model/v1",
  model_version: "v1",
};

afterEach(() => {
  vi.restoreAllMocks();
});

describe("DashboardGrid", () => {
  it("shows skeleton cards while loading", () => {
    vi.mocked(getProjectStatus).mockReturnValue(new Promise(() => {}));
    const { container } = render(<DashboardGrid />);
    expect(container.querySelectorAll('[data-slot="skeleton"]')).toHaveLength(4);
  });

  it("renders speaker and metric cards after fetch resolves", async () => {
    vi.mocked(getProjectStatus).mockResolvedValue(mockStatus);
    render(<DashboardGrid />);
    expect(screen.getByText("Training Speakers")).toBeInTheDocument();
    expect(await screen.findByText("30")).toBeInTheDocument();
    expect(screen.getByText("34.2%")).toBeInTheDocument();
    expect(screen.getByText("19.8%")).toBeInTheDocument();
    expect(screen.getByText("9.1%")).toBeInTheDocument();
  });

  it("shows em dash for null fields", async () => {
    vi.mocked(getProjectStatus).mockResolvedValue({
      ...mockStatus,
      finetuned_metrics: null,
      model_version: null,
    });
    render(<DashboardGrid />);
    await waitFor(() => {
      expect(screen.getAllByText("—")).toHaveLength(2);
    });
  });

  it("shows error banner when fetch fails", async () => {
    vi.mocked(getProjectStatus).mockRejectedValue(new Error("Network error"));
    render(<DashboardGrid />);
    expect(await screen.findByText(/could not reach the API/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /retry/i })).toBeInTheDocument();
  });

  it("re-fetches on retry click", async () => {
    vi.mocked(getProjectStatus)
      .mockRejectedValueOnce(new Error("fail"))
      .mockResolvedValueOnce(mockStatus);
    render(<DashboardGrid />);
    expect(await screen.findByRole("button", { name: /retry/i })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /retry/i }));
    expect(await screen.findByText("30")).toBeInTheDocument();
  });

  it("re-fetches after 10 seconds", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    vi.mocked(getProjectStatus).mockResolvedValue(mockStatus);
    render(<DashboardGrid />);
    await waitFor(() => {
      expect(screen.getByText("30")).toBeInTheDocument();
    });
    const callsBefore = vi.mocked(getProjectStatus).mock.calls.length;
    await act(async () => {
      vi.advanceTimersByTime(10_000);
    });
    await waitFor(() => {
      expect(vi.mocked(getProjectStatus).mock.calls.length).toBeGreaterThan(callsBefore);
    });
    vi.useRealTimers();
  });
});
