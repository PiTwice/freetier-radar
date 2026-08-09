#!/usr/bin/env python3
"""Build FreeTier Radar from data/tools.json.

Does four things, all idempotent — run it after every data edit:

1. Embeds tools.json into index.html (the tools-data script block).
2. Syncs base_url / repo_url / newsletter_url from meta into index.html.
3. Generates one SEO page per tool into tools/<id>.html.
4. Generates sitemap.xml and robots.txt.

    python3 scripts/build.py
"""
import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "tools.json"
INDEX = ROOT / "index.html"
TOOLS_DIR = ROOT / "tools"

CATEGORIES = {
    "hosting": "Hosting & PaaS",
    "database": "Databases",
    "auth": "Auth",
    "email": "Email",
    "monitoring": "Monitoring",
    "cicd": "CI/CD",
    "storage": "Storage & Media",
}

PAGE_CSS = """
:root{--bg:#0F172A;--bg-deep:#0B1120;--surface:#16203A;--muted:#272F42;--border:#2E3A57;
--border-strong:#475569;--fg:#F8FAFC;--fg-2:#B6C2D9;--fg-3:#7E8CA8;--accent:#22C55E;
--accent-bg:rgba(34,197,94,.12);--warn:#F59E0B;--warn-bg:rgba(245,158,11,.12);--radius:14px}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--fg);font-family:'Inter',system-ui,sans-serif;font-size:16px;line-height:1.65;-webkit-font-smoothing:antialiased}
a{color:var(--accent);text-decoration:none}a:hover{text-decoration:underline}
.container{max-width:760px;margin:0 auto;padding:0 24px}
header.site{position:sticky;top:0;z-index:100;background:rgba(11,17,32,.85);backdrop-filter:blur(12px);border-bottom:1px solid var(--border)}
.nav{display:flex;align-items:center;justify-content:space-between;height:60px;max-width:1152px;margin:0 auto;padding:0 24px}
.logo{display:flex;align-items:center;gap:10px;font-weight:800;font-size:17px;color:var(--fg)}
.logo:hover{text-decoration:none}
.crumbs{font-size:13px;color:var(--fg-3);margin:32px 0 8px}
h1{font-size:clamp(24px,4.5vw,34px);font-weight:800;letter-spacing:-.02em;line-height:1.2}
.badges{display:flex;gap:8px;flex-wrap:wrap;margin:16px 0}
.badge{display:inline-flex;align-items:center;gap:5px;font-size:12.5px;font-weight:600;padding:5px 12px;border-radius:6px}
.badge.ok{color:var(--accent);background:var(--accent-bg)}
.badge.warn{color:var(--warn);background:var(--warn-bg)}
.badge.cat{color:var(--fg-3);background:var(--muted)}
p.lead{color:var(--fg-2);font-size:17px}
h2{font-size:20px;font-weight:700;margin:36px 0 12px;letter-spacing:-.01em}
ul.clean{list-style:none;display:flex;flex-direction:column;gap:10px}
ul.clean li{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:12px 16px;font-size:14.5px;color:var(--fg-2);display:flex;gap:10px;align-items:flex-start}
ul.clean li::before{content:"✓";color:var(--accent);font-weight:700;flex:none}
ul.clean.traps li::before{content:"⚠";color:var(--warn)}
.meta-line{font-size:13.5px;color:var(--fg-3);border-top:1px solid var(--border);margin-top:36px;padding-top:16px}
.related{display:flex;flex-wrap:wrap;gap:8px;margin-top:8px}
.related a{border:1px solid var(--border);border-radius:999px;padding:8px 16px;font-size:14px;color:var(--fg-2);min-height:44px;display:inline-flex;align-items:center}
.related a:hover{color:var(--accent);border-color:var(--accent);text-decoration:none}
.cta{margin:40px 0;background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);padding:24px;text-align:center}
.cta a.btn{display:inline-flex;align-items:center;min-height:48px;padding:10px 24px;border-radius:999px;background:var(--accent);color:#06220F;font-weight:600;margin-top:12px}
.cta a.btn:hover{text-decoration:none;background:#33D46E}
footer.site{border-top:1px solid var(--border);margin-top:48px;padding:32px 0;color:var(--fg-3);font-size:13px;text-align:center}
"""

