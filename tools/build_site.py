#!/usr/bin/env python3
"""Build the Tires for Anything site.

Source files (edit these):
  src/site.html          every page's sections, styles and script, in one file
  src/blog/*.body.html   blog post bodies; *.jsonld = structured data for each post
Output (generated, committed, served by Cloudflare):
  public/index.html, public/<page>/index.html, public/blog/*.html, public/sitemap.xml

Run:  python3 tools/build_site.py          (then: node tools/prerender.mjs)
PREVIEW = True keeps every page out of Google (noindex). Flip to False at launch,
together with public/robots.txt and public/_headers.
"""
import html, json, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = "https://tiresforanything.com"
PREVIEW = True
TODAY = "2026-10-25"

# view id: (path, browser-tab title, Google description)
PAGES = {
    "home": ("/", "Tires for Anything: The Right Tire for Anything That Rolls",
             "Plain-English tire guides, a size decoder and dealer quotes for anything that rolls: cars, trucks, trailers, mowers, forklifts, tractors, bikes and more."),
    "cars": ("/passenger-car-tires/", "Passenger Car Tires: Sizes, Types and How to Choose",
             "How to read a car tire size, pick all-season, all-weather, winter or performance tires, and shop the right size."),
    "trucks": ("/light-truck-suv-tires/", "Light Truck and SUV Tires: LT vs P, Load Range and Tread Types",
               "Highway, all-terrain and mud-terrain tires for pickups and SUVs, plus LT load ranges and how to read the size."),
    "forklift": ("/forklift-tires/", "Forklift Tires: Press-On, Pneumatic and Solid Sizes",
                 "Find forklift tire sizes, compare press-on cushion, pneumatic and solid pneumatic tires, and get quotes from dealers who install them."),
    "aviation": ("/aircraft-tires/", "Aircraft Tires: Sizes, Ply Ratings and TSO Basics",
                 "General aviation tire sizes like 6.00-6 and 5.00-5, ply ratings, TSO approval, and how to get quotes on tires for your aircraft."),
    "motorcycle": ("/motorcycle-tires/", "Motorcycle Tires by Year, Make and Model",
                   "Factory front and rear tire sizes for popular motorcycles, how to read the size, and when to replace."),
    "farm": ("/farm-tractor-tires/", "Farm and Tractor Tires: R-1, R-4, IF/VF and Sizes",
             "Tractor and implement tire sizes, tread types from R-1 to R-4, IF and VF tires, and quotes from farm tire dealers."),
    "semi": ("/semi-truck-tires/", "Semi Truck Tires: Steer, Drive and Trailer Positions",
             "Commercial truck tire sizes like 11R22.5 and 295/75R22.5, tire positions, retreads, and quotes from truck tire dealers."),
    "trailer": ("/trailer-tires/", "Trailer Tires: ST Sizes, Load Range and Tire Age",
                "ST trailer tire sizes, load ranges, speed ratings and a DOT date checker for boat, utility, horse and camper trailers."),
    "construction": ("/construction-skid-steer-tires/", "Skid Steer and Construction Tires: Sizes and Types",
                     "Skid steer, backhoe, loader and grader tire sizes, pneumatic vs foam-filled vs solid, and quotes for big OTR tires."),
    "lawn": ("/lawn-garden-tires/", "Lawn Mower, Wheelbarrow and Hand Truck Tires",
             "Riding mower, zero-turn, wheelbarrow and hand truck tire sizes, flat-free options, and tires already mounted on a wheel."),
    "atv": ("/atv-utv-golf-cart-tires/", "ATV, UTV and Golf Cart Tires: Sizes and Fitment",
            "ATV, side-by-side and golf cart tire sizes, lift kit sizing, and wheel and tire sets."),
    "rv": ("/rv-motorhome-tires/", "RV and Motorhome Tires: Sizes, Age and Load",
           "Class A, B and C motorhome tire sizes, how old is too old, load and pressure, and where to get them installed."),
    "mobility": ("/wheelchair-mobility-scooter-tires/", "Wheelchair and Mobility Scooter Tires",
                 "Wheelchair, power chair and mobility scooter tire sizes, solid vs pneumatic, and caster wheels."),
    "toys": ("/rc-toy-ride-on-tires/", "RC Car, RC Plane, Ride-On and Scooter Tires and Wheels",
             "Tire and wheel sizes for RC cars and trucks, RC airplanes, kids' ride-on cars, kick and electric scooters, hoverboards and skateboards."),
    "motorsport": ("/go-kart-tires/", "Go-Kart Tires: Sizes and Compounds",
                   "Go-kart tire sizes for sprint, cadet and rental karts, and how compound and size affect grip."),
    "racing": ("/race-car-tires/", "Race Car Tires: Autocross, Track Day, Drag and Dirt",
               "Tires for autocross, track days, road racing, drag racing and dirt oval, and how class rules decide what you can run."),
    "bicycles": ("/bike-tires/", "Bike Tire Sizes: Road, Gravel, Mountain and Kids",
                 "Road, gravel, mountain, fat and kids' bike tire sizes, including 700c, 29er, 20 inch and the fraction sizes that don't swap."),
    "vintage": ("/vintage-antique-tires/", "Vintage and Antique Car Tires: Model T to Muscle Cars",
                "Vintage and antique tire sizes from the Model T to muscle cars, beaded-edge clinchers, and specialty suppliers."),
    "military": ("/military-truck-tires/", "Military Truck Tires: Humvee, Deuce and a Half and Surplus Sizes",
                 "Tire sizes for surplus military trucks like the Humvee and M35, run-flat inserts, and where to find them."),
    "decoder": ("/tire-size-decoder/", "Tire Size Decoder: Read Any Sidewall Size",
                "Type the size from your sidewall and see what every number means, for cars, trucks, trailers, mowers, forklifts, tractors, bikes and aircraft."),
    "quote": ("/tire-quotes/", "Get Tire Quotes from Dealers",
              "Request quotes for forklift, farm, construction, commercial truck, RV and aircraft tires from dealers who carry and install them."),
    "request": ("/find-my-tire/", "Can't Find Your Tire? We'll Help",
                "Tell us what your tire goes on, and we'll show shopping options right away and help track it down."),
    "partners": ("/for-dealers/", "For Tire Dealers: Get Listed on Tires for Anything",
                 "Tire dealers: get in front of buyers looking for forklift, farm, construction, commercial and specialty tires."),
    "legal": ("/terms/", "Terms and Disclaimers | Tires for Anything", "Terms of use, safety disclaimers and affiliate disclosures for Tires for Anything."),
    "about": ("/about/", "About Tires for Anything", "Who runs Tires for Anything, how we make money, and how we keep our guides honest."),
    "privacy": ("/privacy/", "Privacy Policy | Tires for Anything", "What Tires for Anything collects, how quote requests are shared, and your choices."),
}
TOOLS = ("decoder", "quote", "request")

