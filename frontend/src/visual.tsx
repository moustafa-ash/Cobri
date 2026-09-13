import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";

import { LearnerApp } from "./App";
import type { CobriApi, LessonDetail, PackageSummary, SubmissionView } from "./api/client";
import "./styles.css";

const lesson: LessonDetail = {
  item_id: "function-return-value",
  title: { en: "Return a value", ar: "إرجاع قيمة" },
  prompt: {
    en: "Write double(n), which returns twice n. Do not print the result.",
    ar: "اكتب الدالة double(n) بحيث تعيد ضعف n. لا تطبع النتيجة.",
  },
  evidence: [
    {
      evidence_id: "python-functions:2.0.0:return-values",
      source_title: "Python Tutorial: Defining Functions",
      source_url: "https://docs.python.org/3/tutorial/controlflow.html#defining-functions",
      explanation: {
        en: "A return statement sends a value back to the caller. Printing only displays output.",
        ar: "تعيد جملة return قيمة إلى موضع الاستدعاء، بينما تعرض print ناتجًا فقط.",
      },
    },
  ],
  rubric: [
    { criterion_id: "defines", description: { en: "Defines double with one parameter.", ar: "يعرّف double بمعامل واحد." } },
    { criterion_id: "returns", description: { en: "Returns n multiplied by 2.", ar: "يعيد حاصل ضرب n في 2." } },
  ],
};

const packages: PackageSummary[] = [{
  content_package_id: "python-functions",
  content_version: "2.0.0",
  topic: "Python functions",
  lessons: [lesson],
}];

let poll = 0;
const api = {
  packages: async () => packages,
  discoverTopic: async () => ({ status: "supported", options: packages[0].lessons, content_package_id: "python-functions", content_version: "2.0.0" }),
  lesson: async () => lesson,
  createSession: async () => ({ session_id: "session", content_package_id: "python-functions", content_version: "2.0.0", ui_locale: "en", instructional_language: "en", created_at: new Date().toISOString() }),
  submit: async (_session: string, body: Record<string, unknown>) => ({
    ...body,
    submission_id: "submission",
    session_id: "session",
    content_package_id: "python-functions",
    content_version: "2.0.0",
    created_at: new Date().toISOString(),
    job: { job_id: "job", status: "pending" },
    evaluation: null,
  }) as SubmissionView,
  submission: async () => {
    poll += 1;
    return {
      submission_id: "submission",
      session_id: "session",
      content_package_id: "python-functions",
      content_version: "2.0.0",
      item_id: "function-return-value",
      answer: "def double(n):\n    print(n * 2)",
      reasoning: "Printing shows the value.",
      purpose: "assessment",
      parent_submission_id: null,
      created_at: new Date().toISOString(),
      job: { job_id: "job", status: poll ? "succeeded" : "pending" },
      evaluation: {
        outcome_verdict: "incorrect",
        reasoning_verdict: "incorrect",
        diagnostic_status: "supported",
        evidence_references: ["python-functions:2.0.0:return-values"],
        misconception_id: "print-instead-of-return",
      },
    } as SubmissionView;
  },
  next: async () => ({
    action: "remediation",
    message: { en: "Review this explanation, then try a focused exercise.", ar: "راجع هذا الشرح، ثم جرّب تدريبًا مركّزًا." },
    remediation: { en: "Use return when later code must receive the result.", ar: "استخدم return عندما يحتاج الكود اللاحق إلى استلام النتيجة." },
    next_item: { item_id: "practice-return-square", purpose: "practice", prompt: { en: "Write square(n), which returns n multiplied by itself.", ar: "اكتب square(n) بحيث تعيد حاصل ضرب n في نفسه." } },
  }),
} as unknown as CobriApi;

createRoot(document.getElementById("root")!).render(
  <BrowserRouter><LearnerApp api={api} onSignOut={() => undefined} userName="Visual test learner" /></BrowserRouter>,
);
