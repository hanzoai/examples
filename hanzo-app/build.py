#!/usr/bin/env python3
"""build.py — compose every Hanzo product and publish it through the ONE path.

A product is TWO files and nothing else: a row in products.json (its identity —
slug, name, tagline, brand hue, mark, the named agent that builds it, and the
gallery template it is forked from) and apps/<slug>.html (its body: an
`<!--hz {...}-->` header, markup and one <script>). ONE slug names all three:
the source file, the project, and the host. This script joins the two,
wraps them in the shared shell, attaches the shared kit (hz.css / hz.js) and the
a.hanzo.ai runtime, emits /.well-known/hanzo-example.json, and POSTs the file
manifest to https://api.hanzo.ai/v1/sites/deploy.

THREE THINGS ARE NOT PER-APP, because the shell is the only way a product is
built and an app that skips it cannot be published:

  BRAND.   The product's hue drives --acc/--acc2, so every primitive in the kit
           inherits it; the mark, the name and the tagline are rendered from the
           same row. One product, one identity, in one place.
  BYLINE.  "<Product> — published by Hanzo AI, built by <Agent>". The agent is
           real: it is the agent that wrote the app. It is described as what it
           is (an AI agent, with a discipline) and never dressed as a person —
           no biography, no employer, no photograph. See agents.json.
  BADGE.   hanzo:official + JSON-LD + a visible "Hanzo product" chip in the
           header AND the footer + the machine-readable manifest.

The `official` FLAG on the project record is not set from here and cannot be:
api.hanzo.ai gates it on a SuperAdmin principal. It is declared platform-side in
cloud/clients/projects/firstparty.json, off the same slugs. `--verify-official`
asserts the two halves agree.
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
FORK = "https://api.hanzo.ai/v1/projects/fork"
PROJECT = "https://api.hanzo.ai/v1/projects/%s"
CATALOG = "https://api.hanzo.ai/v1/catalog?limit=600"
TOKEN = open(os.path.expanduser("~/.cache/work/token")).read().strip()

PRODUCTS = json.load(open(os.path.join(ROOT, "products.json")))["products"]
AGENTS = json.load(open(os.path.join(ROOT, "agents.json")))["agents"]

# The index OF the products is not one of them: it is derived (gallery.py reads
# the same roster) and it is forked from nothing, so it carries no template and
# is not in products.json. It is published through the identical path — empty
# `template` is the only thing that distinguishes it, and it means exactly what
# it says: no parent.
GALLERY = {"slug": "examples", "name": "Hanzo Products",
           "tagline": "Every product Hanzo publishes, and the agent that built it.",
           "hue": 224, "mark": "H", "agent": "solaris", "template": "",
           "archetype": "gallery", "nav": [["#/", "Products"], ["#/agents", "Agents"]],
           "desc": ""}
ALL = PRODUCTS + [GALLERY]
BY_SLUG = {p["slug"]: p for p in ALL}

NOTICE = "Every record, person and metric shown is synthetic demo data."


def mark(letter, hue, size=26, r=8):
    """The product mark. Generated from the row, not drawn by hand: 74 products
    need 74 distinct marks and a generated one cannot drift from the brand."""
    return (
        '<svg width="%d" height="%d" viewBox="0 0 32 32" class="hz-m" aria-hidden="true">'
        '<rect width="32" height="32" rx="%d" fill="hsl(%d 74%% 55%%)"/>'
        '<text x="16" y="22" text-anchor="middle" font-family="system-ui,sans-serif"'
        ' font-size="17" font-weight="700" fill="#fff">%s</text></svg>'
        % (size, size, r, hue, letter))


def avatar(handle, size=20):
    """The agent's avatar: a generated mark, deliberately NOT a photograph and
    deliberately not the same shape as a product mark — a ring with a satellite,
    so it reads as an agent rather than as a person or a product."""
    a = AGENTS[handle]
    h = a["hue"]
    return (
        '<svg width="%d" height="%d" viewBox="0 0 32 32" class="hz-a" aria-hidden="true">'
        '<circle cx="16" cy="16" r="14" fill="hsl(%d 62%% 22%%)" stroke="hsl(%d 70%% 58%%)"/>'
        '<circle cx="16" cy="16" r="6.5" fill="hsl(%d 74%% 60%%)"/>'
        '<circle cx="27" cy="9" r="3.2" fill="hsl(%d 80%% 72%%)"/></svg>'
        % (size, size, h, h, h, h))


def favicon(letter, hue):
    svg = ("<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'>"
           "<rect width='32' height='32' rx='9' fill='hsl(%d,74%%,55%%)'/>"
           "<text x='16' y='22.5' text-anchor='middle' font-family='sans-serif'"
           " font-size='18' font-weight='700' fill='#fff'>%s</text></svg>" % (hue, letter))
    return "data:image/svg+xml," + svg.replace("#", "%23").replace('"', "'")


BADGE = ('<span class="hz-official" title="Published by Hanzo AI">&#9670; '
         '<b>Hanzo product</b></span>')

HEAD = """<!doctype html>
<html lang="en" data-theme="dark" style="--acc:hsl({hue} 78% 62%);--acc2:hsl({hue2} 72% 60%)">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{name} &mdash; {tagline}</title>
<meta name="description" content="{desc}">
<meta name="hanzo:official" content="true">
<meta name="hanzo:publisher" content="Hanzo AI, Inc.">
<meta name="hanzo:agent" content="{ahandle}">
<meta name="hanzo:forked-from" content="{template}">
<meta name="hanzo:archetype" content="{archetype}">
<meta name="theme-color" content="hsl({hue} 74% 55%)">
<meta name="robots" content="index,follow">
<meta property="og:title" content="{name} &mdash; {tagline}">
<meta property="og:description" content="{desc}">
<script type="application/ld+json">{ld}</script>
<link rel="stylesheet" href="/hz.css">
<link rel="icon" href="{icon}">
<script src="https://a.hanzo.ai/analytics.js" data-org="hanzo" defer></script>
<script src="https://a.hanzo.ai/chat.js" data-org="hanzo" data-mode="site" defer></script>
</head>
<body>
<header class="hz-top">
  <span class="brand">{mark}<span>{name}</span></span>
  <span class="hz-tag">{tagline}</span>
  <nav>{nav}</nav>
  <span class="spacer"></span>
  """ + BADGE + """
  <span id="hz-theme"></span>