def path_of(v):
    return PAGES[v][0]

def fix_links(s):
    """#forklift -> /forklift-tires/ etc. Tool hashes (#decoder, #quote, #request) stay in-page; '/#x' becomes the real page."""
    def sub(m):
        pre, v = m.group(1), m.group(2)
        if v in PAGES and v not in TOOLS:
            return f'href="{path_of(v)}"'
        if v in TOOLS and pre == "/":
            return f'href="{path_of(v)}"'
        return m.group(0)
    return re.sub(r'href="(/?)#([a-z]+)"', sub, s)

NAV = ('<nav class="nav" aria-label="Site">\n'
       '      <a href="/">All tires</a>\n'
       '      <a href="/tire-size-decoder/">Size decoder</a>\n'
       '      <a href="/blog/">Blog</a>\n'
       '      <a href="/tire-quotes/">Get quotes</a>\n'
       '      <a href="/for-dealers/">For dealers</a>\n'
       '    </nav>')

def meta(title, desc, path, og_type="website", img="/og/default.png", extra=""):
    t, d = html.escape(title), html.escape(desc)
    robots = '<meta name="robots" content="noindex, nofollow">\n' if PREVIEW else ""
    return (f'{robots}<title>{t}</title>\n<meta name="description" content="{d}">\n'
            f'<link rel="canonical" href="{SITE}{path}">\n'
            f'<meta property="og:type" content="{og_type}">\n<meta property="og:site_name" content="Tires for Anything">\n'
            f'<meta property="og:title" content="{t}">\n<meta property="og:description" content="{d}">\n'
            f'<meta property="og:url" content="{SITE}{path}">\n<meta property="og:image" content="{SITE}{img}">\n'
            f'<meta property="og:image:width" content="1200">\n<meta property="og:image:height" content="630">\n'
            f'<meta name="twitter:card" content="summary_large_image">\n{extra}')

