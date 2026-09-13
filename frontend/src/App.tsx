import { useAuth0 } from "@auth0/auth0-react";
import {
  ArrowLeft,
  ArrowRight,
  ChatCircleDots,
  CheckCircle,
  PaperPlaneTilt,
  SignOut,
  Sparkle,
  WarningCircle,
} from "@phosphor-icons/react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link, Route, Routes, useNavigate, useParams } from "react-router-dom";

import {
  ApiError,
  CobriApi,
  type AttemptPurpose,
  type LessonDetail,
  type Locale,
  type NextStepView,
  type TopicDiscoveryResponse,
  type SubmissionView,
} from "./api/client";
import { copy } from "./i18n";

interface LearnerAppProps {
  api: CobriApi;
  onSignOut: () => void;
  userName?: string;
}

function readLocale(key: string, fallback: Locale): Locale {
  return localStorage.getItem(key) === "ar" ? "ar" : fallback;
}

export function LearnerApp({ api, onSignOut, userName }: LearnerAppProps) {
  const [uiLocale, setUiLocale] = useState<Locale>(() => readLocale("cobri.ui", "en"));
  const [instructionLocale, setInstructionLocale] = useState<Locale>(() =>
    readLocale("cobri.instruction", "en"),
  );

  const changeUi = (locale: Locale) => {
    localStorage.setItem("cobri.ui", locale);
    setUiLocale(locale);
  };
  const changeInstruction = (locale: Locale) => {
    localStorage.setItem("cobri.instruction", locale);
    setInstructionLocale(locale);
  };

  return (
    <div dir={uiLocale === "ar" ? "rtl" : "ltr"} className="app-shell">
      <Header
        locale={uiLocale}
        instructionLocale={instructionLocale}
        onUiLocale={changeUi}
        onInstructionLocale={changeInstruction}
        onSignOut={onSignOut}
        userName={userName}
      />
      <main>
        <Routes>
          <Route
            path="/"
            element={<LessonLibrary api={api} locale={uiLocale} instructionLocale={instructionLocale} />}
          />
          <Route
            path="/lesson/:packageId/:version/:itemId"
            element={<LessonWorkspace api={api} locale={uiLocale} instructionLocale={instructionLocale} />}
          />
          <Route path="*" element={<NavigateHome locale={uiLocale} />} />
        </Routes>
      </main>
    </div>
  );
}

function Header({
  locale,
  instructionLocale,
  onUiLocale,
  onInstructionLocale,
  onSignOut,
  userName,
}: {
  locale: Locale;
  instructionLocale: Locale;
  onUiLocale: (value: Locale) => void;
  onInstructionLocale: (value: Locale) => void;
  onSignOut: () => void;
  userName?: string;
}) {
  const t = copy[locale];
  return (
    <header className="topbar">
      <Link className="brand" to="/" aria-label={t.brand}>
        <span className="brand-mark" aria-hidden="true">C</span>
        <span>{t.brand}</span>
      </Link>
      <div className="header-controls">
        <label className="compact-select">
          <span>{t.interfaceLanguage}</span>
          <select value={locale} onChange={(event) => onUiLocale(event.target.value as Locale)}>
            <option value="en">{t.english}</option>
            <option value="ar">{t.arabic}</option>
          </select>
        </label>
        <label className="compact-select lesson-language">
          <span>{t.instructionLanguage}</span>
          <select
            value={instructionLocale}
            onChange={(event) => onInstructionLocale(event.target.value as Locale)}
          >
            <option value="en">{t.english}</option>
            <option value="ar">{t.arabic}</option>
          </select>
        </label>
        <button className="icon-button" type="button" onClick={onSignOut} aria-label={t.signOut} title={userName ?? t.signOut}>
          <SignOut size={20} weight="bold" aria-hidden="true" />
        </button>
      </div>
    </header>
  );
}

