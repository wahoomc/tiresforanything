#!/usr/bin/env python3
"""Build the Tires for Anything site.

Source files (edit these):
  src/site.html          every page's sections, styles and script, in one file
  src/blog/*.body.html   blog post bodies; *.jsonld = structured data for each post
Output (generated, committed, served by Cloudflare):
  public/index.html, public/<page>/index.html, public/blog/*.html, public/sitemap.xml

Run:  python3 tools/build_site.py          (then: node tools/prerender.mjs)
PREVIEW = False keeps every page out of Google (noindex). Flip to False at launch,
together with public/robots.txt and public/_headers.
"""
import datetime, hashlib, html, json, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = "https://tiresforanything.com"
PREVIEW = False
TODAY = datetime.date.today().isoformat()

# Blog publish dates live in src/schedule.json. The worker (src/worker.js) reads the same file and
# hides any post whose date hasn't come yet on tiresforanything.com. The preview shows everything.
SCHEDULE = {k: v for k, v in json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../src/schedule.json"))).items() if not k.startswith("_")}

for _s, _d in SCHEDULE.items():
    assert len(_d) == 16 and "08:00" <= _d[11:] <= "23:59", f"schedule.json: {_s} needs a time between 08:00 and 23:59 ({_d})"

def pub_of(slug):
    return SCHEDULE.get(slug, "2000-01-01")

def long_date(d):
    y, m, dd = map(int, d[:10].split("-"))
    return datetime.date(y, m, dd).strftime("%B ") + str(dd) + f", {y}"

def pub_stamp(d):
    """Schedule value -> (ISO time with Indiana UTC offset, 'November 12, 2026 at 4:47 p.m. ET')."""
    from zoneinfo import ZoneInfo
    t = d[11:16] if len(d) > 10 else "12:00"
    hh, mm = map(int, t.split(":"))
    dt = datetime.datetime.fromisoformat(d[:10]).replace(hour=hh, minute=mm, tzinfo=ZoneInfo("America/Indiana/Indianapolis"))
    h12 = hh % 12 or 12
    return dt.isoformat(), f"{long_date(d)} at {h12}:{mm:02d} {'a.m.' if hh < 12 else 'p.m.'} ET"

POSTCARD = re.compile(r'    <a class="postcard" href="/blog/([a-z0-9-]+)"[^>]*>.*?</a>\n', re.S)

def sorted_postcards(idx):
    """Blog index cards, newest publish date first, each tagged with data-pub."""
    cards = [(m.group(1), m.group(0)) for m in POSTCARD.finditer(idx)]
    cards.sort(key=lambda c: pub_of(c[0]), reverse=True)
    return [(slug, re.sub(r'(<a class="postcard" href="/blog/[a-z0-9-]+")[^>]*>', rf'\1 data-pub="{pub_of(slug)}">', block, count=1)) for slug, block in cards]

def home_cards():
    idx = open(os.path.join(ROOT, "src/blog/index.body.html")).read()
    out = []
    for slug, block in sorted_postcards(idx):
        eb = re.search(r'<span class="eyebrow">(.*?)</span>', block).group(1).split(" · ")[0]
        t = re.search(r"<b>(.*?)</b>", block, re.S).group(1)
        d = re.search(r"<p>(.*?)</p>", block, re.S).group(1)
        out.append(f'\n    <a class="cat live" href="/blog/{slug}" data-pub="{pub_of(slug)}" style="padding:18px">\n'
                   f'      <span class="eyebrow">{eb}</span>\n      <b style="font-size:1.5rem">{t}</b>\n      <small>{d}</small>\n    </a>')
    return "".join(out) + "\n    "

def tag_blog_li(s):
    """Mark list items that only point at one blog post, so the worker can drop them before that post is out."""
    return re.sub(r'<li>(\s*<a href="/blog/([a-z0-9-]+)")', lambda m: f'<li data-pub="{pub_of(m.group(2))}">{m.group(1)}', s)
PAGE_HASH = {}  # path -> hash of the page's own content, for sitemap dates

# view id: (path, browser-tab title, Google description)
PAGES = {
    "home": ("/", "Tires for Anything: The Right Tire for Anything That Rolls",
             "Plain-English tire guides, a size decoder and shopping links for anything that rolls: cars, trucks, trailers, mowers, forklifts, tractors, bikes and more."),
    "cars": ("/passenger-car-tires/", "Passenger Car Tires: Sizes, Types and How to Choose",
             "How to read a car tire size, pick all-season, all-weather, winter or performance tires, and shop the right size."),
    "trucks": ("/light-truck-suv-tires/", "Light Truck and SUV Tires: LT vs. P, Load Range, Tread",
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
            "ATV, UTV and golf cart tire sizes explained, with common sizes, lift kit sizing, and tires or full wheel-and-tire sets you can order online."),
    "rv": ("/rv-motorhome-tires/", "RV and Motorhome Tires: Sizes, Age and Load",
           "Class A, B and C motorhome tire sizes, how old is too old, load and pressure, and where to get them installed."),
    "mobility": ("/wheelchair-mobility-scooter-tires/", "Wheelchair and Mobility Scooter Tires",
                 "Wheelchair, power chair and mobility scooter tire sizes, solid vs. pneumatic vs. foam-filled, caster wheels, and replacements you can order online."),
    "casters": ("/caster-wheels/", "Caster Wheels for Office Chairs, Carts and Tool Chests",
                "How to pick replacement casters for office chairs, utility carts, rolling shelves, tool chests and furniture: stem vs plate, load, wheel size and floor type."),
    "toys": ("/rc-toy-ride-on-tires/", "RC Car, RC Plane, Ride-On and Scooter Tires and Wheels",
             "Tire and wheel sizes for RC cars and trucks, RC airplanes, kids' ride-on cars, kick and electric scooters, hoverboards and skateboards."),
    "motorsport": ("/go-kart-tires/", "Go-Kart Tires: Sizes and Compounds",
                   "Go-kart tire sizes for sprint, cadet, yard and rental karts, how compound and size affect grip, and replacement tires you can order online."),
    "racing": ("/race-car-tires/", "Race Car Tires: Autocross, Track Day, Drag and Dirt",
               "Tires for autocross, track days, road racing, drag racing and dirt oval, and how class rules decide what you can run."),
    "bicycles": ("/bike-tires/", "Bike Tire Sizes: Road, Gravel, Mountain and Kids",
                 "Road, gravel, mountain, fat and kids' bike tire sizes, including 700c, 29er, 20 inch and the fraction sizes that don't swap."),
    "vintage": ("/vintage-antique-tires/", "Vintage and Antique Car Tires: Model T to Muscle Cars",
                "Vintage and antique tire sizes from the Model T to muscle cars, beaded-edge clinchers, and specialty suppliers."),
    "military": ("/military-truck-tires/", "Military Truck Tires: Humvee, Deuce and a Half, Surplus",
                 "Tire sizes for surplus military trucks like the Humvee and M35, run-flat inserts, and where to find them."),
    "decoder": ("/tire-size-decoder/", "Tire Size Decoder: Read Any Sidewall Size",
                "Type the size from your sidewall and see what every number means, for cars, trucks, trailers, mowers, forklifts, tractors, bikes and aircraft."),
    "quote": ("/tire-quotes/", "Buying Tires for Big Equipment and Aircraft",
              "How forklift, farm, construction, semi and aircraft tires are usually bought, and where to start."),
    "request": ("/find-my-tire/", "Can't Find Your Tire? We'll Help",
                "Tell us what your tire goes on, and we'll show shopping options right away and help track it down."),
    "partners": ("/for-dealers/", "For Tire Dealers: Get Listed on Tires for Anything",
                 "Tire dealers: get in front of buyers looking for forklift, farm, construction, commercial and specialty tires."),
    "legal": ("/terms/", "Terms and Disclaimers | Tires for Anything", "Terms of use, safety disclaimers and affiliate disclosures for Tires for Anything."),
    "about": ("/about/", "About Tires for Anything", "Who runs Tires for Anything, the hands-on tire experience behind the guides, how the site makes money, and how we keep the advice honest."),
    "privacy": ("/privacy/", "Privacy Policy | Tires for Anything", "What Tires for Anything collects, how analytics and tire requests are handled, and the choices you have about your information."),
    "contact": ("/contact/", "Contact Tires for Anything", "How to reach Tires for Anything about a tire size, a correction, or a dealer listing."),
    "disclosure": ("/affiliate-disclosure/", "Affiliate Disclosure | Tires for Anything", "How Tires for Anything earns commissions from retailer links, and what that does and doesn't change."),
}
TOOLS = ("decoder", "quote", "request")

# Blog guides linked from each category page ("Related guides" box). Keep each list to the posts that genuinely help.
POSTS = {
    "press-on-forklift-tires": "Press-on forklift tires: sizes, types and when to replace",
    "tire-date-code": "How old is my tire? Reading the DOT date code",
    "st-vs-lt-trailer-tires": "Trailer tires: ST vs. LT vs. car tires",
    "winter-tires-vs-all-season": "Winter tires vs. all-season: do you need them?",
    "how-to-read-tire-size": "How to read a tire size, any tire, in 5 minutes",
    "tire-sealant-vs-plug-vs-patch": "Leak stops: thorn-proofing, Slime, and plug vs. patch",
    "tire-wheel-rim-definitions": "Tire vs. wheel vs. rim, plus casters and flat-proof tires",
    "tire-balancing-beads-vs-wheel-weights": "Balance beads vs. wheel weights: what to use and when",
    "how-to-replace-office-chair-casters": "How to replace office chair casters (and cart casters)",
    "cushion-vs-pneumatic-forklift-tires": "Cushion vs. pneumatic forklift tires: which do you need?",
    "kids-bike-tire-sizes": "Kids' bike tire sizes, 12 to 24 inch, explained",
    "hand-truck-wheelbarrow-tire-replacement": "Wagon, wheelbarrow and hand truck tires: flat-free vs. air",
    "tire-pressure-light-cold-weather": "Why is my tire pressure light on when it's cold?",
    "snowblower-tires-chains": "Snowblower tires and chains: sizes, treads and when to upgrade",
    "portable-tire-inflator-guide": "How to pick a portable tire inflator",
    "tire-sidewall-bulge": "Is a sidewall bulge dangerous?",
    "cdl-pre-trip-tire-inspection": "CDL pre-trip tire inspection: what to check",
}
RELATED = {
    "trailer": ["st-vs-lt-trailer-tires", "tire-date-code", "tire-balancing-beads-vs-wheel-weights", "tire-wheel-rim-definitions"],
    "motorcycle": ["tire-date-code", "tire-balancing-beads-vs-wheel-weights"],
    "cars": ["winter-tires-vs-all-season", "tire-pressure-light-cold-weather", "tire-sidewall-bulge", "how-to-read-tire-size"],
    "trucks": ["winter-tires-vs-all-season", "tire-sidewall-bulge", "how-to-read-tire-size", "tire-balancing-beads-vs-wheel-weights"],
    "rv": ["tire-date-code", "portable-tire-inflator-guide", "cdl-pre-trip-tire-inspection", "tire-balancing-beads-vs-wheel-weights"],
    "semi": ["cdl-pre-trip-tire-inspection", "how-to-read-tire-size", "tire-balancing-beads-vs-wheel-weights"],
    "atv": ["tire-balancing-beads-vs-wheel-weights", "tire-wheel-rim-definitions", "tire-sealant-vs-plug-vs-patch"],
    "lawn": ["hand-truck-wheelbarrow-tire-replacement", "snowblower-tires-chains", "tire-sealant-vs-plug-vs-patch", "tire-wheel-rim-definitions"],
    "casters": ["how-to-replace-office-chair-casters", "tire-wheel-rim-definitions"],
    "mobility": ["tire-wheel-rim-definitions", "how-to-replace-office-chair-casters", "tire-sealant-vs-plug-vs-patch"],
    "forklift": ["press-on-forklift-tires", "cushion-vs-pneumatic-forklift-tires", "tire-wheel-rim-definitions"],
    "construction": ["tire-wheel-rim-definitions"],
    "farm": ["tire-wheel-rim-definitions"],
    "military": ["tire-date-code", "tire-wheel-rim-definitions"],
    "bicycles": ["kids-bike-tire-sizes", "tire-sealant-vs-plug-vs-patch"],
    "decoder": ["how-to-read-tire-size", "tire-wheel-rim-definitions", "tire-balancing-beads-vs-wheel-weights"],
}

def related_box(v):
    slugs = RELATED.get(v)
    if not slugs:
        return ""
    links = "".join(f'<li data-pub="{pub_of(s)}"><a href="/blog/{s}">{html.escape(POSTS[s])}</a></li>' for s in slugs)
    return ('\n  <div class="wrap stack"><div class="callout"><b>Related guides</b>'
            f'<ul class="clean" style="margin-top:8px">{links}</ul></div></div>\n')

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
       '      <a href="/find-my-tire/">Find my tire</a>\n'
       '      <a href="/for-dealers/">For dealers</a>\n'
       '    </nav>')

