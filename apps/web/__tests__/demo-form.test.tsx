import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import DemoForm from "@/components/demo-form";
import type { DemoOptions } from "@/lib/api";

const options: DemoOptions = {
  languages: [
    { id: "pam", label: "Kapampangan", description: "Central Luzon" },
    { id: "tl", label: "Tagalog", description: "National language" },
  ],
  models: [
    { id: "baseline", label: "Whisper Small", model_path: "openai/whisper-small", available: true, unavailable_reason: null },
    { id: "finetuned", label: "BosesPH v1", model_path: "outputs/model/v1", available: false, unavailable_reason: "not trained yet" },
  ],
  default_language_id: "pam",
  default_model_id: "baseline",
};

describe("DemoForm", () => {
  it("renders all form fields", () => {
    render(<DemoForm options={options} onSubmit={vi.fn()} />);
    expect(screen.getByTestId("audio-input")).toBeInTheDocument();
    expect(screen.getByTestId("language-select")).toBeInTheDocument();
    expect(screen.getByTestId("model-select")).toBeInTheDocument();
    expect(screen.getByTestId("reference-input")).toBeInTheDocument();
  });

  it("disables submit button until file is selected", () => {
    render(<DemoForm options={options} onSubmit={vi.fn()} />);
    const btn = screen.getByRole("button", { name: /transcribe/i });
    expect(btn).toBeDisabled();
  });

  it("enables submit and calls onSubmit with FormData when file is selected", async () => {
    const onSubmit = vi.fn();
    render(<DemoForm options={options} onSubmit={onSubmit} />);
    const file = new File(["audio"], "test.wav", { type: "audio/wav" });
    const input = screen.getByTestId("audio-input");
    await userEvent.upload(input, file);
    const btn = screen.getByRole("button", { name: /transcribe/i });
    expect(btn).not.toBeDisabled();
    await userEvent.click(btn);
    expect(onSubmit).toHaveBeenCalledTimes(1);
    const [form, filename] = onSubmit.mock.calls[0];
    expect(form).toBeInstanceOf(FormData);
    expect(form.get("audio")).toBe(file);
    expect(form.get("language_id")).toBe("pam");
    expect(form.get("model_id")).toBe("baseline");
    expect(filename).toBe("test.wav");
  });

  it("includes reference when provided", async () => {
    const onSubmit = vi.fn();
    render(<DemoForm options={options} onSubmit={onSubmit} />);
    const file = new File(["audio"], "test.wav", { type: "audio/wav" });
    await userEvent.upload(screen.getByTestId("audio-input"), file);
    await userEvent.type(screen.getByTestId("reference-input"), "Masanting ya ing aldo");
    await userEvent.click(screen.getByRole("button", { name: /transcribe/i }));
    const [form] = onSubmit.mock.calls[0];
    expect(form.get("reference")).toBe("Masanting ya ing aldo");
  });
});