function LessonLibrary({ api, locale, instructionLocale }: { api: CobriApi; locale: Locale; instructionLocale: Locale }) {
  const [query, setQuery] = useState("");
  const [submittedQuery, setSubmittedQuery] = useState<string | null>(null);
  const [discovery, setDiscovery] = useState<TopicDiscoveryResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const t = copy[locale];

  const discover = async () => {
    const topic = query.trim();
    if (!topic || busy) return;
    setSubmittedQuery(topic);
    setQuery("");
    setDiscovery(null);
    setError(null);
    setBusy(true);
    try {
      setDiscovery(await api.discoverTopic(topic));
    } catch (reason) {
      setError(errorMessage(reason, locale));
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="topic-chat page-width" aria-labelledby="topic-chat-title">
      <div className="chat-heading">
        <span className="section-icon"><ChatCircleDots size={25} weight="duotone" /></span>
        <div>
          <h1 id="topic-chat-title">{t.chatTitle}</h1>
          <p>{t.chatSubtitle}</p>
        </div>
      </div>

      <div className="conversation" aria-live="polite">
        <div className="message-row assistant-message">
          <span className="message-avatar" aria-hidden="true">C</span>
          <div className="message-bubble"><p>{t.chatGreeting}</p></div>
        </div>

        {submittedQuery && (
          <div className="message-row learner-message">
            <div className="message-bubble"><p>{submittedQuery}</p></div>
          </div>
        )}

        {busy && (
          <div className="message-row assistant-message">
            <span className="message-avatar" aria-hidden="true">C</span>
            <div className="message-bubble typing-message"><span /><span /><span /><span className="sr-only">{t.findingTopics}</span></div>
          </div>
        )}

        {discovery && (
          <div className="message-row assistant-message">
            <span className="message-avatar" aria-hidden="true">C</span>
            <div className="message-bubble discovery-message">
              {discovery.status === "supported" ? (
                <>
                  <p>{t.supportedTopic}</p>
                  <div className="topic-options">
                    {discovery.options.map((lesson) => (
                      <Link
                        className="topic-option"
                        key={lesson.item_id}
                        to={`/lesson/${discovery.content_package_id}/${discovery.content_version}/${lesson.item_id}`}
                      >
                        <span><strong>{lesson.title[instructionLocale]}</strong><small>{lesson.prompt[instructionLocale]}</small></span>
                        {locale === "ar" ? <ArrowLeft size={18} /> : <ArrowRight size={18} />}
                      </Link>
                    ))}
                  </div>
                </>
              ) : (
                <>
                  <p>{t.unsupportedTopic}</p>
                  <small className="availability-note">{t.availableNow}</small>
                </>
              )}
            </div>
          </div>
        )}

        {error && <ErrorNotice message={error} />}
      </div>

      <form className="topic-composer" onSubmit={(event) => { event.preventDefault(); void discover(); }}>
        <label className="sr-only" htmlFor="topic-query">{t.topicLabel}</label>
        <textarea
          id="topic-query"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey) {
              event.preventDefault();
              void discover();
            }
          }}
          placeholder={t.topicPlaceholder}
          rows={2}
          maxLength={300}
        />
        <button className="send-button" type="submit" disabled={busy || !query.trim()} aria-label={t.sendTopic}>
          <PaperPlaneTilt size={21} weight="fill" aria-hidden="true" />
        </button>
      </form>
      <p className="composer-hint">{t.composerHint}</p>
    </section>
  );
}

