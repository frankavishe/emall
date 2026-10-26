import { afterEach, describe, expect, it } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import Link from "next/link";
import { ErrorState } from "./error-state";

afterEach(cleanup);

describe("ErrorState", () => {
  it("renders the code, title, description and actions", () => {
    render(
      <ErrorState
        code="404"
        title="Page not found"
        description="Nothing here."
        actions={<Link href="/">Go home</Link>}
      />,
    );
    expect(screen.getByText("404")).toBeTruthy();
    expect(screen.getByRole("heading", { level: 1, name: "Page not found" })).toBeTruthy();
    expect(screen.getByText("Nothing here.")).toBeTruthy();
    expect(screen.getByRole("link", { name: "Go home" }).getAttribute("href")).toBe("/");
  });

  it("omits the code when none is given", () => {
    render(<ErrorState title="Couldn't load this order" />);
    expect(screen.queryByText(/^\d{3}$/)).toBeNull();
  });
});
