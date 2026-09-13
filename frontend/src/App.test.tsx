import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { LearnerApp } from "./App";
import type { CobriApi, PackageSummary } from "./api/client";

const packages: PackageSummary[] = [
  {
    content_package_id: "python-functions",
    content_version: "2.0.0",
    topic: "Python functions",
    lessons: [
      {
        item_id: "function-return-value",
        title: { en: "Return a value", ar: "إرجاع قيمة" },
        prompt: {
          en: "Write double(n), which returns twice n.",
          ar: "اكتب الدالة double(n) بحيث تعيد ضعف n.",
        },
      },
    ],
  },
];

function mockApi(): CobriApi {
  return {
    discoverTopic: vi.fn().mockImplementation(async (query: string) =>
      query.includes("loops")
        ? { status: "unsupported", options: [], content_package_id: null, content_version: null }
        : {
            status: "supported",
            options: packages[0].lessons,
            content_package_id: "python-functions",
            content_version: "2.0.0",
          },
    ),
  } as unknown as CobriApi;
}

describe("topic discovery chat", () => {
  beforeEach(() => localStorage.clear());

  it("offers reviewed lesson choices after a learner names a supported topic", async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <LearnerApp api={mockApi()} onSignOut={vi.fn()} userName="Learner" />
      </MemoryRouter>,
    );
    expect(screen.getByText(/What topic would you like/)).toBeInTheDocument();
    await user.type(screen.getByLabelText("Topic to check"), "Python functions");
    await user.click(screen.getByRole("button", { name: "Send topic" }));
    expect(await screen.findByText("Return a value")).toBeInTheDocument();
    expect(screen.getByLabelText("Interface")).toBeInTheDocument();
    expect(screen.getByLabelText("Lesson language")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Return a value/ })).toHaveAttribute(
      "href",
      "/lesson/python-functions/2.0.0/function-return-value",
    );
  });

  it("explains when a topic has no reviewed material", async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <LearnerApp api={mockApi()} onSignOut={vi.fn()} />
      </MemoryRouter>,
    );
    await user.type(screen.getByLabelText("Topic to check"), "Python loops");
    await user.click(screen.getByRole("button", { name: "Send topic" }));
    expect(await screen.findByText("I don’t have reviewed material for that topic yet.")).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /Start lesson/ })).not.toBeInTheDocument();
  });

  it("renders the Arabic interface right to left", async () => {
    localStorage.setItem("cobri.ui", "ar");
    localStorage.setItem("cobri.instruction", "ar");
    const { container } = render(
      <MemoryRouter>
        <LearnerApp api={mockApi()} onSignOut={vi.fn()} />
      </MemoryRouter>,
    );
    expect(await screen.findByRole("heading", { name: "ما الذي تريد أن تفهمه؟" })).toBeInTheDocument();
    expect(container.firstElementChild).toHaveAttribute("dir", "rtl");
  });
});
