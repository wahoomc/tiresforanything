// Tires for Anything: serves the static site and saves tire requests and quote requests.
// Records are stored in the REQUESTS KV namespace (bound in wrangler.jsonc).

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.pathname === "/api/request") {
      return handleRequest(request, env);
    }
    return env.ASSETS.fetch(request);
  },
};

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
  return json({ saved: true });
}

function json(obj, status = 200) {
  return new Response(JSON.stringify(obj), {
    status,
    headers: { "content-type": "application/json; charset=utf-8" },
  });
}
