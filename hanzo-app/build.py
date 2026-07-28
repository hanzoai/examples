#!/usr/bin/env python3
"""build.py — compose every example app and publish it through the ONE path.

An app is ONE file: apps/<slug>.html, opening with an `<!--hz {...}-->` header
that declares its title / archetype / creator. This script wraps that fragment
in the shared shell (head + first-party marker + nav + footer), attaches the
shared kit (hz.css / hz.js) and the shared a.hanzo.ai runtime, emits the
machine-readable /.well-known/hanzo-example.json marker, and POSTs the file
manifest to https://api.hanzo.ai/v1/sites/deploy.

Labelling is NOT optional and NOT per-app: it is applied here, once, to every
app — a `hanzo:official` meta + JSON-LD + a visible "Hanzo Example" badge in the
header AND the footer + the .well-known manifest. An example that skips the
shell cannot be published, because the shell is the only way an app is built.
"""
import concurrent.futures as cf
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.abspath(__file__))
API = "https://api.hanzo.ai/v1/sites/deploy"
TOKEN = open("/home/z/.cache/work/token").read().strip()

# ---- seeded creator accounts -------------------------------------------------
# FIRST-PARTY Hanzo example studios. They are named as what they are — internal
# Hanzo teams — carry official/seeded flags, and have no invented biography,
# employer, photograph or social proof. Nothing here may imply an independent
# third-party author.
CREATORS = {
    "web": ("Hanzo Examples — Web Studio", "Marketing, content and storefront examples"),
    "apps": ("Hanzo Examples — App Studio", "Dashboards, CRUD and internal-tool examples"),
    "ai": ("Hanzo Examples — AI Studio", "Chat, agent, RAG and generation examples"),
    "live": ("Hanzo Examples — Realtime Studio", "Multiplayer, WebRTC and collaboration examples"),
    "gfx": ("Hanzo Examples — Graphics Studio", "WebGL, canvas and 3D examples"),
    "data": ("Hanzo Examples — Data Studio", "Analytics, ETL and developer-tool examples"),
}
NOTICE = ("First-party Hanzo example, published by Hanzo AI. Not independent "
          "community content. All records, people and metrics shown are "
          "synthetic demo data.")

BADGE = ('<span class="hz-official" title="{n}">&#9670; <b>Hanzo Example</b> '
         '&middot; official</span>')

HEAD = """<!doctype html>
<html lang="en" data-theme="dark">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} &middot; Hanzo Example</title>
<meta name="description" content="{desc}">
<meta name="hanzo:official" content="true">
<meta name="hanzo:seeded" content="true">
<meta name="hanzo:first-party" content="true">
<meta name="hanzo:creator" content="{chandle}">
<meta name="hanzo:archetype" content="{archetype}">
<meta name="robots" content="index,follow">
<meta property="og:title" content="{title} — official Hanzo example">
<meta property="og:description" content="{desc}">
<script type="application/ld+json">{ld}</script>
<link rel="stylesheet" href="/hz.css">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='9' fill='%235b8cff'/%3E%3C/svg%3E">
<script src="https://a.hanzo.ai/analytics.js" data-org="hanzo" defer></script>
<script src="https://a.hanzo.ai/chat.js" data-org="hanzo" data-mode="site" defer></script>
</head>
<body>
<header class="hz-top">
  <span class="brand"><span class="dot"></span>{title}</span>
  """ + BADGE + """
  <nav>{nav}</nav>
  <span class="spacer"></span>
  <span id="hz-theme"></span>
</header>
<main>
{body}
</main>
<footer class="hz-foot">
  """ + BADGE + """
  <span>Published by <b>{cname}</b> &mdash; an official first-party Hanzo example
  account (<code>official: true</code>, <code>seeded: true</code>). {notice}</span>
  <span class="spacer"></span>
  <a href="/.well-known/hanzo-example.json">manifest</a>
  <a href="https://hanzo.app">hanzo.app</a>
</footer>
<script src="/hz.js"></script>
<script>document.getElementById('hz-theme').append(hz.theme());</script>
{script}
</body>
</html>
"""

META_RE = re.compile(r"^<!--hz\s*(\{.*?\})\s*-->\s*", re.S)