function LessonWorkspace({ api, locale, instructionLocale }: { api: CobriApi; locale: Locale; instructionLocale: Locale }) {
  const { packageId = "", version = "", itemId = "" } = useParams();
  const [lesson, setLesson] = useState<LessonDetail | null>(null);
  const [currentItem, setCurrentItem] = useState<{ item_id: string; prompt: Record<Locale, string>; purpose: AttemptPurpose } | null>(null);
  const [parentId, setParentId] = useState<string | null>(null);
  const [answer, setAnswer] = useState("");
  const [reasoning, setReasoning] = useState("");
  const [submission, setSubmission] = useState<SubmissionView | null>(null);
  const [nextStep, setNextStep] = useState<NextStepView | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const pollCount = useRef(0);
  const t = copy[locale];

  useEffect(() => {
    let active = true;
    api.lesson(packageId, version, itemId).then((result) => {
      if (!active) return;
      setLesson(result);
      setCurrentItem({ item_id: result.item_id, prompt: result.prompt, purpose: "assessment" });
    }).catch((reason: unknown) => active && setError(errorMessage(reason, locale)));
    return () => { active = false; };
  }, [api, packageId, version, itemId, locale]);

  const loadResult = useCallback(async (submissionId: string) => {
    const result = await api.submission(submissionId);
    setSubmission(result);
    if (result.job.status === "succeeded" || result.job.status === "failed") {
      setNextStep(await api.next(result.submission_id));
      localStorage.removeItem(`cobri.pending.${itemId}`);
      setBusy(false);
    }
    return result;
  }, [api, itemId]);

  useEffect(() => {
    const saved = localStorage.getItem(`cobri.pending.${itemId}`);
    if (!saved) return;
    const pending = JSON.parse(saved) as { sessionId: string; submissionId?: string };
    setSessionId(pending.sessionId);
    if (pending.submissionId) {
      setBusy(true);
      loadResult(pending.submissionId).catch((reason: unknown) => { setError(errorMessage(reason, locale)); setBusy(false); });
    }
  }, [itemId, loadResult, locale]);

  useEffect(() => {
    if (!submission || !["pending", "running"].includes(submission.job.status)) return;
    const delay = Math.min(5000, 750 * 2 ** Math.min(pollCount.current, 3));
    const timer = window.setTimeout(() => {
      pollCount.current += 1;
      loadResult(submission.submission_id).catch((reason: unknown) => { setError(errorMessage(reason, locale)); setBusy(false); });
    }, delay);
    return () => window.clearTimeout(timer);
  }, [submission, loadResult, locale]);

  const submit = async () => {
    if (!currentItem || !answer.trim() || !reasoning.trim()) return;
    setBusy(true);
    setError(null);
    setNextStep(null);
    try {
      const activeSession = sessionId ?? (await api.createSession(packageId, version, locale, instructionLocale)).session_id;
      setSessionId(activeSession);
      const keyName = `cobri.pending.${itemId}`;
      const existing = localStorage.getItem(keyName);
      const pending = existing ? JSON.parse(existing) as { key: string } : { key: crypto.randomUUID() };
      localStorage.setItem(keyName, JSON.stringify({ sessionId: activeSession, key: pending.key }));
      const accepted = await api.submit(activeSession, {
        item_id: currentItem.item_id,
        answer,
        reasoning,
        purpose: currentItem.purpose,
        parent_submission_id: currentItem.purpose === "assessment" ? null : parentId,
      }, pending.key);
      localStorage.setItem(keyName, JSON.stringify({ sessionId: activeSession, key: pending.key, submissionId: accepted.submission_id }));
      pollCount.current = 0;
      setSubmission(accepted);
    } catch (reason) {
      setError(errorMessage(reason, locale));
      setBusy(false);
    }
  };

  const continueFlow = () => {
    if (!nextStep?.next_item || !submission) return;
    setCurrentItem(nextStep.next_item);
    setParentId(nextStep.next_item.purpose === "assessment" ? null : submission.submission_id);
    setAnswer("");
    setReasoning("");
    setSubmission(null);
    setNextStep(null);
    setError(null);
  };

  const retryInfrastructureFailure = () => {
    localStorage.removeItem(`cobri.pending.${itemId}`);
    setSubmission(null);
    setNextStep(null);
    setError(null);
    setBusy(false);
  };

  if (error && !lesson) return <section className="page-width"><ErrorNotice message={error} /></section>;
  if (!lesson || !currentItem) return <section className="page-width"><LessonSkeleton /></section>;

  return (
    <section className="workspace page-width">
      <aside className="lesson-context">
        <Link className="back-link" to="/">{locale === "ar" ? <ArrowRight size={17} /> : <ArrowLeft size={17} />}{t.back}</Link>
        <div className="step-track" aria-label="Learning progress">
          {(["assessment", "practice", "transfer"] as AttemptPurpose[]).map((step) => (
            <span key={step} className={currentItem.purpose === step ? "active" : ""}>{step}</span>
          ))}
        </div>
        <h1>{lesson.title[instructionLocale]}</h1>
        <p className="prompt" dir={instructionLocale === "ar" ? "rtl" : "ltr"}>{currentItem.prompt[instructionLocale]}</p>
        <div className="rubric-block">
          <h2>{instructionLocale === "ar" ? "ما الذي نتحقق منه" : "What we check"}</h2>
          <ul>{lesson.rubric.map((criterion) => <li key={criterion.criterion_id}>{criterion.description[instructionLocale]}</li>)}</ul>
        </div>
      </aside>
      <div className="attempt-panel">
        {nextStep?.remediation && (
          <div className="remediation" role="status">
            <Sparkle size={22} weight="fill" aria-hidden="true" />
            <div><strong>{instructionLocale === "ar" ? "فكرة للمراجعة" : "A point to review"}</strong><p>{nextStep.remediation[instructionLocale]}</p></div>
          </div>
        )}
        {!submission?.evaluation && nextStep?.action !== "failed" && (
          <form onSubmit={(event) => { event.preventDefault(); void submit(); }}>
            <label htmlFor="answer">{t.code}</label>
            <p className="field-help" id="answer-help">{t.codeHelp}</p>
            <textarea id="answer" className="code-input" value={answer} onChange={(event) => setAnswer(event.target.value)} aria-describedby="answer-help" spellCheck={false} dir="ltr" rows={10} required />
            <label htmlFor="reasoning">{t.reasoning}</label>
            <p className="field-help" id="reasoning-help">{t.reasoningHelp}</p>
            <textarea id="reasoning" value={reasoning} onChange={(event) => setReasoning(event.target.value)} aria-describedby="reasoning-help" rows={5} required />
            {error && <ErrorNotice message={error} />}
            <button className="primary-button" disabled={busy || !answer.trim() || !reasoning.trim()}>{busy ? t.checking : t.submit}</button>
          </form>
        )}
        {busy && !submission?.evaluation && <div className="evaluation-skeleton" role="status">{t.checking}</div>}
        {submission?.evaluation && <Feedback submission={submission} lesson={lesson} nextStep={nextStep} locale={locale} instructionLocale={instructionLocale} onContinue={continueFlow} />}
        {nextStep?.action === "failed" && (
          <div>
            <ErrorNotice message={nextStep.message[instructionLocale]} />
            <button className="primary-button" type="button" onClick={retryInfrastructureFailure}>
              {t.tryAgain}
            </button>
          </div>
        )}
      </div>
    </section>
  );
}

