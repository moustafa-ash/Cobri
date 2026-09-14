import { useAuth0 } from "@auth0/auth0-react";
import {
  ArrowLeft,
  ArrowRight,
  ChatCircleDots,
  CheckCircle,
  Code,
  PaperPlaneTilt,
  SignOut,
  Sparkle,
  WarningCircle,
  X,
} from "@phosphor-icons/react";
import {
  lazy,
  Suspense,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { Link, matchPath, useLocation, useNavigate } from "react-router-dom";

import {
  ApiError,
  CobriApi,
  type AttemptPurpose,
  type LessonDetail,
  type Locale,
  type NextStepView,
  type SubmissionView,
  type TopicDiscoveryResponse,
} from "./api/client";
import { copy } from "./i18n";

const PythonEditor = lazy(() => import("./CodeEditor"));

interface LearnerAppProps {
  api: CobriApi;
  onSignOut: () => void;
  userName?: string;
}

interface CurrentItem {
  item_id: string;
  prompt: Record<Locale, string>;
  purpose: AttemptPurpose;
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
        <TutorExperience api={api} locale={uiLocale} instructionLocale={instructionLocale} />
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

function TutorExperience({ api, locale, instructionLocale }: { api: CobriApi; locale: Locale; instructionLocale: Locale }) {
  const location = useLocation();
  const navigate = useNavigate();
  const lessonRoute = matchPath("/lesson/:packageId/:version/:itemId", location.pathname);
  const packageId = lessonRoute?.params.packageId ?? "";
  const version = lessonRoute?.params.version ?? "";
  const itemId = lessonRoute?.params.itemId ?? "";
  const hasLessonRoute = lessonRoute !== null;
  const lessonRouteKey = hasLessonRoute ? `${packageId}/${version}/${itemId}` : "";
  const [query, setQuery] = useState("");
  const [submittedQuery, setSubmittedQuery] = useState<string | null>(null);
  const [discovery, setDiscovery] = useState<TopicDiscoveryResponse | null>(null);
  const [lesson, setLesson] = useState<LessonDetail | null>(null);
  const [currentItem, setCurrentItem] = useState<CurrentItem | null>(null);
  const [parentId, setParentId] = useState<string | null>(null);
  const [answer, setAnswer] = useState("");
  const [reasoning, setReasoning] = useState("");
  const [submission, setSubmission] = useState<SubmissionView | null>(null);
  const [nextStep, setNextStep] = useState<NextStepView | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [discovering, setDiscovering] = useState(false);
  const [loadingLesson, setLoadingLesson] = useState(false);
  const [checking, setChecking] = useState(false);
  const [submittedForReview, setSubmittedForReview] = useState(false);
  const [editorOpen, setEditorOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const pollCount = useRef(0);
  const conversationEnd = useRef<HTMLDivElement>(null);
  const localeRef = useRef(locale);
  const t = copy[locale];

  useEffect(() => {
    localeRef.current = locale;
  }, [locale]);

  useEffect(() => {
    if (location.pathname !== "/" && !hasLessonRoute) void navigate("/", { replace: true });
  }, [hasLessonRoute, location.pathname, navigate]);

  useEffect(() => {
    if (!hasLessonRoute) {
      setLesson(null);
      setCurrentItem(null);
      setSubmission(null);
      setNextStep(null);
      setEditorOpen(false);
      setSubmittedForReview(false);
      return;
    }
    let active = true;
    setLoadingLesson(true);
    setLesson(null);
    setCurrentItem(null);
    setAnswer("");
    setReasoning("");
    setParentId(null);
    setError(null);
    setSubmission(null);
    setNextStep(null);
    setSubmittedForReview(false);
    api.lesson(packageId, version, itemId).then((result) => {
      if (!active) return;
      setLesson(result);
      setCurrentItem({ item_id: result.item_id, prompt: result.prompt, purpose: "assessment" });
      setEditorOpen(true);
      setLoadingLesson(false);
    }).catch((reason: unknown) => {
      if (!active) return;
      setError(errorMessage(reason, localeRef.current));
      setLoadingLesson(false);
    });
    return () => { active = false; };
  }, [api, hasLessonRoute, itemId, lessonRouteKey, packageId, version]);

  const loadResult = useCallback(async (submissionId: string) => {
    const result = await api.submission(submissionId);
    setSubmission(result);
    if (result.job.status === "succeeded" || result.job.status === "failed") {
      setNextStep(await api.next(result.submission_id));
      localStorage.removeItem(`cobri.pending.${itemId}`);
      setChecking(false);
    }
    return result;
  }, [api, itemId]);

  useEffect(() => {
    if (!itemId) return;
    const saved = localStorage.getItem(`cobri.pending.${itemId}`);
    if (!saved) return;
    const pending = JSON.parse(saved) as { sessionId: string; submissionId?: string };
    setSessionId(pending.sessionId);
    if (pending.submissionId) {
      setSubmittedForReview(true);
      setEditorOpen(false);
      setChecking(true);
      loadResult(pending.submissionId).catch((reason: unknown) => {
        setError(errorMessage(reason, locale));
        setChecking(false);
      });
    }
  }, [itemId, loadResult, locale]);

  useEffect(() => {
    if (!submission || !["pending", "running"].includes(submission.job.status)) return;
    const delay = Math.min(5000, 750 * 2 ** Math.min(pollCount.current, 3));
    const timer = window.setTimeout(() => {
      pollCount.current += 1;
      loadResult(submission.submission_id).catch((reason: unknown) => {
        setError(errorMessage(reason, locale));
        setChecking(false);
      });
    }, delay);
    return () => window.clearTimeout(timer);
  }, [submission, loadResult, locale]);

  useEffect(() => {
    conversationEnd.current?.scrollIntoView?.({ behavior: "smooth", block: "nearest" });
  }, [discovery, lesson, currentItem, submittedForReview, submission, nextStep, error]);

  const discover = async () => {
    const topic = query.trim();
    if (!topic || discovering) return;
    setSubmittedQuery(topic);
    setQuery("");
    setDiscovery(null);
    setError(null);
    setDiscovering(true);
    try {
      setDiscovery(await api.discoverTopic(topic));
    } catch (reason) {
      setError(errorMessage(reason, locale));
    } finally {
      setDiscovering(false);
    }
  };

  const openLesson = () => {
    setAnswer("");
    setReasoning("");
    setParentId(null);
    setSessionId(null);
    setEditorOpen(true);
  };

  const submit = async () => {
    if (!currentItem || !answer.trim() || !reasoning.trim()) return;
    setChecking(true);
    setSubmittedForReview(true);
    setEditorOpen(false);
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
      if (!["pending", "running"].includes(accepted.job.status)) await loadResult(accepted.submission_id);
    } catch (reason) {
      setError(errorMessage(reason, locale));
      setChecking(false);
      if (!submission) setSubmittedForReview(false);
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
    setSubmittedForReview(false);
    setEditorOpen(true);
  };

  const retryInfrastructureFailure = () => {
    localStorage.removeItem(`cobri.pending.${itemId}`);
    setSubmission(null);
    setNextStep(null);
    setError(null);
    setChecking(false);
    setSubmittedForReview(false);
    setEditorOpen(true);
  };

  const retryResultRequest = () => {
    setError(null);
    if (!submission) {
      setSubmittedForReview(false);
      setEditorOpen(true);
      return;
    }
    setChecking(true);
    loadResult(submission.submission_id).catch((reason: unknown) => {
      setError(errorMessage(reason, locale));
      setChecking(false);
    });
  };

  return (
    <section className={`tutor-shell ${editorOpen && lesson && currentItem ? "editor-is-open" : ""}`} aria-labelledby="topic-chat-title">
      <div className="chat-column">
        <div className="chat-heading">
          <span className="section-icon"><ChatCircleDots size={25} weight="duotone" /></span>
          <div>
            <h1 id="topic-chat-title">{lesson ? lesson.title[instructionLocale] : t.chatTitle}</h1>
            <p>{lesson ? t.lessonChatSubtitle : t.chatSubtitle}</p>
          </div>
          {lesson && currentItem && !editorOpen && !submittedForReview && (
            <button className="open-editor-button" type="button" onClick={() => setEditorOpen(true)}>
              <Code size={19} weight="bold" aria-hidden="true" />{t.openEditor}
            </button>
          )}
        </div>

        <div className="conversation" aria-live="polite" aria-label={t.chatPanel}>
          <AssistantMessage><p>{t.chatGreeting}</p></AssistantMessage>
          {submittedQuery && <LearnerMessage><p>{submittedQuery}</p></LearnerMessage>}
          {discovering && <TypingMessage label={t.findingTopics} />}
          {discovery && (
            <AssistantMessage wide>
              {discovery.status === "supported" ? (
                <>
                  <p>{t.supportedTopic}</p>
                  <div className="topic-options">
                    {discovery.options.map((option) => (
                      <Link
                        className="topic-option"
                        key={option.item_id}
                        onClick={openLesson}
                        to={`/lesson/${discovery.content_package_id}/${discovery.content_version}/${option.item_id}`}
                      >
                        <span><strong>{option.title[instructionLocale]}</strong><small>{option.prompt[instructionLocale]}</small></span>
                        {locale === "ar" ? <ArrowLeft size={18} /> : <ArrowRight size={18} />}
                      </Link>
                    ))}
                  </div>
                </>
              ) : (
                <><p>{t.unsupportedTopic}</p><small className="availability-note">{t.availableNow}</small></>
              )}
            </AssistantMessage>
          )}
          {loadingLesson && <TypingMessage label={t.loadingLesson} />}
          {lesson && currentItem && (
            <AssistantMessage wide>
              <span className="message-kicker">{purposeLabel(currentItem.purpose, instructionLocale)}</span>
              <p dir={instructionLocale === "ar" ? "rtl" : "ltr"}>{currentItem.prompt[instructionLocale]}</p>
              {!submittedForReview && !editorOpen && <button className="message-action" type="button" onClick={() => setEditorOpen(true)}><Code size={18} />{t.openEditor}</button>}
            </AssistantMessage>
          )}
          {submittedForReview && <LearnerMessage><p>{t.sentForEvaluation}</p></LearnerMessage>}
          {checking && <TypingMessage label={t.checking} />}
          {submission?.evaluation && lesson && (
            <AssistantMessage wide>
              <Feedback
                submission={submission}
                lesson={lesson}
                nextStep={nextStep}
                locale={locale}
                instructionLocale={instructionLocale}
                onContinue={continueFlow}
              />
            </AssistantMessage>
          )}
          {nextStep?.action === "failed" && (
            <AssistantMessage wide>
              <ErrorNotice message={nextStep.message[instructionLocale]} />
              <button className="message-action" type="button" onClick={retryInfrastructureFailure}>{t.tryAgain}</button>
            </AssistantMessage>
          )}
          {error && (
            <AssistantMessage wide>
              <ErrorNotice message={error} />
              {(submission || lesson) && <button className="message-action" type="button" onClick={retryResultRequest}>{t.tryAgain}</button>}
            </AssistantMessage>
          )}
          <div ref={conversationEnd} />
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
            placeholder={lesson ? t.chatPlaceholder : t.topicPlaceholder}
            rows={2}
            maxLength={300}
          />
          <button className="send-button" type="submit" disabled={discovering || !query.trim()} aria-label={t.sendTopic}>
            <PaperPlaneTilt size={21} weight="fill" aria-hidden="true" />
          </button>
        </form>
        <p className="composer-hint">{t.composerHint}</p>
      </div>

      {editorOpen && lesson && currentItem && (
        <AttemptDrawer
          lesson={lesson}
          currentItem={currentItem}
          locale={locale}
          instructionLocale={instructionLocale}
          answer={answer}
          reasoning={reasoning}
          checking={checking}
          onAnswer={setAnswer}
          onReasoning={setReasoning}
          onClose={() => setEditorOpen(false)}
          onSubmit={submit}
        />
      )}
      {!editorOpen && lesson && currentItem && !submittedForReview && (
        <button className="side-editor-tab" type="button" onClick={() => setEditorOpen(true)} aria-label={t.openEditor}>
          <Code size={20} weight="bold" aria-hidden="true" /><span>{t.editorTab}</span>
        </button>
      )}
    </section>
  );
}

function AssistantMessage({ children, wide = false }: { children: React.ReactNode; wide?: boolean }) {
  return (
    <div className="message-row assistant-message">
      <span className="message-avatar" aria-hidden="true">C</span>
      <div className={`message-bubble ${wide ? "wide-message" : ""}`}>{children}</div>
    </div>
  );
}

function LearnerMessage({ children }: { children: React.ReactNode }) {
  return <div className="message-row learner-message"><div className="message-bubble">{children}</div></div>;
}

function TypingMessage({ label }: { label: string }) {
  return (
    <div className="message-row assistant-message">
      <span className="message-avatar" aria-hidden="true">C</span>
      <div className="message-bubble typing-message"><span /><span /><span /><span className="sr-only">{label}</span></div>
    </div>
  );
}

function AttemptDrawer({ lesson, currentItem, locale, instructionLocale, answer, reasoning, checking, onAnswer, onReasoning, onClose, onSubmit }: {
  lesson: LessonDetail;
  currentItem: CurrentItem;
  locale: Locale;
  instructionLocale: Locale;
  answer: string;
  reasoning: string;
  checking: boolean;
  onAnswer: (value: string) => void;
  onReasoning: (value: string) => void;
  onClose: () => void;
  onSubmit: () => Promise<void>;
}) {
  const t = copy[locale];
  return (
    <aside className="attempt-drawer" aria-label={t.workspaceLabel}>
      <div className="drawer-header">
        <div>
          <span className="drawer-file"><Code size={18} weight="bold" aria-hidden="true" />solution.py</span>
          <small>{purposeLabel(currentItem.purpose, locale)}</small>
        </div>
        <button className="drawer-close" type="button" onClick={onClose} aria-label={t.closeEditor}>
          <X size={20} weight="bold" aria-hidden="true" />
          <span className="mobile-close-label">{t.returnToChat}</span>
        </button>
      </div>
      <div className="drawer-prompt" dir={instructionLocale === "ar" ? "rtl" : "ltr"}>
        <strong>{lesson.title[instructionLocale]}</strong>
        <p>{currentItem.prompt[instructionLocale]}</p>
      </div>
      <form className="attempt-form" onSubmit={(event) => { event.preventDefault(); void onSubmit(); }}>
        <div className="editor-field">
          <span className="editor-label">{t.code}</span>
          <p className="field-help">{t.codeHelp}</p>
          <Suspense fallback={<div className="editor-loading" role="status">{t.loadingEditor}</div>}>
            <PythonEditor value={answer} onChange={onAnswer} ariaLabel={t.code} />
          </Suspense>
        </div>
        <div className="reasoning-field">
          <label htmlFor="reasoning">{t.reasoning}</label>
          <p className="field-help" id="reasoning-help">{t.reasoningHelp}</p>
          <textarea id="reasoning" value={reasoning} onChange={(event) => onReasoning(event.target.value)} aria-describedby="reasoning-help" rows={4} required />
        </div>
        <div className="drawer-actions">
          <button className="primary-button" disabled={checking || !answer.trim() || !reasoning.trim()}>{checking ? t.checking : t.submit}</button>
        </div>
      </form>
    </aside>
  );
}

function Feedback({ submission, lesson, nextStep, locale, instructionLocale, onContinue }: { submission: SubmissionView; lesson: LessonDetail; nextStep: NextStepView | null; locale: Locale; instructionLocale: Locale; onContinue: () => void }) {
  const t = copy[locale];
  const evaluation = submission.evaluation!;
  return (
    <div className="feedback" aria-live="polite">
      <div className="feedback-heading"><CheckCircle size={25} weight="fill" /><h2>{t.feedback}</h2></div>
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
      {nextStep?.remediation && (
        <div className="remediation" role="status">
          <Sparkle size={20} weight="fill" aria-hidden="true" />
          <div><strong>{instructionLocale === "ar" ? "فكرة للمراجعة" : "A point to review"}</strong><p>{nextStep.remediation[instructionLocale]}</p></div>
        </div>
      )}
      {nextStep && <div className="next-step"><p>{nextStep.message[instructionLocale]}</p>{nextStep.next_item && <button className="message-action" type="button" onClick={onContinue}>{nextStep.action === "retry" ? t.tryAgain : t.continue}</button>}</div>}
    </div>
  );
}

function ErrorNotice({ message }: { message: string }) {
  return <div className="error-notice" role="alert"><WarningCircle size={21} weight="fill" /><span>{message}</span></div>;
}

function purposeLabel(purpose: AttemptPurpose, locale: Locale): string {
  const labels = locale === "ar"
    ? { assessment: "تقييم", practice: "تدريب", transfer: "تطبيق جديد" }
    : { assessment: "Assessment", practice: "Practice", transfer: "Transfer" };
  return labels[purpose];
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