</header>
<main>
{body}
</main>
<footer class="hz-foot">
  <span class="hz-by">{avatar}<span><b>{name}</b> &mdash; published by
  <a href="https://hanzo.ai">Hanzo AI</a>, built by
  <a href="https://examples.hanzo.app/#/agent/{ahandle}"><b>{aname}</b></a>,
  an AI agent working on {adisc}. {notice}</span></span>
  <span class="spacer"></span>
  {lineage}
  <a href="/.well-known/hanzo-example.json">manifest</a>
  <a href="https://examples.hanzo.app">all products</a>
</footer>
<script src="/hz.js"></script>
<script>document.getElementById('hz-theme').append(hz.theme());</script>
{script}
</body>
</html>
"""

# The two shell rules the kit does not already carry: the tagline slot in the
# header and the agent byline in the footer. Appended to hz.css once, here, so
# they cannot be forgotten by an app and cannot be restyled per-app.
SHELL_CSS = """
.hz-top .brand .hz-m{flex:none;display:block}
.hz-tag{color:var(--fg3);font-size:12.5px;white-space:nowrap;overflow:hidden;
  text-overflow:ellipsis;max-width:44ch}
@media(max-width:900px){.hz-tag{display:none}}
.hz-by{display:flex;align-items:center;gap:8px;max-width:78ch}
.hz-by .hz-a{flex:none}
"""

META_RE = re.compile(r"^<!--hz\s*(\{.*?\})\s*-->\s*", re.S)
KIT_CSS = open(os.path.join(ROOT, "kit", "hz.css")).read() + SHELL_CSS
KIT_JS = open(os.path.join(ROOT, "kit", "hz.js")).read()


def compose(p):
    """Join a product row with its app body and return (files, html)."""
    src = open(os.path.join(ROOT, "apps", p["slug"] + ".html"), encoding="utf-8").read()
    m = META_RE.match(src)
    if not m:
        raise ValueError(p["slug"] + ": missing <!--hz {...}--> header")
    body = src[m.end():]
    script = ""
    i = body.find("<script>")
    if i >= 0:
        script, body = body[i:], body[:i]
    a = AGENTS[p["agent"]]
    desc = "%s %s" % (p["tagline"], p["desc"])
    ld = json.dumps({
        "@context": "https://schema.org", "@type": "SoftwareApplication",
        "name": p["name"], "applicationCategory": p["archetype"],
        "description": p["tagline"], "isAccessibleForFree": True,
        "publisher": {"@type": "Organization", "name": "Hanzo AI, Inc.",
                      "url": "https://hanzo.ai"},
        # The creator is SOFTWARE, because it is: an AI agent that Hanzo runs and
        # that genuinely wrote this app. Modelling it as a Person would be the
        # one lie this catalogue refuses to tell.
        "creator": {"@type": "SoftwareApplication", "name": a["name"],
                    "applicationCategory": "AI agent",
                    "description": a["profile"],
                    "publisher": {"@type": "Organization", "name": "Hanzo AI, Inc."}},
        **({"isBasedOn": "https://hanzo.app/templates/" + p["template"]}
           if p["template"] else {}),
        "disambiguatingDescription": NOTICE,
    }, separators=(",", ":"))
    html = HEAD.format(
        name=p["name"], tagline=p["tagline"], desc=desc, hue=p["hue"],
        hue2=(p["hue"] + 38) % 360, archetype=p["archetype"], template=p["template"],
        icon=favicon(p["mark"], p["hue"]), mark=mark(p["mark"], p["hue"]),
        avatar=avatar(p["agent"]), ahandle=p["agent"], aname=a["name"],
        adisc=a["discipline"].lower(), ld=ld, notice=NOTICE,
        lineage=('<a href="https://hanzo.app/templates/%s">forked from %s</a>'
                 % (p["template"], p["template"])) if p["template"] else "",
        nav="".join('<a href="%s">%s</a>' % (u, t) for u, t in p["nav"]),
        body=body, script=script)
    manifest = {
        "official": True, "firstParty": True, "slug": p["slug"], "name": p["name"],
        "tagline": p["tagline"], "archetype": p["archetype"],
        "publisher": {"name": "Hanzo AI, Inc.", "url": "https://hanzo.ai"},
        "builtBy": {"handle": p["agent"], "name": a["name"], "type": "ai-agent",
                    "discipline": a["discipline"], "profile": a["profile"],
                    "human": False, "independentThirdParty": False},
        "forkedFrom": ({"template": p["template"],
                        "source": "https://github.com/hanzo-templates/" + p["template"],
                        "via": "POST /v1/projects/fork"} if p["template"] else None),
        "backend": {"provider": "@hanzo/base",
                    "endpoint": "/v1/base/collections/submissions/records"},
        "runtime": ["https://a.hanzo.ai/analytics.js", "https://a.hanzo.ai/chat.js"],
        "syntheticData": True, "notice": NOTICE,
    }
    return [
        {"path": "index.html", "content": html},
        {"path": ".well-known/hanzo-example.json", "content": json.dumps(manifest, indent=2)},
        {"path": "hz.css", "content": KIT_CSS},
        {"path": "hz.js", "content": KIT_JS},
    ], html


def api(url, body=None, method="GET"):
    req = urllib.request.Request(
        url, data=json.dumps(body).encode() if body is not None else None,
        method=method, headers={"Authorization": "Bearer " + TOKEN,
                                "X-Org-Id": "hanzo", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            return r.status, json.load(r)
    except urllib.error.HTTPError as e:
        return e.code, e.read()[:200].decode("utf-8", "replace")
    except Exception as e:
        return 0, str(e)[:200]


def syntax(slug, html):
    """Refuse to publish a page whose script does not parse. A syntax error ships
    a 200 that renders nothing — the exact failure this catalogue exists to avoid."""
    i, j = html.rfind("<script>"), html.rfind("</script>")
    if i < 0 or j < i:
        return ""
    tmp = "/tmp/hzchk-%s.js" % slug
    open(tmp, "w").write(html[i + 8:j])
    p = subprocess.run(["node", "--check", tmp], capture_output=True)
    os.remove(tmp)
    return "" if p.returncode == 0 else p.stderr.decode()[:200].replace("\n", " ")


def fork(p):
    """Create the product's project BY FORKING its parent template, so lineage is
    a fact the platform recorded at fork time (projects.forked_from) rather than a
    claim this script makes about itself afterwards. Idempotent: the slug is only
    claimable once, so a re-run gets 409 and keeps the original edge.

    It must run BEFORE the deploy: /v1/sites/deploy calls ensureProject, which
    reuses an existing project but creates a LINEAGE-LESS one if there is none."""
    code, out = api(FORK, {"slug": p["template"], "target": p["slug"], "name": p["name"]}, "POST")
    if code in (200, 201, 409):
        # The fork seeds name/description from the PARENT, which is correct for a
        # fork and wrong for a product: the catalog row must read as the product,
        # not as the template it came from. Lineage stays (forked_from is
        # immutable and not a caller field); only the identity is the product's.
        api(PROJECT % p["slug"], {"name": p["name"], "description": p["tagline"]}, "PATCH")
    return code, out


def one(p):
    try:
        files, html = compose(p)
    except Exception as e:
        return p["slug"], 0, "compose: %s" % e
    bad = syntax(p["slug"], html)
    if bad:
        return p["slug"], 0, "SYNTAX " + bad
    if p["template"]:
        fc, fo = fork(p)
        if fc not in (200, 201, 409):
            return p["slug"], 0, "fork %s: %s" % (fc, fo)
    code, out = api(API, {"slug": p["slug"], "name": p["name"], "files": files}, "POST")
    return p["slug"], code, (out.get("url", "") if isinstance(out, dict) else out)


def verify_official():
    """Assert the platform-side declaration landed: every product must come back
    from the PUBLIC catalog as official. This is the join between the two halves
    (cloud/clients/projects/firstparty.json and products.json) and it fails loud."""
    rows = json.load(urllib.request.urlopen(CATALOG, timeout=120))["data"]
    by = {r["id"]: r for r in rows}
    bad = []
    for p in PRODUCTS:
        r = by.get("hanzo/" + p["slug"])
        if r is None:
            bad.append((p["slug"], "absent from catalog"))
        elif not r.get("official"):
            bad.append((p["slug"], "official=false"))
    print("official: %d/%d products" % (len(PRODUCTS) - len(bad), len(PRODUCTS)))
    for s, why in bad:
        print("  FAIL %-14s %s" % (s, why))
    return 1 if bad else 0


def main():
    if "--verify-official" in sys.argv:
        sys.exit(verify_official())
    names = [a for a in sys.argv[1:] if not a.startswith("-")]
    todo = [BY_SLUG[n] for n in names] if names else ALL
    with cf.ThreadPoolExecutor(8) as ex:
        for slug, code, out in ex.map(one, todo):
            print("%-14s %-3s %s" % (slug, code, out), flush=True)


if __name__ == "__main__":
    main()