def compose(slug, src):
    m = META_RE.match(src)
    if not m:
        raise ValueError(slug + ": missing <!--hz {...}--> header")
    meta = json.loads(m.group(1))
    body = src[m.end():]
    script = ""
    i = body.find("<script>")
    if i >= 0:
        script, body = body[i:], body[:i]
    ck = meta.get("creator", "apps")
    cname, crole = CREATORS[ck]
    nav = "".join('<a href="%s">%s</a>' % (u, t) for u, t in meta.get("nav", []))
    ld = json.dumps({
        "@context": "https://schema.org", "@type": "SoftwareApplication",
        "name": meta["title"], "applicationCategory": meta["archetype"],
        "description": meta.get("desc", ""),
        "isAccessibleForFree": True,
        "publisher": {"@type": "Organization", "name": "Hanzo AI, Inc.", "url": "https://hanzo.ai"},
        "author": {"@type": "Organization", "name": cname, "identifier": "hanzo-examples-" + ck},
        "disambiguatingDescription": NOTICE,
    }, separators=(",", ":"))
    html = HEAD.format(title=meta["title"], desc=meta.get("desc", ""), nav=nav,
                       archetype=meta["archetype"], chandle="hanzo-examples-" + ck,
                       cname=cname, n=crole, ld=ld, notice=NOTICE,
                       body=body, script=script)
    manifest = {
        "official": True, "seeded": True, "firstParty": True,
        "vendor": "Hanzo AI, Inc.", "slug": slug, "title": meta["title"],
        "archetype": meta["archetype"], "description": meta.get("desc", ""),
        "creator": {"handle": "hanzo-examples-" + ck, "name": cname, "role": crole,
                    "official": True, "seeded": True, "type": "first-party-team",
                    "independentThirdParty": False},
        "backend": {"provider": "@hanzo/base",
                    "endpoint": "/v1/base/collections/submissions/records"},
        "runtime": ["https://a.hanzo.ai/analytics.js", "https://a.hanzo.ai/chat.js"],
        "upstream": meta.get("upstream"), "license": meta.get("license"),
        "syntheticData": True, "notice": NOTICE,
    }
    files = [
        {"path": "index.html", "content": html},
        {"path": ".well-known/hanzo-example.json",
         "content": json.dumps(manifest, indent=2)},
        {"path": "hz.css", "content": KIT_CSS},
        {"path": "hz.js", "content": KIT_JS},
    ]
    return meta, files


KIT_CSS = open(os.path.join(ROOT, "kit", "hz.css")).read()
KIT_JS = open(os.path.join(ROOT, "kit", "hz.js")).read()


def deploy(slug, meta, files):
    body = json.dumps({"slug": slug, "name": meta["title"], "files": files}).encode()
    req = urllib.request.Request(API, data=body, method="POST", headers={
        "Authorization": "Bearer " + TOKEN, "X-Org-Id": "hanzo",
        "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            return r.status, json.load(r).get("url", "")
    except urllib.error.HTTPError as e:
        return e.code, e.read()[:180].decode("utf-8", "replace")
    except Exception as e:
        return 0, str(e)[:180]


def syntax(slug, html):
    """Refuse to publish a page whose script does not parse. A syntax error
    ships a 200 that renders nothing — the exact failure this batch must avoid —
    so the check belongs HERE, before the deploy, not in review afterwards."""
    i, j = html.rfind("<script>"), html.rfind("</script>")
    if i < 0 or j < i:
        return ""
    tmp = "/tmp/hzchk-%s.js" % slug
    open(tmp, "w").write(html[i + 8:j])
    p = subprocess.run(["node", "--check", tmp], capture_output=True)
    os.remove(tmp)
    return "" if p.returncode == 0 else p.stderr.decode()[:200].replace("\n", " ")


def one(path):
    slug = os.path.basename(path)[:-5]
    try:
        meta, files = compose(slug, open(path, encoding="utf-8").read())
    except Exception as e:
        return slug, 0, "compose: %s" % e, ""
    bad = syntax(slug, files[0]["content"])
    if bad:
        return slug, 0, "SYNTAX " + bad, meta["archetype"]
    code, out = deploy(slug, meta, files)
    return slug, code, out, meta["archetype"]


def main():
    names = sys.argv[1:]
    apps = sorted(os.path.join(ROOT, "apps", f) for f in os.listdir(os.path.join(ROOT, "apps"))
                  if f.endswith(".html") and (not names or f[:-5] in names))
    with cf.ThreadPoolExecutor(8) as ex:
        for slug, code, out, arch in ex.map(one, apps):
            print("%-26s %-3s %-22s %s" % (slug, code, arch, out), flush=True)


if __name__ == "__main__":
    main()
