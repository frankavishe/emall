import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import ErrorPage from "./error";

afterEach(cleanup);
beforeEach(() => {
  vi.spyOn(console, "error").mockImplementation(() => {});
});

describe("error boundary page", () => {
  it("retries when Try again is clicked", () => {
    const retry = vi.fn();
    render(<ErrorPage error={new Error("boom")} retry={retry} />);
    fireEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(retry).toHaveBeenCalledOnce();
  });

  it("shows the digest as a reference id but never the raw message", () => {
    const error = Object.assign(new Error("secret detail"), { digest: "abc123" });
    render(<ErrorPage error={error} retry={() => {}} />);
    expect(screen.getByText("Reference: abc123")).toBeTruthy();
    expect(screen.queryByText(/secret detail/)).toBeNull();
  });
});