def meta(title, desc, path, og_type="website", img="/og/default.png", extra="", noindex=False):
    t, d = html.escape(title), html.escape(desc)
    robots = '<meta name="robots" content="noindex, nofollow">\n' if (PREVIEW or noindex) else ""
    return (f'{robots}<title>{t}</title>\n<meta name="description" content="{d}">\n'
            f'<link rel="canonical" href="{SITE}{path}">\n'
            f'<meta property="og:type" content="{og_type}">\n<meta property="og:site_name" content="Tires for Anything">\n'
            f'<meta property="og:title" content="{t}">\n<meta property="og:description" content="{d}">\n'
            f'<meta property="og:url" content="{SITE}{path}">\n<meta property="og:image" content="{SITE}{img}">\n'
            f'<meta property="og:image:width" content="1200">\n<meta property="og:image:height" content="630">\n'
            f'<meta name="twitter:card" content="summary_large_image">\n{extra}')

def build_site():
    src = open(os.path.join(ROOT, "src/site.html")).read().replace("<!--BLOGCARDS-->", home_cards())
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
           "name": "Tires for Anything", "url": SITE + "/", "logo": SITE + "/og/default.png"}) + "</script>\n"
           + '<script type="application/ld+json">' + json.dumps({"@context": "https://schema.org", "@type": "WebSite",
           "name": "Tires for Anything", "url": SITE + "/"}) + "</script>\n")
    urls = []
    for v, (path, title, desc) in PAGES.items():
        own = sections[v].replace(f'id="v-{v}" data-view="{v}" hidden', f'id="v-{v}" data-view="{v}"', 1)
        page_ld = ""
        if v == "decoder":
            # How-to, popular sizes and FAQ live only on the decoder's own page (not in the hidden copy on other pages).
            guide = open(os.path.join(ROOT, "src/decoder-guide.html")).read()
            i = own.rfind("</section>")
            own = own[:i] + guide + own[i:]
            faqs = re.findall(r"<details><summary>(.*?)</summary><p>(.*?)</p></details>", guide)
            page_ld = ('<script type="application/ld+json">' + json.dumps({"@context": "https://schema.org", "@type": "FAQPage",
                "mainEntity": [{"@type": "Question", "name": html.unescape(q), "acceptedAnswer": {"@type": "Answer", "text": html.unescape(re.sub("<[^>]+>", "", a))}} for q, a in faqs]}) + "</script>\n")
        rb = related_box(v)
        if rb:
            i = own.rfind("</section>")
            own = own[:i] + rb + own[i:]
        PAGE_HASH[path] = hashlib.sha1(own.encode()).hexdigest()
        parts = [own] + [sections[t] for t in TOOLS if t != v]
        crumbs = "" if v == "home" else ('<script type="application/ld+json">' + json.dumps({"@context": "https://schema.org", "@type": "BreadcrumbList",
            "itemListElement": [{"@type": "ListItem", "position": 1, "name": "Home", "item": SITE + "/"},
                                {"@type": "ListItem", "position": 2, "name": title.split(":")[0].split("|")[0].strip(), "item": SITE + path}]}) + "</script>\n")
        doc = (head + meta(title, desc, path, extra=(org if v == "home" else crumbs + page_ld), noindex=(v == "quote")) + "</head>\n"
               + f'<body data-page="{v}">' + top + "<main>\n\n" + "\n\n".join(parts) + "\n\n</main>" + tail)
        doc = tag_blog_li(fix_links(doc))
        out = os.path.join(ROOT, "public", path.strip("/"), "index.html") if path != "/" else os.path.join(ROOT, "public/index.html")
        os.makedirs(os.path.dirname(out), exist_ok=True)
        open(out, "w").write(doc)
        if v not in ("request", "quote"):
            urls.append(path)
    return urls