PAGE_TMPL = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{name} free tier in {year}: real limits, traps & verification — FreeTier Radar</title>
<meta name="description" content="{meta_desc}">
<link rel="canonical" href="{canonical}">
<meta property="og:title" content="{name} free tier in {year}: verified limits and traps">
<meta property="og:description" content="{meta_desc}">
<meta property="og:type" content="article">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<script type="application/ld+json">{jsonld}</script>
<style>{css}</style>
</head>
<body>
<header class="site"><div class="nav">
  <a class="logo" href="../index.html">
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#22C55E" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6" opacity=".55"/><circle cx="12" cy="12" r="2" fill="#22C55E" stroke="none"/><line x1="12" y1="12" x2="19" y2="5"/></svg>
    FreeTier&nbsp;Radar
  </a>
  <nav style="font-size:14px"><a href="../index.html#tools" style="color:var(--fg-2)">← All free tiers</a></nav>
</div></header>
<main class="container">
  <p class="crumbs"><a href="../index.html">Home</a> / <a href="../index.html#tools">{cat_label}</a> / {name}</p>
  <h1>{name} free tier: what you actually get</h1>
  <div class="badges">
    <span class="badge cat">{cat_label}</span>
    {card_badge}
    <span class="badge ok">Verified {verified}</span>
  </div>
  <p class="lead">{summary}</p>

  <h2>The limits, verified</h2>
  <ul class="clean">{limits_html}</ul>

  <h2>Watch out — the fine print</h2>
  <ul class="clean traps">{traps_html}</ul>

  <h2>Should you build on it?</h2>
  <p style="color:var(--fg-2)">{verdict}</p>

  <div class="cta">
    <strong>Free tiers change — and usually not in your favor.</strong>
    <p style="color:var(--fg-2);font-size:14.5px;margin-top:6px">Get one short email when {name} (or any tool we track) changes or kills its free tier.</p>
    <a class="btn" href="{newsletter_url}" target="_blank" rel="noopener">Get change alerts</a>
  </div>

  <h2>Related free tiers</h2>
  <div class="related">{related_html}</div>

  <p class="meta-line">Verified {verified} against <a href="{pricing_url}" target="_blank" rel="noopener nofollow">the official pricing page</a>. Additional context: <a href="{source}" target="_blank" rel="noopener nofollow">source</a>. Found an error? <a href="{repo_url}" target="_blank" rel="noopener">Open an issue</a> — corrections ship within a day.</p>
