import { chromium } from "playwright";

const executablePath = process.env.COBRI_BROWSER_EXECUTABLE;
const output = process.env.COBRI_BROWSER_ARTIFACT_DIR ?? ".data/browser-artifacts/visual";
const baseUrl = process.env.COBRI_VISUAL_BASE_URL ?? "http://localhost:5173";
await import("node:fs/promises").then(({ mkdir }) => mkdir(output, { recursive: true }));
const browser = await chromium.launch({ headless: true, ...(executablePath ? { executablePath } : {}) });
const findings = [];

for (const viewport of [
  { name: "desktop", width: 1280, height: 900 },
  { name: "mobile", width: 390, height: 844 },
]) {
  const page = await browser.newPage({ viewport });
  const consoleErrors = [];
  const failedResponses = [];
  page.on("console", (message) => {
    if (message.type() === "error") {
      consoleErrors.push({ text: message.text(), location: message.location() });
    }
  });
  page.on("response", (response) => {
    if (response.status() >= 400) failedResponses.push(`${response.status()} ${response.url()}`);
  });
  // Vite keeps a hot-reload socket open, so networkidle never settles in dev.
  await page.goto(`${baseUrl}/visual.html`, { waitUntil: "domcontentloaded" });
  await page.locator("#root").waitFor({ state: "attached" });
  const arabic = viewport.name === "mobile";
  if (arabic) {
    await page.getByLabel("Interface").selectOption("ar");
    await page.getByLabel("لغة الدرس").selectOption("ar");
  }
  const hasContent = (await page.locator("body").innerText()).trim().length > 0;
  const overlay = await page.locator(".vite-error-overlay").count();
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > innerWidth);
  await page.getByLabel(arabic ? "الموضوع المراد التحقق منه" : "Topic to check").fill(arabic ? "دوال بايثون" : "Python functions");
  await page.getByRole("button", { name: arabic ? "إرسال الموضوع" : "Send topic" }).click();
  await page.getByRole("link", { name: arabic ? /إرجاع قيمة/ : /Return a value/ }).click();
  const chatVisibleWithEditor = await page.getByLabel(arabic ? "المحادثة مع كوبري" : "Conversation with Cobri").isVisible();
  const editorVisible = await page.getByLabel(arabic ? "مساحة كتابة الكود" : "Coding workspace").isVisible();
  const expectedEditorLabel = arabic ? "كود Python الخاص بك" : "Your Python code";
  const codeEditor = page.locator(".monaco-editor").locator(`[aria-label="${expectedEditorLabel}"]`).first();
  try {
    await page.locator(".monaco-editor").waitFor({ timeout: 10_000 });
  } catch (error) {
    console.error(JSON.stringify({ consoleErrors, failedResponses, body: (await page.locator("body").innerText()).slice(-2000) }, null, 2));
    throw error;
  }
  await codeEditor.waitFor({ state: "attached" });
  const editorAccessible = (await codeEditor.getAttribute("aria-label")) === expectedEditorLabel;
  await page.waitForTimeout(300);
  await page.screenshot({ path: `${output}/cobri-${viewport.name}-editor.png`, fullPage: false });
  await page.locator(".monaco-editor").click({ position: { x: 120, y: 70 } });
  await page.keyboard.insertText("def double(n):\n    print(n * 2)");
  await page.getByLabel(arabic ? "اشرح تفكيرك" : "Explain your reasoning").fill(arabic ? "تعرض الطباعة القيمة المحسوبة." : "Printing shows the calculated value.");
  await page.getByRole("button", { name: arabic ? "تحقق من إجابتي" : "Check my answer" }).click();
  await page.getByRole("heading", { name: arabic ? "ملاحظاتك" : "Your feedback" }).waitFor({ timeout: 10_000 });
  const feedbackVisible = await page.getByText(arabic ? "فكرة للمراجعة" : "A point to review").isVisible();
  const editorClosedAfterSubmit = (await page.getByLabel(arabic ? "مساحة كتابة الكود" : "Coding workspace").count()) === 0;
  await page.screenshot({
    path: `${output}/cobri-${viewport.name}.png`,
    fullPage: !arabic,
  });
  findings.push({
    ...viewport,
    hasContent,
    overlay,
    overflow,
    consoleErrors,
    failedResponses,
    feedbackVisible,
    chatVisibleWithEditor,
    editorVisible,
    editorClosedAfterSubmit,
    editorAccessible,
  });
  await page.close();
}

await browser.close();
console.log(JSON.stringify(findings, null, 2));
if (
  findings.some(
    (item) =>
      !item.hasContent ||
      item.overlay ||
      item.overflow ||
      item.consoleErrors.length ||
      item.failedResponses.length ||
      !item.feedbackVisible ||
      !item.chatVisibleWithEditor ||
      !item.editorVisible ||
      !item.editorClosedAfterSubmit ||
      !item.editorAccessible,
  )
) {
  process.exitCode = 1;
}
