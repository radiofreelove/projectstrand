// Run axe-core (WCAG 2.0 to 2.2, levels A and AA) on every built page.
// Used in the GitHub Actions "axe" job:
//   npm install --no-save axe-core playwright && node tests/axe_check.mjs
// Prints every violation. Exit 1 on any serious or critical violation.
import { chromium } from "playwright";
import { createRequire } from "node:module";
import { readFileSync, readdirSync } from "node:fs";
import { createServer } from "node:http";
import { extname, join, resolve } from "node:path";

const require = createRequire(import.meta.url);
const axeSource = readFileSync(require.resolve("axe-core/axe.min.js"), "utf8");
const PUBLIC = resolve("public");
const TYPES = { ".html": "text/html", ".css": "text/css", ".js": "text/javascript", ".svg": "image/svg+xml", ".json": "application/json", ".woff2": "font/woff2" };

const server = createServer((req, res) => {
  const path = join(PUBLIC, decodeURIComponent(new URL(req.url, "http://x").pathname));
  try {
    const body = readFileSync(path.endsWith("/") ? join(path, "index.html") : path);
    res.writeHead(200, { "Content-Type": TYPES[extname(path)] || "application/octet-stream" });
    res.end(body);
  } catch {
    res.writeHead(404);
    res.end("not found");
  }
});
await new Promise((ok) => server.listen(0, "127.0.0.1", ok));
const base = `http://127.0.0.1:${server.address().port}/`;

const browser = await chromium.launch();
// bypassCSP lets the test inject axe; the real site keeps its strict policy.
const context = await browser.newContext({ bypassCSP: true });
const page = await context.newPage();
let serious = 0;
for (const theme of ["light", "dark", "contrast"]) {
  for (const file of readdirSync(PUBLIC).filter((f) => f.endsWith(".html")).sort()) {
    await page.goto(base + file);
    await page.evaluate((t) => document.documentElement.setAttribute("data-theme", t), theme);
    await page.addScriptTag({ content: axeSource });
    const result = await page.evaluate(async () =>
      // eslint-disable-next-line no-undef
      await axe.run(document, { runOnly: { type: "tag", values: ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa", "best-practice"] } })
    );
    for (const v of result.violations) {
      const level = v.impact || "unknown";
      if (level === "serious" || level === "critical") serious += 1;
      console.log(`${theme.padEnd(8)} ${file.padEnd(20)} ${level.padEnd(9)} ${v.id}: ${v.help} (${v.nodes.length} element(s))`);
    }
    if (!result.violations.length) console.log(`${theme.padEnd(8)} ${file.padEnd(20)} ok`);
  }
}
await browser.close();
server.close();
console.log(`\n${serious} serious or critical violation(s).`);
process.exit(serious ? 1 : 0);