</main>
<footer class="site"><div class="container">© {year} FreeTier Radar · Limits change without notice — always confirm on the provider's official pricing page. Not affiliated with {name}.</div></footer>
<!-- Analytics: create a free account at goatcounter.com, then uncomment and set your code.
<script data-goatcounter="https://YOURCODE.goatcounter.com/count" async src="//gc.zgo.at/count.js"></script>
-->
</body>
</html>
"""


def esc(s: str) -> str:
    return html.escape(str(s), quote=True)


def verdict_for(tool: dict) -> str:
    n_traps = len(tool.get("traps", []))
    name = tool["name"]
    if n_traps == 0:
        return (
            f"{name} currently has one of the cleaner free tiers in its category — "
            "no major traps on record. As always, set a calendar note to re-check the limits before launch."
        )
    if n_traps == 1:
        return (
            f"{name} is a solid free choice as long as the single caveat above fits your use case. "
            "If it does, there is little reason to look elsewhere in this category."
        )
    return (
        f"{name} can absolutely be used for free, but go in with eyes open: the {n_traps} caveats above are "
        "the exact things that catch people in production. If your project can tolerate them, it's a fine pick; "
        "if not, check the related free tiers below for an alternative."
    )


def jsonld_for(tool: dict, canonical: str) -> str:
    card = "No credit card is required to sign up." if not tool["card_required"] else "A credit card is required to sign up."
    faq = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {
                "@type": "Question",
                "name": f"Does {tool['name']} have a free tier?",
                "acceptedAnswer": {"@type": "Answer", "text": f"Yes. {tool['summary']} Key limits: {'; '.join(tool['limits'])}."},
            },
            {
                "@type": "Question",
                "name": f"Does the {tool['name']} free tier require a credit card?",
                "acceptedAnswer": {"@type": "Answer", "text": card},
            },
            {
                "@type": "Question",
                "name": f"What are the catches of the {tool['name']} free tier?",
                "acceptedAnswer": {"@type": "Answer", "text": " ".join(tool["traps"]) or "No major catches on record."},
            },
        ],
    }
    return json.dumps(faq, ensure_ascii=False)


def build_tool_page(tool: dict, tools: list, meta: dict) -> str:
    year = meta["last_full_review"][:4]
    base = meta["base_url"].rstrip("/")
    canonical = f"{base}/tools/{tool['id']}.html"
    cat_label = CATEGORIES.get(tool["category"], tool["category"])
    related = [t for t in tools if t["category"] == tool["category"] and t["id"] != tool["id"]]
    if len(related) < 3:  # pad with other categories
        related += [t for t in tools if t["category"] != tool["category"]][: 3 - len(related)]
    related_html = "".join(
        f'<a href="{esc(t["id"])}.html">{esc(t["name"])}</a>' for t in related[:6]
    ) or '<a href="../index.html#tools">Browse the full directory</a>'
    card_badge = (
        '<span class="badge ok">No card required</span>'
        if not tool["card_required"]
        else '<span class="badge warn">Card required</span>'
    )
    limits_html = "".join(f"<li>{esc(l)}</li>" for l in tool["limits"])
    traps_html = "".join(f"<li>{esc(t)}</li>" for t in tool["traps"]) or "<li>No major traps on record — enjoy it while it lasts.</li>"
    meta_desc = (
        f"{tool['name']} free tier, verified {tool['verified']}: "
        + "; ".join(tool["limits"][:3])
        + ". Plus the traps the pricing page won't highlight."
    )[:158]
    return PAGE_TMPL.format(
        name=esc(tool["name"]),
        year=year,
        meta_desc=esc(meta_desc),
        canonical=esc(canonical),
        jsonld=jsonld_for(tool, canonical),
        css=PAGE_CSS,
        cat_label=esc(cat_label),
        card_badge=card_badge,
        verified=esc(tool["verified"]),
        summary=esc(tool["summary"]),
        limits_html=limits_html,
        traps_html=traps_html,
        verdict=esc(verdict_for(tool)),
        newsletter_url=esc(meta["newsletter_url"]),
        related_html=related_html,
        pricing_url=esc(tool["pricing_url"]),
        source=esc(tool["source"]),
        repo_url=esc(meta["repo_url"]),
    )


def main() -> int:
    data = json.loads(DATA.read_text(encoding="utf-8"))
    meta, tools = data["meta"], data["tools"]
    base = meta["base_url"].rstrip("/")

    # 1) embed data into index.html
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    idx = INDEX.read_text(encoding="utf-8")
    block = re.compile(r'(<script id="tools-data" type="application/json">).*?(</script>)', re.DOTALL)
    if not block.search(idx):
        print("ERROR: tools-data block not found in index.html", file=sys.stderr)
        return 1
    idx = block.sub(lambda m: m.group(1) + "\n" + payload + "\n" + m.group(2), idx, count=1)

    # 2) sync urls from meta
    idx = re.sub(r'(<link rel="canonical" href=")[^"]*(")', rf"\g<1>{base}/\g<2>", idx, count=1)
    idx = re.sub(r'("@type":"WebSite"[^}]*"url":")[^"]*(")', rf"\g<1>{base}/\g<2>", idx, count=1)
    idx = re.sub(r'(id="newsletter-link" href=")[^"]*(")', rf'\g<1>{meta["newsletter_url"]}\g<2>', idx, count=1)
    idx = re.sub(r'(id="gh-link" href=")[^"]*(")', rf'\g<1>{meta["repo_url"]}\g<2>', idx, count=1)
    INDEX.write_text(idx, encoding="utf-8")

    # 3) per-tool pages
    TOOLS_DIR.mkdir(exist_ok=True)
    for t in tools:
        (TOOLS_DIR / f"{t['id']}.html").write_text(build_tool_page(t, tools, meta), encoding="utf-8")

    # 4) sitemap + robots
    today = meta["last_full_review"]
    urls = [f"{base}/"] + [f"{base}/tools/{t['id']}.html" for t in tools]
    sitemap = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for u in urls:
        sitemap.append(f"  <url><loc>{esc(u)}</loc><lastmod>{today}</lastmod></url>")
    sitemap.append("</urlset>")
    (ROOT / "sitemap.xml").write_text("\n".join(sitemap) + "\n", encoding="utf-8")
    (ROOT / "robots.txt").write_text(f"User-agent: *\nAllow: /\n\nSitemap: {base}/sitemap.xml\n", encoding="utf-8")

    print(f"OK: index.html updated, {len(tools)} tool pages, sitemap.xml ({len(urls)} urls), robots.txt")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
