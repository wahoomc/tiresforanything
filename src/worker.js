// Tires for Anything: serves the static site and saves tire requests and quote requests.
// Records are stored in the REQUESTS KV namespace (bound in wrangler.jsonc).

import SCHEDULE from "./schedule.json";

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.pathname === "/api/request") {
      return handleRequest(request, env);
    }
    if (url.pathname === "/api/event") {
      return handleEvent(request, env);
    }
    // The preview copy on workers.dev must never show up in Google; only tiresforanything.com should.
    // It also shows every queued blog post, so posts can be checked before their date.
    if (url.hostname.endsWith(".workers.dev")) {
      const res = await env.ASSETS.fetch(request);
      const out = new Response(res.body, res);
      out.headers.set("X-Robots-Tag", "noindex, nofollow");
      return out;
    }
    return serveScheduled(request, env, url);
  },
};

// Blog posts publish on the dates in src/schedule.json (Indiana time). Until a post's date it is a 404,
// and its cards, related links and sitemap entry are left out of every page.
function todayIndiana() {
  // "YYYY-MM-DDTHH:MM" in Indiana time. Schedule entries can be a date ("2026-11-16", live from midnight)
  // or a date and time ("2026-11-12T16:47"); plain string comparison handles both.
  const parts = Object.fromEntries(
    new Intl.DateTimeFormat("en-CA", {
      timeZone: "America/Indiana/Indianapolis",
      year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", hourCycle: "h23",
    }).formatToParts(new Date()).map((p) => [p.type, p.value])
  );
  return `${parts.year}-${parts.month}-${parts.day}T${parts.hour}:${parts.minute}`;
}

async function serveScheduled(request, env, url) {
  const today = todayIndiana();
  const future = new Set(Object.keys(SCHEDULE).filter((k) => !k.startsWith("_") && SCHEDULE[k] > today));
  if (!future.size) return env.ASSETS.fetch(request);

  const m = url.pathname.match(/^\/blog\/([a-z0-9-]+?)(?:\.html)?\/?$/);
  if (m && future.has(m[1])) {
    return new Response(NOT_YET, { status: 404, headers: { "content-type": "text/html; charset=utf-8", "cache-control": "no-store" } });
  }

  // Ask for a full copy (no "not modified" shortcut), because what we send changes from day to day.
  const headers = new Headers(request.headers);
  headers.delete("if-none-match");
  headers.delete("if-modified-since");
  const res = await env.ASSETS.fetch(new Request(request, { headers }));
  const type = res.headers.get("content-type") || "";

  if (url.pathname === "/sitemap.xml" && res.ok) {
    const xml = (await res.text())
      .split("\n")
      .filter((line) => ![...future].some((slug) => line.includes(`/blog/${slug}</loc>`)))
      .join("\n");
    const out = new Response(xml, res);
    out.headers.delete("etag");
    out.headers.set("cache-control", "no-cache");
    return out;
  }
  if (!type.includes("text/html")) return res;

  const slugOf = (href) => {
    const h = (href || "").split(/[?#]/)[0].match(/^\/blog\/([a-z0-9-]+?)(?:\.html)?\/?$/);
    return h ? h[1] : "";
  };
  const out = new HTMLRewriter()
    .on("[data-pub]", {
      element(el) {
        if (el.getAttribute("data-pub") > today) el.remove();
      },
    })
    .on('a[href^="/blog/"]', {
      element(el) {
        if (future.has(slugOf(el.getAttribute("href")))) el.removeAndKeepContent();
      },
    })
    .transform(res);
  const final = new Response(out.body, out);
  final.headers.delete("etag");
  final.headers.set("cache-control", "no-cache");
  return final;
}

const NOT_YET = `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta name="robots" content="noindex"><title>Page not found | Tires for Anything</title></head><body style="font-family:system-ui,sans-serif;max-width:560px;margin:60px auto;padding:0 16px;line-height:1.5"><h1>Page not found</h1><p>We couldn't find that page. Try the <a href="/blog/">blog</a> or the <a href="/tire-size-decoder/">tire size decoder</a>, or head back to <a href="/">Tires for Anything</a>.</p></body></html>`;

async function handleRequest(request, env) {
  if (request.method !== "POST") return json({ error: "Use POST" }, 405);
  let body;
  try {
    body = await request.json();
  } catch {
    return json({ error: "Bad request" }, 400);
  }
  // Honeypot field: real visitors never fill it in.
  if (body.website) return json({ saved: true });

  const clean = (v, n) => String(v ?? "").slice(0, n).trim();
  const type = body.type === "quote" ? "quote" : "request";
  const record = {
    type,
    page: clean(body.page, 40),
    equipment: clean(body.equipment, 200),
    size: clean(body.size, 60),
    notes: clean(body.notes, 1000),
    email: clean(body.email, 200),
    at: new Date().toISOString(),
  };
  if (type === "quote") {
    Object.assign(record, {
      qty: clean(body.qty, 6),
      timeline: clean(body.timeline, 60),
      zip: clean(body.zip, 10),
      name: clean(body.name, 120),
      company: clean(body.company, 160),
      phone: clean(body.phone, 40),
    });
    if (!record.name || !record.email || !/^\d{5}$/.test(record.zip)) {
      return json({ error: "Name, email and ZIP code are required." }, 400);
    }
  } else if (!record.equipment && !record.size) {
    return json({ error: "Tell us the equipment or the tire size." }, 400);
  }
  if (!env.REQUESTS) return json({ saved: false });

  // Anything sent from a workers.dev address (preview builds) is saved as a test.
  const host = new URL(request.url).hostname;
  const prefix = host.endsWith(".workers.dev") ? "test-" : "";
  if (prefix) record.test = true;
  const key = `${prefix}${type}:${record.at}:${crypto.randomUUID().slice(0, 8)}`;
  await env.REQUESTS.put(key, JSON.stringify(record));
  await count(env, request, type === "quote" ? "quote_submit" : "request_submit", record.page);
  return json({ saved: true });
}

// Click counting. One record per day, like stats:2026-10-25 = {"amazon | trailer-tires": 12, ...}.
// No personal data is stored. Visits from workers.dev (preview) are kept separate as test-stats.
const EVENTS = ["amazon", "darkside", "find_shop", "quote_open", "request_open", "decode"];

async function handleEvent(request, env) {
  if (request.method !== "POST") return json({ error: "Use POST" }, 405);
  let body;
  try {
    body = await request.json();
  } catch {
    return json({ ok: false }, 400);
  }
  if (!EVENTS.includes(body.e)) return json({ ok: false }, 400);
  await count(env, request, body.e, String(body.p || "home"));
  return json({ ok: true });
}

async function count(env, request, ev, page) {
  if (!env.REQUESTS) return;
  try {
    const host = new URL(request.url).hostname;
    const day = new Date().toISOString().slice(0, 10);
    const key = (host.endsWith(".workers.dev") ? "test-stats:" : "stats:") + day;
    const label = `${ev} | ${String(page).replace(/[^a-z0-9\/ -]/gi, "").slice(0, 60)}`;
    const cur = (await env.REQUESTS.get(key, "json")) || {};
    cur[label] = (cur[label] || 0) + 1;
    await env.REQUESTS.put(key, JSON.stringify(cur));
  } catch {
    // counting must never break the site
  }
}

function json(obj, status = 200) {
  return new Response(JSON.stringify(obj), {
    status,
    headers: { "content-type": "application/json; charset=utf-8" },
  });
}
