// Writes the script-built parts of each page (category menu, home grid, size tables, shop boxes)
// straight into the HTML, so search engines see them without running code. The page script
// clears and redraws them on load, so nothing doubles up.
// Run after tools/build_site.py, with the site running locally:  npx wrangler dev --port 8799
//   NODE_PATH=/tmp/node_modules node tools/prerender.mjs
import { createRequire } from "node:module";
// Playwright is looked up from the folder you run this in.
const { chromium } = createRequire(process.cwd() + "/")("playwright");
import fs from "node:fs";
import path from "node:path";

const ROOT = path.resolve(path.dirname(new URL(import.meta.url).pathname), "..");
const BASE = process.env.BASE || "http://localhost:8799";
const pub = path.join(ROOT, "public");
const files = [path.join(pub, "index.html")];
for (const d of fs.readdirSync(pub, { withFileTypes: true })) {
  if (d.isDirectory() && fs.existsSync(path.join(pub, d.name, "index.html")) && d.name !== "blog") files.push(path.join(pub, d.name, "index.html"));
}
const browser = await chromium.launch({ executablePath: "/opt/pw-browsers/chromium" }).catch(() => chromium.launch());
const page = await browser.newPage();
let n = 0;
for (const f of files) {
  const rel = "/" + path.relative(pub, f).replace(/index\.html$/, "");
  await page.goto(BASE + rel);
  await page.waitForTimeout(300);
  const parts = await page.evaluate(() => {
    const clean = (el) => { el.querySelectorAll("[aria-current]").forEach((a) => a.removeAttribute("aria-current")); return el.innerHTML; };
    const out = {};
    const cb = document.getElementById("catbar"); if (cb) out['<div class="wrap" id="catbar"></div>'] = ['<div class="wrap" id="catbar">', clean(cb.cloneNode(true)), "</div>"];
    const cats = document.getElementById("cats"); if (cats) out['<div class="cats" id="cats"></div>'] = ['<div class="cats" id="cats">', cats.innerHTML, "</div>"];
    document.querySelectorAll('tbody[id^="sft-"], tbody#mc-rows').forEach((t) => { out[`<tbody id="${t.id}"></tbody>`] = [`<tbody id="${t.id}">`, t.innerHTML, "</tbody>"]; });
    document.querySelectorAll(".shop[data-shop]").forEach((s) => { const k = s.getAttribute("data-shop"); out[`<div class="shop" data-shop="${k}"></div>`] = [`<div class="shop" data-shop="${k}">`, s.innerHTML, "</div>"]; });
    return out;
  });
  let html = fs.readFileSync(f, "utf8");
  for (const [empty, [open, inner, close]] of Object.entries(parts)) {
    if (html.includes(empty)) { html = html.replace(empty, open + inner + close); n++; }
  }
  fs.writeFileSync(f, html);
}
await browser.close();
console.log(`prerendered ${n} blocks across ${files.length} pages`);
