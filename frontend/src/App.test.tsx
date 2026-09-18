import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { LearnerApp } from "./App";
import type { CobriApi, PackageSummary } from "./api/client";

vi.mock("./CodeEditor", () => ({
  default: ({ value, onChange, ariaLabel }: { value: string; onChange: (value: string) => void; ariaLabel: string }) => (
    <textarea aria-label={ariaLabel} value={value} onChange={(event) => onChange(event.target.value)} />
  ),
}));

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
    lesson: vi.fn().mockResolvedValue({
      ...packages[0].lessons[0],
      evidence: [],
      rubric: [],
    }),
    createSession: vi.fn().mockResolvedValue({ session_id: "session-1" }),
    submit: vi.fn().mockResolvedValue({
      submission_id: "submission-1",
      job: { job_id: "job-1", status: "succeeded" },
      evaluation: null,
    }),
    submission: vi.fn().mockResolvedValue({
      submission_id: "submission-1",
      job: { job_id: "job-1", status: "succeeded" },
      evaluation: {
        outcome_verdict: "correct",
        reasoning_verdict: "correct",
        diagnostic_status: "supported",
        evidence_references: [],
        misconception_id: null,
      },
    }),
    next: vi.fn().mockResolvedValue({
      action: "complete",
      message: { en: "You completed this learning loop.", ar: "أكملت مسار التعلّم." },
      remediation: null,
      next_item: null,
    }),
    progress: vi.fn().mockResolvedValue([]),
    history: vi.fn().mockResolvedValue([]),
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

  it("keeps the conversation visible when the coding workspace opens", async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <LearnerApp api={mockApi()} onSignOut={vi.fn()} userName="Learner" />
      </MemoryRouter>,
    );
    await user.type(screen.getByLabelText("Topic to check"), "Python functions");
    await user.click(screen.getByRole("button", { name: "Send topic" }));
    await user.click(await screen.findByRole("link", { name: /Return a value/ }));

    expect(await screen.findByLabelText("Coding workspace")).toBeInTheDocument();
    expect(await screen.findByRole("textbox", { name: "Your Python code" }, { timeout: 5000 })).toBeInTheDocument();
    expect(screen.getByLabelText("Conversation with Cobri")).toBeInTheDocument();
    expect(screen.getByText(/What topic would you like/)).toBeInTheDocument();
  });

  it("returns to chat and presents evaluation feedback after submission", async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter initialEntries={["/lesson/python-functions/2.0.0/function-return-value"]}>
        <LearnerApp api={mockApi()} onSignOut={vi.fn()} />
      </MemoryRouter>,
    );

    await user.type(await screen.findByRole("textbox", { name: "Your Python code" }, { timeout: 5000 }), "def double(n):\n    return n * 2");
    await user.type(screen.getByLabelText("Explain your reasoning"), "It returns twice the input.");
    await user.click(screen.getByRole("button", { name: "Check my answer" }));

    expect(await screen.findByRole("heading", { name: "Your feedback" })).toBeInTheDocument();
    expect(screen.queryByLabelText("Coding workspace")).not.toBeInTheDocument();
    expect(screen.getByText("I sent my code and reasoning for evaluation.")).toBeInTheDocument();
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

  it("shows persisted activity details without exposing submission content", async () => {
    const api = mockApi();
    vi.mocked(api.progress).mockResolvedValue([{
      content_package_id: "python-functions",
      content_version: "2.0.0",
      item_id: "function-return-value",
      status: "mastered",
      version: 2,
      updated_at: "2026-01-01T12:00:00Z",
    }]);
    render(<MemoryRouter><LearnerApp api={api} onSignOut={vi.fn()} /></MemoryRouter>);
    expect(await screen.findByText("Saved activity")).toBeInTheDocument();
    expect(screen.getByText(/function-return-value/)).toBeInTheDocument();
    expect(screen.queryByText(/answer|reasoning/i)).not.toBeInTheDocument();
  });
});