# ---------- blog ----------
GROUPS = [("small", "Small wheels"), ("power", "Powersports & racing"), ("road", "On the road"), ("heavy", "Heavy duty"), ("air", "Aircraft")]
CATS = [("small", "bicycles", "Bicycles & e-bikes"), ("small", "mobility", "Mobility & medical"), ("small", "casters", "Casters & carts"), ("small", "toys", "Toys, RC & ride-ons"),
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
<script async src="https://www.googletagmanager.com/gtag/js?id=G-PHZB9G6M10"></script>
<script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}gtag("js",new Date());gtag("config","G-PHZB9G6M10");</script>
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
<main>
{fix_links(body)}
</main>
<footer>
  <div class="wrap">
    <div><b style="font-family:var(--display);text-transform:uppercase;font-size:1.1rem;color:var(--ink)">Tires for Anything</b> · tiresforanything.com</div>
    <div class="row" style="gap:16px"><a href="/blog/">Blog</a><a href="/about/">About</a><a href="/privacy/">Privacy policy</a><a href="/terms/">Terms and disclaimers</a><a href="/affiliate-disclosure/">Affiliate disclosure</a><a href="/contact/">Contact</a><a href="/for-dealers/">For dealers</a><a href="/find-my-tire/">Can't find your tire?</a></div>
    <p><b>Safety notice:</b> Information on this site is general and educational. It is not professional, mechanical or aviation advice, and it doesn't replace your manufacturer's specifications or a qualified technician. You are responsible for verifying any tire before you buy, install or use it. <a href="/terms/">Read the full terms and disclaimers</a>.</p>
    <p>Some links on this site are affiliate links. If you buy through them, we may earn a commission at no extra cost to you. Featured dealers pay for placement, and they're always labeled. We never earn commissions on non-standard fitments. As an Amazon Associate I earn from qualifying purchases.</p>
    <p>Product and company names are trademarks of their owners, used for identification only. Tires for Anything is not affiliated with any manufacturer named on this site.</p>
  </div>
