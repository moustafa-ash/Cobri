const required = ["COBRI_LIVE_BASE_URL", "COBRI_LIVE_TOKEN"];
const missing = required.filter((name) => !process.env[name]);
if (missing.length) {
  console.error(`Live verification requires: ${missing.join(", ")}`);
  process.exit(2);
}

const response = await fetch(`${process.env.COBRI_LIVE_BASE_URL}/health/live`, {
  headers: { Authorization: `Bearer ${process.env.COBRI_LIVE_TOKEN}` },
});
if (!response.ok) {
  console.error(`Live health check failed: HTTP ${response.status}`);
  process.exit(1);
}
const progress = await fetch(`${process.env.COBRI_LIVE_BASE_URL}/api/v1/progress`, {
  headers: { Authorization: `Bearer ${process.env.COBRI_LIVE_TOKEN}` },
});
if (!progress.ok) {
  console.error(`Live progress check failed: HTTP ${progress.status}`);
  process.exit(1);
}
const body = await progress.json();
console.log(JSON.stringify({ status: "live", health: "ok", progressItems: Array.isArray(body) ? body.length : 0 }));