function Feedback({ submission, lesson, nextStep, locale, instructionLocale, onContinue }: { submission: SubmissionView; lesson: LessonDetail; nextStep: NextStepView | null; locale: Locale; instructionLocale: Locale; onContinue: () => void }) {
  const t = copy[locale];
  const evaluation = submission.evaluation!;
  return (
    <div className="feedback" aria-live="polite">
      <div className="feedback-heading"><CheckCircle size={28} weight="fill" /><h2>{t.feedback}</h2></div>
      <dl className="result-grid">
        <div><dt>{t.outcome}</dt><dd>{evaluation.outcome_verdict}</dd></div>
        <div><dt>{t.reasoningResult}</dt><dd>{evaluation.reasoning_verdict}</dd></div>
        <div><dt>{t.diagnosis}</dt><dd>{evaluation.diagnostic_status}</dd></div>
      </dl>
      <section className="evidence-block">
        <h3>{t.evidence}</h3>
        {lesson.evidence.filter((source) => evaluation.evidence_references.includes(source.evidence_id)).map((source) => (
          <article key={source.evidence_id}><p>{source.explanation[instructionLocale]}</p><a href={source.source_url} target="_blank" rel="noreferrer">{source.source_title}</a></article>
        ))}
      </section>
      {nextStep && <div className="next-step"><p>{nextStep.message[instructionLocale]}</p>{nextStep.next_item && <button className="primary-button" type="button" onClick={onContinue}>{nextStep.action === "retry" ? t.tryAgain : t.continue}</button>}</div>}
    </div>
  );
}

function ErrorNotice({ message }: { message: string }) {
  return <div className="error-notice" role="alert"><WarningCircle size={21} weight="fill" /><span>{message}</span></div>;
}

function LessonSkeleton() {
  return <div className="skeleton-stack" aria-label="Loading"><span /><span /><span /></div>;
}

function NavigateHome({ locale }: { locale: Locale }) {
  const navigate = useNavigate();
  useEffect(() => {
    void navigate("/", { replace: true });
  }, [navigate]);
  return <p>{copy[locale].loading}</p>;
}

function errorMessage(reason: unknown, locale: Locale): string {
  if (reason instanceof ApiError) {
    const suffix = reason.correlationId ? ` (${reason.correlationId})` : "";
    if (reason.code === "authentication_unavailable") return `${locale === "ar" ? "خدمة تسجيل الدخول غير متاحة." : "Sign-in service is unavailable."}${suffix}`;
    if (reason.code === "invalid_progression") return `${locale === "ar" ? "هذه الخطوة غير متاحة بعد." : "This step is not available yet."}${suffix}`;
    return `${reason.message}${suffix}`;
  }
  return locale === "ar" ? "تعذر الاتصال بالخدمة. حاول مرة أخرى." : "Could not reach the service. Try again.";
}

export function AuthenticatedApp() {
  const { getAccessTokenSilently, logout, user } = useAuth0();
  const api = useMemo(() => new CobriApi(import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000", () => getAccessTokenSilently()), [getAccessTokenSilently]);
  return <LearnerApp api={api} userName={user?.name} onSignOut={() => void logout({ logoutParams: { returnTo: window.location.origin } })} />;
}
