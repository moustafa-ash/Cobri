import type { components } from "./generated";

export type Locale = "en" | "ar";
export type Localized = Record<Locale, string>;
export type AttemptPurpose = components["schemas"]["AttemptPurpose"];
type ApiLessonSummary = components["schemas"]["LessonSummary"];
type ApiLessonDetail = components["schemas"]["LessonDetail"];
type ApiPackageSummary = components["schemas"]["PackageSummary"];
type ApiSubmissionView = components["schemas"]["SubmissionView"];
type ApiNextStepView = components["schemas"]["NextStepView"];

export type EvidenceSource = Omit<components["schemas"]["EvidenceSource"], "explanation"> & {
  explanation: Localized;
};
export type RubricCriterion = Omit<components["schemas"]["RubricCriterion"], "description"> & {
  description: Localized;
};
export type LessonSummary = Omit<ApiLessonSummary, "title" | "prompt"> & {
  title: Localized;
  prompt: Localized;
};
export type PackageSummary = Omit<ApiPackageSummary, "lessons"> & {
  lessons: LessonSummary[];
};
export type LessonDetail = Omit<ApiLessonDetail, "title" | "prompt" | "evidence" | "rubric"> & {
  title: Localized;
  prompt: Localized;
  evidence: EvidenceSource[];
  rubric: RubricCriterion[];
};
export type SessionView = components["schemas"]["SessionView"];
export type EvaluationView = components["schemas"]["EvaluationView"] & {
  evidence_references: string[];
  misconception_id: string | null;
};
export type SubmissionView = Omit<
  ApiSubmissionView,
  "reasoning" | "parent_submission_id" | "evaluation"
> & {
  reasoning: string | null;
  parent_submission_id: string | null;
  evaluation: EvaluationView | null;
};
export type NextStepView = Omit<ApiNextStepView, "message" | "remediation" | "next_item"> & {
  message: Localized;
  remediation: Localized | null;
  next_item: { item_id: string; purpose: AttemptPurpose; prompt: Localized } | null;
};

export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    message: string,
    readonly correlationId: string | null,
  ) {
    super(message);
  }
}

export class CobriApi {
  constructor(
    private readonly baseUrl: string,
    private readonly getToken: () => Promise<string>,
  ) {}

  private async request<T>(path: string, init?: RequestInit): Promise<T> {
    const token = await this.getToken();
    const response = await fetch(`${this.baseUrl}${path}`, {
      ...init,
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
        "X-Correlation-ID": crypto.randomUUID(),
        ...init?.headers,
      },
    });
    if (!response.ok) {
      const body = (await response.json().catch(() => null)) as
        | { detail?: { code?: string; message?: string } }
        | null;
      throw new ApiError(
        response.status,
        body?.detail?.code ?? "request_failed",
        body?.detail?.message ?? "The request could not be completed.",
        response.headers.get("X-Correlation-ID"),
      );
    }
    return (await response.json()) as T;
  }

  packages() {
    return this.request<PackageSummary[]>("/api/v1/content/packages");
  }

  lesson(packageId: string, version: string, itemId: string) {
    return this.request<LessonDetail>(
      `/api/v1/content/packages/${encodeURIComponent(packageId)}/${encodeURIComponent(version)}/lessons/${encodeURIComponent(itemId)}`,
    );
  }

  createSession(packageId: string, version: string, ui: Locale, instruction: Locale) {
    return this.request<SessionView>("/api/v1/sessions", {
      method: "POST",
      body: JSON.stringify({
        content_package_id: packageId,
        content_version: version,
        ui_locale: ui,
        instructional_language: instruction,
      }),
    });
  }

  submit(
    sessionId: string,
    body: {
      item_id: string;
      answer: string;
      reasoning: string;
      purpose: AttemptPurpose;
      parent_submission_id: string | null;
    },
    idempotencyKey: string,
  ) {
    return this.request<SubmissionView>(`/api/v1/sessions/${sessionId}/submissions`, {
      method: "POST",
      headers: { "Idempotency-Key": idempotencyKey },
      body: JSON.stringify(body),
    });
  }

  submission(submissionId: string) {
    return this.request<SubmissionView>(`/api/v1/submissions/${submissionId}`);
  }

  next(submissionId: string) {
    return this.request<NextStepView>(`/api/v1/submissions/${submissionId}/next`);
  }
}
