import { afterEach, describe, expect, it } from "vitest";
import { cleanup, render } from "@testing-library/react";
import { Avatar } from "./avatar";

afterEach(cleanup);

describe("Avatar", () => {
  it("shows the photo when there is one", () => {
    const { container } = render(<Avatar name="Asha Mwita" src="https://x.test/a.png" />);
    expect(container.querySelector("img")?.getAttribute("src")).toBe("https://x.test/a.png");
  });

  it("falls back to initials", () => {
    const { container } = render(<Avatar name="Asha Mwita" src={null} />);
    expect(container.querySelector("img")).toBeNull();
    expect(container.textContent).toBe("AM");
  });
});
