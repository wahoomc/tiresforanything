// Makes a 1200x630 share image for a blog post (design "A": dark, hazard stripe, big title).
// Usage (run from a folder where Playwright is installed):
//   node tools/og_image.mjs <slug> "<eyebrow>" "<title, use *word* for the yellow part>" "<subtitle>"
// Writes public/og/<slug>.png
import { createRequire } from "node:module";
import fs from "node:fs";
import path from "node:path";
const { chromium } = createRequire(process.cwd() + "/")("playwright");
const ROOT = path.resolve(path.dirname(new URL(import.meta.url).pathname), "..");
const [slug, eyebrow, title, sub] = process.argv.slice(2);
if (!slug || !title) { console.error("usage: og_image.mjs slug eyebrow title subtitle"); process.exit(1); }
const F = ["/tmp/node_modules/@fontsource", path.join(process.cwd(), "node_modules/@fontsource")].find((d) => fs.existsSync(d)) || "";
const esc = (s) => String(s || "").replace(/&/g, "&amp;").replace(/</g, "&lt;");
const t = esc(title).replace(/\*(.+?)\*/g, "<em>$1</em>");
const html = `<!doctype html><html><head><meta charset="utf-8"><style>
@font-face{font-family:BS;src:url(file://${F}/big-shoulders-display/files/big-shoulders-display-latin-900-normal.woff2);font-weight:900}
@font-face{font-family:PS;src:url(file://${F}/public-sans/files/public-sans-latin-400-normal.woff2)}
@font-face{font-family:JB;src:url(file://${F}/jetbrains-mono/files/jetbrains-mono-latin-700-normal.woff2);font-weight:700}
body{margin:0}
#c{width:1200px;height:630px;position:relative;overflow:hidden;box-sizing:border-box;background:#1E2328;color:#F2F3F1;padding:70px 72px}
.tread{position:absolute;left:0;right:0;top:0;height:26px;background:repeating-linear-gradient(115deg,#E9B300 0 14px,transparent 14px 32px)}
.eb{font-family:JB;font-weight:700;letter-spacing:.14em;text-transform:uppercase;font-size:22px;color:#E9B300}
h1{font-family:BS;font-weight:900;font-size:112px;line-height:.92;text-transform:uppercase;margin:22px 0 0;max-width:760px}
h1 em{font-style:normal;color:#E9B300}
.sub{font-family:PS;font-size:30px;opacity:.8;margin-top:22px;max-width:700px}
.bot{position:absolute;left:72px;bottom:58px;display:flex;gap:24px;align-items:center}
.logo{display:flex;align-items:center;gap:14px;font-family:BS;font-weight:900;font-size:40px;text-transform:uppercase}
.logo span{color:#E9B300}.url{font-family:JB;font-weight:700;font-size:22px;opacity:.7}
</style></head><body><div id="c"><div class="tread"></div>
<svg style="position:absolute;right:-170px;top:65px" width="560" height="560" viewBox="0 0 560 560"><circle cx="280" cy="280" r="270" fill="#0B0D0F"/><circle cx="280" cy="280" r="255" fill="none" stroke="#F2F3F1" stroke-opacity=".12" stroke-width="18" stroke-dasharray="10 16"/><circle cx="280" cy="280" r="175" fill="#E9B300"/><circle cx="280" cy="280" r="155" fill="#2B3137"/><circle cx="280" cy="280" r="42" fill="#1E2328" stroke="#E9B300" stroke-width="4"/></svg>
<div class="eb">${esc(eyebrow)}</div><h1>${t}</h1><div class="sub">${esc(sub)}</div>
<div class="bot"><div class="logo"><svg width="46" height="46" viewBox="0 0 30 30"><circle cx="15" cy="15" r="13" fill="none" stroke="#F2F3F1" stroke-width="5" stroke-dasharray="3 2.2"/><circle cx="15" cy="15" r="5.5" fill="#E9B300"/></svg><div>Tires for <span>Anything</span></div></div><div class="url">tiresforanything.com</div></div>
</div></body></html>`;
const tmp = path.join(process.cwd(), `og-${slug}.html`);
fs.writeFileSync(tmp, html);
const b = await chromium.launch({ executablePath: "/opt/pw-browsers/chromium" }).catch(() => chromium.launch());
const p = await b.newPage({ viewport: { width: 1200, height: 630 } });
await p.goto("file://" + tmp);
await p.waitForTimeout(400);
const out = path.join(ROOT, "public/og", slug + ".png");
await p.locator("#c").screenshot({ path: out });
await b.close();
fs.unlinkSync(tmp);
console.log("wrote", out);
