import { render, screen } from "@testing-library/react";
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
    packages: vi.fn().mockResolvedValue(packages),
  } as unknown as CobriApi;
}

describe("learner library", () => {
  beforeEach(() => localStorage.clear());

  it("shows reviewed lessons and keeps both language controls", async () => {
    render(
      <MemoryRouter>
        <LearnerApp api={mockApi()} onSignOut={vi.fn()} userName="Learner" />
      </MemoryRouter>,
    );
    expect(await screen.findByRole("heading", { name: "Return a value" })).toBeInTheDocument();
    expect(screen.getByLabelText("Interface")).toBeInTheDocument();
    expect(screen.getByLabelText("Lesson language")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Start lesson/ })).toHaveAttribute(
      "href",
      "/lesson/python-functions/2.0.0/function-return-value",
    );
  });

  it("renders the Arabic interface right to left", async () => {
    localStorage.setItem("cobri.ui", "ar");
    localStorage.setItem("cobri.instruction", "ar");
    const { container } = render(
      <MemoryRouter>
        <LearnerApp api={mockApi()} onSignOut={vi.fn()} />
      </MemoryRouter>,
    );
    expect(await screen.findByRole("heading", { name: "إرجاع قيمة" })).toBeInTheDocument();
    expect(container.firstElementChild).toHaveAttribute("dir", "rtl");
  });
});
