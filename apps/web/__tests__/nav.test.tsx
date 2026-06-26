import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import Nav from "@/components/nav";

vi.mock("next/navigation", () => ({
  usePathname: vi.fn(() => "/"),
}));

describe("Nav", () => {
  it("renders the wordmark", () => {
    render(<Nav />);
    expect(screen.getByText("BosesPH")).toBeInTheDocument();
  });

  it("renders Dashboard and Demo links", () => {
    const { container } = render(<Nav />);
    const links = Array.from(container.querySelectorAll("a"));
    const dashLink = links.find((a) => a.textContent?.trim() === "Dashboard");
    const demoLink = links.find((a) => a.textContent?.trim() === "Demo");
    expect(dashLink).toBeTruthy();
    expect(dashLink?.getAttribute("href")).toBe("/");
    expect(demoLink).toBeTruthy();
    expect(demoLink?.getAttribute("href")).toBe("/demo");
  });

  it("underlines the active link", () => {
    const { container } = render(<Nav />);
    const links = Array.from(container.querySelectorAll("a"));
    const dashLink = links.find((a) => a.textContent?.trim() === "Dashboard");
    expect(dashLink?.className).toContain("underline");
  });
});
