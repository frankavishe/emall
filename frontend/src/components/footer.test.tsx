import { afterEach, describe, expect, it } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { Footer } from "./footer";

afterEach(cleanup);

describe("Footer", () => {
  it("renders the footer landmark with its column headings", () => {
    render(<Footer />);
    expect(screen.getByRole("contentinfo")).toBeTruthy();
    for (const heading of ["About", "Customer Care", "Stay Connected"]) {
      expect(screen.getByRole("heading", { name: heading })).toBeTruthy();
    }
    expect(screen.getByText(/E-Mall Technologies Limited/)).toBeTruthy();
  });

  it("labels every social link", () => {
    render(<Footer />);
    for (const name of ["Instagram", "X (Twitter)", "Facebook", "LinkedIn", "WhatsApp"]) {
      expect(screen.getByRole("link", { name })).toBeTruthy();
    }
  });

  it("does not navigate when the newsletter form is submitted", () => {
    render(<Footer />);
    const input = screen.getByLabelText("Email address");
    const form = input.closest("form")!;
    const event = new Event("submit", { bubbles: true, cancelable: true });
    fireEvent(form, event);
    expect(event.defaultPrevented).toBe(true);
  });
});
