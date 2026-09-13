import { chromium } from "playwright";

const chrome = "C:/Program Files/Google/Chrome/Application/chrome.exe";
const output =
  "C:/Users/ps420/.codex/visualizations/2026/09/10/01a08ac3-9ac8-7c52-aa92-377d28ded443";
const browser = await chromium.launch({ headless: true, executablePath: chrome });
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
  await page.goto("http://127.0.0.1:5173/visual.html", { waitUntil: "networkidle" });
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
  await page.getByLabel(arabic ? "كود Python الخاص بك" : "Your Python code").fill("def double(n):\n    print(n * 2)");
  await page.getByLabel(arabic ? "اشرح تفكيرك" : "Explain your reasoning").fill(arabic ? "تعرض الطباعة القيمة المحسوبة." : "Printing shows the calculated value.");
  await page.getByRole("button", { name: arabic ? "تحقق من إجابتي" : "Check my answer" }).click();
  await page.getByRole("heading", { name: arabic ? "ملاحظاتك" : "Your feedback" }).waitFor({ timeout: 10_000 });
  const feedbackVisible = await page.getByText(arabic ? "فكرة للمراجعة" : "A point to review").isVisible();
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
      !item.feedbackVisible,
  )
) {
  process.exitCode = 1;
}
