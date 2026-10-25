# Tires for Anything

Source for tiresforanything.com, served by Cloudflare Workers. `src/worker.js` serves the files in `public/` and handles the request and quote forms (`/api/request`) and click counting (`/api/event`), saved in the `REQUESTS` KV store.

## Editing the site

Edit the sources, then rebuild. Don't edit the generated pages in `public/` by hand.

- `src/site.html` holds every page's sections, styles and script.
- `src/blog/` holds blog post bodies (`*.body.html`) and their structured data (`*.jsonld`).

Rebuild:

1. `python3 tools/build_site.py` writes one page per category and tool (for example `public/forklift-tires/index.html`), the blog pages and `public/sitemap.xml`.
2. Start the site locally with `npx wrangler dev --port 8799`, then run `node tools/prerender.mjs` from a folder where Playwright is installed. This writes the size tables and menus into the HTML so search engines can read them.

## Click counts

Daily totals are saved in KV as `stats:YYYY-MM-DD`. Each entry is a label like `amazon | trailer-tires` with a count. Clicks on the preview site are saved as `test-stats:`. Form submissions are counted as `quote_submit` and `request_submit`.

## Preview mode

`PREVIEW = True` in `tools/build_site.py` adds noindex to every page. `public/robots.txt` and `public/_headers` also block search engines. At launch, change all three, rebuild, and submit the sitemap in Google Search Console.
