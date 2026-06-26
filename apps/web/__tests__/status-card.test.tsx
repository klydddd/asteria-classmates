import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import StatusCard from "@/components/status-card";

describe("StatusCard", () => {
  it("renders label and value", () => {
    render(<StatusCard label="Dataset Clips" value="42" loading={false} />);
    expect(screen.getByText("Dataset Clips")).toBeInTheDocument();
    expect(screen.getByText("42")).toBeInTheDocument();
  });

  it("renders em dash when value is null", () => {
    render(<StatusCard label="Baseline WER" value={null} loading={false} />);
    expect(screen.getByText("—")).toBeInTheDocument();
  });

  it("renders a skeleton when loading", () => {
    render(<StatusCard label="Speakers" value={null} loading={true} />);
    expect(screen.getByTestId("status-card-skeleton")).toBeInTheDocument();
  });
});
