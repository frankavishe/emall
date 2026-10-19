import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { TrackLinkForm, extractTrackToken } from "./track-link-form";

const push = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ push }) }));

afterEach(() => {
  cleanup();
  push.mockReset();
});

const TOKEN = "Xq3_vB9-kLm2Np7Rs4Tu8Wy1Za6Cd0Ef5Gh2Jk9Lm4";

describe("extractTrackToken", () => {
  it("reads the token from a full tracking link", () => {
    expect(extractTrackToken(`https://mangimall.com/orders/track/${TOKEN}`)).toBe(TOKEN);
  });

  it("ignores a trailing path, query string or fragment", () => {
    expect(extractTrackToken(`https://mangimall.com/orders/track/${TOKEN}/pay`)).toBe(TOKEN);
    expect(extractTrackToken(`/orders/track/${TOKEN}?utm=email#top`)).toBe(TOKEN);
  });

  it("accepts a bare token, trimming whitespace", () => {
    expect(extractTrackToken(`  ${TOKEN}\n`)).toBe(TOKEN);
  });

  it("rejects anything else", () => {
    expect(extractTrackToken("")).toBeNull();
    expect(extractTrackToken("12345")).toBeNull();
    expect(extractTrackToken("https://mangimall.com/orders/42")).toBeNull();
    expect(extractTrackToken("https://mangimall.com/orders/track/")).toBeNull();
  });
});

describe("TrackLinkForm", () => {
  const input = () => screen.getByLabelText("Tracking link or code");
  const submit = () => fireEvent.click(screen.getByRole("button", { name: "Track order" }));

  it("opens the order for a valid link", () => {
    render(<TrackLinkForm />);

    fireEvent.change(input(), { target: { value: `https://mangimall.com/orders/track/${TOKEN}` } });
    submit();

    expect(push).toHaveBeenCalledWith(`/orders/track/${TOKEN}`);
  });

  it("shows an error for an invalid link", () => {
    render(<TrackLinkForm />);

    fireEvent.change(input(), { target: { value: "order 42" } });
    submit();

    expect(push).not.toHaveBeenCalled();
    expect(screen.getByText(/doesn't look like a tracking link/)).toBeTruthy();
  });
});
