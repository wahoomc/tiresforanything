// Tires for Anything: serves the static site and saves "Can't find your tire?" requests.
// Requests are stored in the REQUESTS KV namespace once it is bound in wrangler.jsonc.

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
  const record = {
    page: clean(body.page, 40),
    equipment: clean(body.equipment, 200),
    size: clean(body.size, 60),
    notes: clean(body.notes, 1000),
    email: clean(body.email, 200),
    at: new Date().toISOString(),
  };
  if (!record.equipment && !record.size) {
    return json({ error: "Tell us the equipment or the tire size." }, 400);
  }
  if (!env.REQUESTS) return json({ saved: false });

  const key = `request:${record.at}:${crypto.randomUUID().slice(0, 8)}`;
  await env.REQUESTS.put(key, JSON.stringify(record));
  return json({ saved: true });
}

function json(obj, status = 200) {
  return new Response(JSON.stringify(obj), {
    status,
    headers: { "content-type": "application/json; charset=utf-8" },
  });
}