</footer>
</body>
</html>
"""

BLOG = [  # slug, tab title, Google description
    ("press-on-forklift-tires", "Press-On Forklift Tires: Sizes, Types and When to Replace",
     "How to read press-on forklift tire sizes, pick between rubber, non-marking and polyurethane, spot when they're worn out, and get them replaced on site."),
    ("tire-date-code", "How Old Is My Tire? How to Read the DOT Date Code",
     "Find the four-digit date code on any tire, read it in seconds, and learn how old is too old for cars, trailers, RVs and motorcycles."),
    ("st-vs-lt-trailer-tires", "ST vs. LT vs. Car Tires on a Trailer: What to Use and Why",
     "Why trailers use ST tires, when LT tires make sense, why car tires are a bad idea, plus speed ratings, load range and the pressure trailer tires need."),
    ("winter-tires-vs-all-season", "Winter Tires vs. All-Season: Do You Really Need Them?",
     "All-season, all-weather or winter tires? What the snowflake symbol means, when winter tires are worth it, and how to make switching each season easier."),
    ("how-to-read-tire-size", "How to Read a Tire Size: Any Tire in 5 Minutes",
     "Read the numbers on any tire sidewall: cars, trucks, trailers, semis, mowers, ATVs, forklifts, motorcycles and bikes. One page, plain English."),
    ("tire-sealant-vs-plug-vs-patch", "Tire Sealant vs. Plug vs. Patch: What Actually Fixes a Flat",
     "Stop thorn flats before they start, know when Slime or Fix-a-Flat makes sense, why tire shops hate them, and whether a sealed tire can still be repaired."),
    ("how-to-replace-office-chair-casters", "How to Replace Office Chair Casters (and Cart Casters)",
     "Swap office chair casters in ten minutes, pick wheels that won't scratch hardwood, and size plate or stem casters for carts, shelves and tool chests."),
    ("tire-balancing-beads-vs-wheel-weights", "Balance Beads vs. Wheel Weights: What to Use and When",
     "When does tire balancing matter? Balance beads vs. stick-on vs. clip-on wheel weights for motorcycles, cars, trucks, semis, RVs and trailers."),
    ("tire-wheel-rim-definitions", "Tire vs. Wheel vs. Rim, Plus Casters and Flat-Proof Tires",
     "What's the difference between a tire, wheel and rim? Plain-English definitions of casters, solid, press-on, foam-filled, liquid-filled and run-flat tires."),
    ("cushion-vs-pneumatic-forklift-tires", "Cushion vs. Pneumatic Forklift Tires: Which Do You Need?",
     "Cushion or pneumatic forklift tires? The difference, where each one works, air vs. solid pneumatic, and why you usually can't switch a truck from one to the other."),
    ("kids-bike-tire-sizes", "Kids' Bike Tire Sizes: 12, 16, 20 and 24 Inch Explained",
     "Find the right replacement tire or tube for a kid's bike. Sizes by age, the decimal vs. fraction trap that trips everybody up, and valve types."),
    ("hand-truck-wheelbarrow-tire-replacement", "Hand Truck, Wagon and Wheelbarrow Tires: How to Pick the Right Wheel",
     "Replace a hand truck, wagon or wheelbarrow tire the easy way. Read the size, measure the axle and hub, and choose flat-free or air-filled."),
    ("tire-pressure-light-cold-weather", "Tire Pressure Light On in Cold Weather? Here's Why",
     "Cold mornings drop tire pressure about 1 psi per 10°F and trip the TPMS light. What it means, how to fix it in five minutes, and when it's something else."),
    ("snowblower-tires-chains", "Snowblower Tires and Chains: Sizes and Upgrades",
     "Find your snowblower tire size, pick the right tread, and decide if chains are worth it. Common sizes like 13x4.00-6, 15x5.00-6 and 4.80-8 explained."),
    ("portable-tire-inflator-guide", "How to Pick a Portable Tire Inflator (Buying Guide)",
     "Cordless, 12V or garage plug-in? What PSI, airflow and duty cycle mean, and which kind of tire inflator fits cars, trucks, trailers, bikes and mowers."),
    ("tire-sidewall-bulge", "Tire Sidewall Bulge: Is It Safe to Drive On?",
     "A bubble on your tire's sidewall means the inside is damaged and it can't be repaired. How to tell a bulge from a normal dent, what causes it, and what to do now."),
    ("cdl-pre-trip-tire-inspection", "CDL Pre-Trip Tire Inspection: What to Check",
     "The tire part of a CDL pre-trip, in plain English: tread depth (4/32 steer, 2/32 others), inflation, cuts, duals, valve stems and the rule on recaps for bus front tires."),
]

def build_blog():
    urls = ["/blog/"]
    b = os.path.join(ROOT, "src/blog")
    idx = open(os.path.join(b, "index.body.html")).read()
    cards = sorted_postcards(idx)
    first = POSTCARD.search(idx).start()
    idx = POSTCARD.sub("", idx)
    idx = idx[:first] + "".join(c for _, c in cards) + idx[first:]
    PAGE_HASH["/blog/"] = hashlib.sha1(idx.encode()).hexdigest()
    open(os.path.join(ROOT, "public/blog/index.html"), "w").write(blog_page(idx, "Blog | Tires for Anything",
        "Plain-English tire how-tos and buying advice for anything that rolls, from wheelbarrows and forklifts to tractors and aircraft.", "/blog/", og_type="website"))
    for slug, title, desc in BLOG:
        body = open(os.path.join(b, slug + ".body.html")).read()
        jl = open(os.path.join(b, slug + ".jsonld")).read()
        iso, shown = pub_stamp(pub_of(slug))  # every post shows the exact time it went live
        m = re.search(r'"dateModified": *"([^"]+)"', jl)
        mod = m.group(1) if m and m.group(1)[:10] > iso[:10] else iso
        jl = re.sub(r'"datePublished": *"[^"]+"', f'"datePublished": "{iso}"', jl)
        jl = re.sub(r'"dateModified": *"[^"]+"', f'"dateModified": "{mod}"', jl)
        body = re.sub(r'<span>(?:Updated|Published) <time datetime="[^"]+">[^<]*</time></span>',
                      f'<span>Published <time datetime="{iso}">{shown}</time></span>', body, count=1)
        body = tag_blog_li(body)
        img = f"/og/{slug}.png" if os.path.exists(os.path.join(ROOT, "public/og", slug + ".png")) else "/og/default.png"
        open(os.path.join(ROOT, "public/blog", slug + ".html"), "w").write(blog_page(body, title, desc, f"/blog/{slug}", jl, img))
        PAGE_HASH[f"/blog/{slug}"] = hashlib.sha1((body + title + desc).encode()).hexdigest()
        urls.append(f"/blog/{slug}")
    return urls

def sitemap(urls):
    # tools/page-dates.json remembers each page's last content change, so dates only move when a page really changes.
    f = os.path.join(ROOT, "tools/page-dates.json")
    known = json.load(open(f)) if os.path.exists(f) else {}
    for u in urls:
        hsh = PAGE_HASH.get(u, "")
        if u not in known or known[u][0] != hsh:
            known[u] = [hsh, TODAY]
        if u.startswith("/blog/") and pub_of(u[6:])[:10] > known[u][1]:
            known[u][1] = pub_of(u[6:])[:10]
    json.dump(known, open(f, "w"), indent=1, sort_keys=True)
    rows = "".join(f"  <url><loc>{SITE}{u}</loc><lastmod>{known[u][1]}</lastmod></url>\n" for u in urls)
    open(os.path.join(ROOT, "public/sitemap.xml"), "w").write(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + rows + "</urlset>\n")

if __name__ == "__main__":
    u = build_site() + build_blog()
    sitemap(u)
    print(f"built {len(u)} sitemap pages, PREVIEW={PREVIEW}")
