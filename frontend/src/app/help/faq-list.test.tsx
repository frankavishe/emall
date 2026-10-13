import { afterEach, describe, expect, it } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { FaqList, type FaqSection } from "./faq-list";

afterEach(cleanup);

const SECTIONS: FaqSection[] = [
  {
    id: "payments",
    title: "Payments",
    items: [{ q: "Which payment methods do you accept?", a: "M-Pesa and Airtel Money." }],
  },
  {
    id: "delivery",
    title: "Delivery",
    items: [{ q: "Who delivers my order?", a: "MangiMall riders." }],
  },
];

const search = () => screen.getByLabelText("Search help articles");

describe("FaqList", () => {
  it("shows every section with topic links when there is no search", () => {
    render(<FaqList sections={SECTIONS} />);

    expect(screen.getByRole("link", { name: "Payments" }).getAttribute("href")).toBe("#payments");
    expect(screen.getByText("Which payment methods do you accept?")).toBeTruthy();
    expect(screen.getByText("Who delivers my order?")).toBeTruthy();
  });

  it("filters questions by question or answer text, ignoring case", () => {
    render(<FaqList sections={SECTIONS} />);

    fireEvent.change(search(), { target: { value: "RIDERS" } });

    expect(screen.getByText("Who delivers my order?")).toBeTruthy();
    expect(screen.queryByText("Which payment methods do you accept?")).toBeNull();
    expect(screen.queryByRole("heading", { name: "Payments" })).toBeNull();
  });

  it("shows an empty state when nothing matches", () => {
    render(<FaqList sections={SECTIONS} />);

    fireEvent.change(search(), { target: { value: "bitcoin" } });

    expect(screen.getByText(/No answers match/)).toBeTruthy();
  });
});