def build_site():
    src = open(os.path.join(ROOT, "src/site.html")).read()
    head_end = src.index("</head>")
    head = src[:head_end]
    # strip the source's own SEO tags; each page gets its own
    head = re.sub(r'<meta name="robots"[^>]*>\n?', "", head)
    head = re.sub(r'<title>.*?</title>\n?', "", head, flags=re.S)
    head = re.sub(r'<meta name="description"[^>]*>\n?', "", head)
    head = re.sub(r'<link rel="canonical"[^>]*>\n?', "", head)
    head = re.sub(r'<meta (property="og:[^"]*"|name="twitter:card")[^>]*>\n?', "", head)
    body_start = src.index("<body>", head_end)
    main_s, main_e = src.index("<main>"), src.index("</main>")
    top = src[body_start + len("<body>"):main_s]
    top = re.sub(r'<nav class="nav" aria-label="Site">.*?</nav>', NAV, top, flags=re.S)
    top = top.replace('class="brand" href="#home"', 'class="brand" href="/"')
    tail = src[main_e + len("</main>"):]
    sections = {}
    for m in re.finditer(r'(<!--[^\n]*-->\n)?<section class="view" id="v-([a-z]+)".*?</section>', src[main_s:main_e], re.S):
        sections[m.group(2)] = re.sub(r'^<!--[^\n]*-->\n', "", m.group(0))
    missing = set(PAGES) - set(sections)
    assert not missing, missing
    org = ('<script type="application/ld+json">' + json.dumps({"@context": "https://schema.org", "@type": "Organization",
           "name": "Tires for Anything", "url": SITE + "/", "logo": SITE + "/og/default.png"}) + "</script>\n")
    urls = []
    for v, (path, title, desc) in PAGES.items():
        own = sections[v].replace(f'id="v-{v}" data-view="{v}" hidden', f'id="v-{v}" data-view="{v}"', 1)
        parts = [own] + [sections[t] for t in TOOLS if t != v]
        crumbs = "" if v == "home" else ('<script type="application/ld+json">' + json.dumps({"@context": "https://schema.org", "@type": "BreadcrumbList",
            "itemListElement": [{"@type": "ListItem", "position": 1, "name": "Home", "item": SITE + "/"},
                                {"@type": "ListItem", "position": 2, "name": title.split(":")[0].split("|")[0].strip(), "item": SITE + path}]}) + "</script>\n")
        doc = (head + meta(title, desc, path, extra=(org if v == "home" else crumbs)) + "</head>\n"
               + f'<body data-page="{v}">' + top + "<main>\n\n" + "\n\n".join(parts) + "\n\n</main>" + tail)
        doc = fix_links(doc)
        out = os.path.join(ROOT, "public", path.strip("/"), "index.html") if path != "/" else os.path.join(ROOT, "public/index.html")
        os.makedirs(os.path.dirname(out), exist_ok=True)
        open(out, "w").write(doc)
        if v not in ("request",):
            urls.append(path)
    return urls

# ---------- blog ----------
GROUPS = [("small", "Small wheels"), ("power", "Powersports & racing"), ("road", "On the road"), ("heavy", "Heavy duty"), ("air", "Aircraft")]
CATS = [("small", "bicycles", "Bicycles & e-bikes"), ("small", "mobility", "Mobility & medical"), ("small", "toys", "Toys, RC & ride-ons"),
        ("small", "lawn", "Lawn & garden"), ("small", "motorsport", "Go-karts & karting"), ("power", "motorcycle", "Motorcycles"),
        ("power", "racing", "Race cars"), ("power", "atv", "ATV, UTV & golf"), ("road", "cars", "Passenger cars"),
        ("road", "trucks", "Light trucks & SUVs"), ("road", "trailer", "Trailers"), ("road", "rv", "RV & motorhome"),
        ("road", "vintage", "Vintage & antique"), ("heavy", "forklift", "Forklift & industrial"), ("heavy", "semi", "Semi & commercial"),
        ("heavy", "farm", "Farm & ag"), ("heavy", "construction", "Construction & OTR"), ("heavy", "military", "Military & specialty"),
        ("air", "aviation", "Aviation")]

def catbar():
    out = []
    for g, label in GROUPS:
        links = "".join(f'<a href="{path_of(i)}">{html.escape(n)}</a>' for gg, i, n in CATS if gg == g)
        out.append(f'<div class="cg"><span class="cgl">{html.escape(label)}</span>{links}</div>')
    return "".join(out)

FAVICON = "data:image/svg+xml,%3Csvg xmlns=%27http://www.w3.org/2000/svg%27 viewBox=%270 0 30 30%27%3E%3Ccircle cx=%2715%27 cy=%2715%27 r=%2713%27 fill=%27none%27 stroke=%27%2315191D%27 stroke-width=%275%27 stroke-dasharray=%273 2.2%27/%3E%3Ccircle cx=%2715%27 cy=%2715%27 r=%275.5%27 fill=%27%23E9B300%27/%3E%3C/svg%3E"

def blog_page(body, title, desc, path, jsonld="", img="/og/default.png", og_type="article"):
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
{meta(title, desc, path, og_type=og_type, img=img)}<link rel="icon" href="{FAVICON}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Big+Shoulders+Display:wght@600;800;900&family=Public+Sans:ital,wght@0,400;0,600;0,700;1,400&family=JetBrains+Mono:wght@500;700&display=swap">
<link rel="stylesheet" href="/blog/blog.css">
{jsonld}
<script src="/t.js" defer></script>
</head>
<body>
<header class="top">
  <div class="wrap">
    <a class="brand" href="/" aria-label="Tires for Anything home">
      <svg width="30" height="30" viewBox="0 0 30 30" aria-hidden="true"><circle cx="15" cy="15" r="13" fill="none" stroke="currentColor" stroke-width="5" stroke-dasharray="3 2.2"/><circle cx="15" cy="15" r="5.5" fill="var(--accent)"/></svg>
      <b>Tires for <span>Anything</span></b>
    </a>
    {NAV.replace('<a href="/blog/">Blog</a>', '<a href="/blog/" aria-current="page">Blog</a>')}
  </div>
</header>
<nav class="catbar" aria-label="Tire categories"><div class="wrap" id="catbar">{catbar()}</div></nav>
<div class="proto"><div class="wrap">Early preview. New guides and tire sizes are being added every week.</div></div>
<main>
{fix_links(body)}
</main>
<footer>
  <div class="wrap">
    <div><b style="font-family:var(--display);text-transform:uppercase;font-size:1.1rem;color:var(--ink)">Tires for Anything</b> · tiresforanything.com</div>
    <div class="row" style="gap:16px"><a href="/blog/">Blog</a><a href="/about/">About</a><a href="/privacy/">Privacy policy</a><a href="/terms/">Terms and disclaimers</a><a href="/for-dealers/">For dealers</a><a href="/find-my-tire/">Can't find your tire?</a></div>
    <p><b>Safety notice:</b> Information on this site is general and educational. It is not professional, mechanical or aviation advice, and it doesn't replace your manufacturer's specifications or a qualified technician. You are responsible for verifying any tire before you buy, install or use it. <a href="/terms/">Read the full terms and disclaimers</a>.</p>
    <p>Some links on this site are affiliate links. If you buy through them, we may earn a commission at no extra cost to you. Featured dealers pay for placement, and they're always labeled. We never earn commissions on non-standard fitments. As an Amazon Associate I earn from qualifying purchases.</p>
    <p>Product and company names are trademarks of their owners, used for identification only. Tires for Anything is not affiliated with any manufacturer named on this site.</p>
  </div>
</footer>
</body>
</html>
"""

BLOG = [  # slug, tab title, Google description
    ("tire-balancing-beads-vs-wheel-weights", "Balance Beads vs. Wheel Weights: What to Use and When | Tires for Anything",
     "When does tire balancing matter? Balance beads vs. stick-on vs. clip-on wheel weights for motorcycles, cars, trucks, semis, RVs and trailers."),
    ("tire-wheel-rim-definitions", "Tire vs. Wheel vs. Rim (Plus Casters & Flat-Proof Tires) | Tires for Anything",
     "What's the difference between a tire, wheel and rim? Plain-English definitions of casters, solid, press-on, foam-filled, liquid-filled and run-flat tires."),
]

def build_blog():
    urls = ["/blog/"]
    b = os.path.join(ROOT, "src/blog")
    idx = open(os.path.join(b, "index.body.html")).read()
    open(os.path.join(ROOT, "public/blog/index.html"), "w").write(blog_page(idx, "Blog | Tires for Anything",
        "Plain-English tire how-tos and buying advice for anything that rolls, from wheelbarrows and forklifts to tractors and aircraft.", "/blog/", og_type="website"))
    for slug, title, desc in BLOG:
        body = open(os.path.join(b, slug + ".body.html")).read()
        jl = open(os.path.join(b, slug + ".jsonld")).read()
        img = f"/og/{slug}.png" if os.path.exists(os.path.join(ROOT, "public/og", slug + ".png")) else "/og/default.png"
        open(os.path.join(ROOT, "public/blog", slug + ".html"), "w").write(blog_page(body, title, desc, f"/blog/{slug}", jl, img))
        urls.append(f"/blog/{slug}")
    return urls

def sitemap(urls):
    rows = "".join(f"  <url><loc>{SITE}{u}</loc><lastmod>{TODAY}</lastmod></url>\n" for u in urls)
    open(os.path.join(ROOT, "public/sitemap.xml"), "w").write(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + rows + "</urlset>\n")

if __name__ == "__main__":
    u = build_site() + build_blog()
    sitemap(u)
    print(f"built {len(u)} sitemap pages, PREVIEW={PREVIEW}")
