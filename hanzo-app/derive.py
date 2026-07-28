#!/usr/bin/env python3
"""derive.py — build a product FROM its parent template, and prove it.

products.json records which gallery template each product was forked from, and
POST /v1/projects/fork records that edge platform-side. This script closes the
loop the only way that actually means anything: it checks out the parent
template, applies the agent's edit to its SOURCE, runs the template's own build,
and publishes THAT output as the product. The `git diff` it prints is the whole
point — it is simultaneously the proof the product is a derivative and the proof
a template is agent-editable.

The edit has two halves and both are declared in products.json under `derive`:

  BRAND (generic, every derivative gets it): the document metadata becomes the
  product's, and the design-system's primary/ring tokens become the product's
  hue. One function, because "make the template wear the product's brand" is one
  idea, not N.

  CONTENT (per product): `replace` pairs rewrite the template's own copy into the
  product's. This is the half a generic transform cannot do and the half that
  makes the result a product rather than a recoloured demo.

Usage: derive.py [slug ...]     (default: every product with a `derive` block)
       derive.py --diff [slug]  (apply + build nothing, just show the diff)
"""
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import urllib.error
import urllib.request

import build as B  # the ONE publish path: compose/api/deploy live there

ROOT = os.path.dirname(os.path.abspath(__file__))
# Where the parent template checkouts live. They are ordinary git clones of
# github.com/hanzo-templates/<slug>, so the baseline the diff is taken against
# is the template's real HEAD, not a copy this script made up.
TPL = os.environ.get("HZ_TEMPLATES", os.path.expanduser("~/.cache/work/tpl2"))
BUILD_DIRS = ["out", "dist", "build", "_site", "public"]
TEXT = {".html", ".css", ".js", ".mjs", ".json", ".svg", ".txt", ".xml",
        ".webmanifest", ".map", ".md", ".ico"}
RUNTIME = ('<script src="https://a.hanzo.ai/analytics.js" data-org="hanzo" defer></script>\n'
           '<script src="https://a.hanzo.ai/chat.js" data-org="hanzo" data-mode="site" defer></script>\n')


def git(d, *a):
    return subprocess.run(["git", "-C", d, *a], capture_output=True, text=True).stdout


def reset(d):
    """Back to the template's own HEAD. Every derivation starts from the same
    baseline, so the diff is against the TEMPLATE and never against the last run.
    node_modules is preserved — it is not part of the template's source."""
    git(d, "checkout", "--", ".")
    git(d, "clean", "-fdq", "-e", "node_modules")


def placeholder(hue, w, h):
    """Templates that source demo imagery from an /api/placeholder route 404 on a
    static host — one of the real defects this exercise turns up. The agent's edit
    replaces them with an inline SVG in the product's own hue, which is both a fix
    and a brand."""
    return ("data:image/svg+xml,%%3Csvg xmlns='http://www.w3.org/2000/svg' width='%s'"
            " height='%s'%%3E%%3Crect width='100%%25' height='100%%25' fill='hsl(%d,42%%25,26%%25)'/"
            "%%3E%%3Ccircle cx='50%%25' cy='50%%25' r='%s' fill='hsl(%d,74%%25,55%%25)'/%%3E%%3C/svg%%3E"
            % (w, h, hue, max(8, int(min(int(w), int(h)) / 6)), hue))


def brand(d, p):
    """The generic half: the template wears the product's identity."""
    a = B.AGENTS[p["agent"]]
    hue, n = p["hue"], 0
    for rel in ("app/layout.tsx", "src/app/layout.tsx", "app/layout.js"):
        f = os.path.join(d, rel)
        if not os.path.exists(f):
            continue
        s = t = open(f, encoding="utf-8").read()
        s = re.sub(r'(title:\s*)"[^"]*"', r'\1"%s — %s"' % (p["name"], p["tagline"]), s)
        s = re.sub(r'(description:\s*)"[^"]*"', r'\1"%s"' % p["tagline"], s)
        # The byline is rendered BY the template, not stapled onto its output:
        # a Next.js app owns <body> after hydration and drops anything it did not
        # render, so an injected footer survives the first paint and no longer.
        if "HZ_BYLINE" not in s and "{children}" in s:
            s = ("const HZ_BYLINE = " + json.dumps(byline(p)) + ";\n" + s).replace(
                "{children}",
                "{children}\n        <footer className=\"hzf\" "
                "dangerouslySetInnerHTML={{ __html: HZ_BYLINE }} />", 1)
        if s != t:
            open(f, "w", encoding="utf-8").write(s)
            n += 1
        break
    for rel in ("app/globals.css", "src/app/globals.css", "styles/globals.css"):
        f = os.path.join(d, rel)
        if not os.path.exists(f):
            continue
        css = open(f, encoding="utf-8").read()
        # Appended, not rewritten: the template keeps its own token scale and the
        # product only overrides the two that carry the brand.
        open(f, "a", encoding="utf-8").write(
            "\n/* %s — brand tokens. Built by %s (AI agent, %s) for Hanzo AI. */\n"
            ":root,.dark{--primary:%d 74%% 55%%;--ring:%d 74%% 55%%;"
            "--primary-foreground:0 0%% 100%%}\n" % (
                p["name"], a["name"], a["discipline"].lower(), hue, hue) + BYLINE_CSS)
        n += 1
        break
    # A product on hanzo.app is a static site; a template that has not said so
    # cannot be published. Part of the agent's edit, and honest about it.
    for rel in ("next.config.js", "next.config.mjs", "next.config.ts"):
        f = os.path.join(d, rel)
        if os.path.exists(f):
            s = open(f, encoding="utf-8").read()
            if "output:" not in s:
                s = re.sub(r"(nextConfig(?::\s*NextConfig)?\s*=\s*\{)",
                           r"\1\n  output: 'export',", s, count=1)
                s = s.replace("images: {", "images: { unoptimized: true,", 1)
                open(f, "w", encoding="utf-8").write(s)
                n += 1
            break
    for dp, dns, fs in os.walk(d):
        dns[:] = [x for x in dns if x not in (".git", "node_modules", ".next", "out", "dist")]
        for f in fs:
            if os.path.splitext(f)[1] not in (".tsx", ".jsx", ".ts", ".js"):
                continue
            fp = os.path.join(dp, f)
            try:
                s = t = open(fp, encoding="utf-8").read()
            except (OSError, UnicodeDecodeError):
                continue
            s = re.sub(r"/api/placeholder/(\d+)/(\d+)",
                       lambda m: placeholder(hue, m.group(1), m.group(2)), s)
            # A template that hard-codes its accent (`bg-amber-600` on the CTA)
            # cannot be rebranded, which defeats being a template. Point the
            # primary action at the design token instead — a rebrand AND a fix.
            s = re.sub(r"bg-(?:amber|orange|blue|indigo|violet|emerald|rose|red|"
                       r"green|purple|sky|teal|cyan)-(?:500|600)"
                       r"(\s+hover:bg-(?:amber|orange|blue|indigo|violet|emerald|"
                       r"rose|red|green|purple|sky|teal|cyan)-(?:600|700))",
                       "bg-primary hover:bg-primary/90", s)
            # Every one of these templates ships the same placeholder subtitle.
            s = s.replace("Built with @hanzo/ui components", p["tagline"])
            if s != t:
                open(fp, "w", encoding="utf-8").write(s)
                n += 1
    return n


def content(d, p):
    """The per-product half: the template's copy becomes the product's."""
    pairs = p["derive"].get("replace", [])
    n = 0
    for dp, dns, fs in os.walk(d):
        dns[:] = [x for x in dns if x not in (".git", "node_modules", ".next", "out", "dist")]
        for f in fs:
            if os.path.splitext(f)[1] not in (".tsx", ".ts", ".jsx", ".js", ".mdx", ".md", ".json"):
                continue
            fp = os.path.join(dp, f)
            try:
                s = t = open(fp, encoding="utf-8").read()
            except (OSError, UnicodeDecodeError):
                continue
            for a, b in pairs:
                s = s.replace(a, b)
            if s != t:
                open(fp, "w", encoding="utf-8").write(s)
                n += 1
    return n


def buildsite(d):
    """Run the template's OWN build. A non-zero exit is fatal even when a build
    directory exists: `out/` is gitignored, so it survives `git clean` from the
    previous run, and trusting its presence is exactly how a failed build ships
    yesterday's bytes under today's brand."""
    for c in BUILD_DIRS:  # never inherit a stale build
        shutil.rmtree(os.path.join(d, c), ignore_errors=True)
    r = subprocess.run(["npm", "run", "build"], cwd=d, capture_output=True,
                       text=True, timeout=900)
    if r.returncode != 0:
        return "", r.returncode, (r.stdout + r.stderr)[-500:]
    for c in BUILD_DIRS:
        if os.path.exists(os.path.join(d, c, "index.html")):
            return c, 0, ""
    return "", 0, "build succeeded but produced no index.html"


BYLINE_CSS = (
    "\n.hzf{display:flex;gap:10px;align-items:center;flex-wrap:wrap;padding:14px 18px;"
    "border-top:1px solid rgba(128,128,128,.25);font:12.5px/1.5 system-ui,sans-serif;"
    "background:#0b0c0f;color:#98a0b0}.hzf a{color:#8ab4ff;text-decoration:none}"
    ".hzf b{color:#e7eaf0}.hzb{display:inline-flex;align-items:center;gap:6px;"
    "border:1px solid rgba(91,140,255,.35);border-radius:999px;padding:3px 10px;"
    "font-size:11px;font-weight:600;color:#a9c2ff}\n")


def byline(p):
    """The product's identity, applied to a page the TEMPLATE authored. A
    derivative is still a product: it carries the same mark, the same "Hanzo
    product" badge and the same named-agent byline as every kit-built one, from
    the same row. Injected into the built HTML rather than into the template
    source, because it is a fact about the PRODUCT, not an edit to the parent."""
    a = B.AGENTS[p["agent"]]
    return ('%s%s<span><b>%s</b> \u2014 published by '
            '<a href="https://hanzo.ai">Hanzo AI</a>, built by '
            '<a href="https://examples.hanzo.app/#/agent/%s"><b>%s</b></a>, an AI agent '
            'working on %s. %s</span><span style="flex:1"></span>'
            '<span class="hzb">\u25C6 Hanzo product</span>'
            '<a href="https://hanzo.app/templates/%s">forked from %s</a>'
            '<a href="/.well-known/hanzo-example.json">manifest</a>'
            '<a href="https://examples.hanzo.app">all products</a>' % (
                B.mark(p["mark"], p["hue"], 22, 7), B.avatar(p["agent"], 20), p["name"],
                p["agent"], a["name"], a["discipline"].lower(), B.NOTICE,
                p["template"], p["template"]))


def files(root, p):
    """The built site, as bytes. Binary assets (the fonts next/font self-hosts,
    images) are carried verbatim — dropping them is how a derived build ships a
    page that answers 200 and 404s six times in the console."""
    head = ('<meta name="hanzo:official" content="true">'
            '<meta name="hanzo:publisher" content="Hanzo AI, Inc.">'
            '<meta name="hanzo:agent" content="%s">'
            '<meta name="hanzo:forked-from" content="%s">'
            '<link rel="icon" href="%s">' % (
                p["agent"], p["template"], B.favicon(p["mark"], p["hue"])))
    out = []
    for dp, dns, fs in os.walk(root):
        dns[:] = [x for x in dns if x != ".git"]
        for f in fs:
            fp = os.path.join(dp, f)
            rel = os.path.relpath(fp, root).replace(os.sep, "/")
            if os.path.getsize(fp) > 4_000_000:
                continue
            data = open(fp, "rb").read()
            if f.endswith(".html"):
                t = data.decode("utf-8", "replace")
                if "a.hanzo.ai/analytics.js" not in t:
                    t = t.replace("</head>", RUNTIME + head + "</head>", 1)
                data = t.encode()
            out.append((rel, data))
    return out


def manifest(p):
    a = B.AGENTS[p["agent"]]
    return json.dumps({
        "official": True, "firstParty": True, "slug": p["slug"], "name": p["name"],
        "tagline": p["tagline"], "archetype": p["archetype"],
        "publisher": {"name": "Hanzo AI, Inc.", "url": "https://hanzo.ai"},
        "builtBy": {"handle": p["agent"], "name": a["name"], "type": "ai-agent",
                    "discipline": a["discipline"], "profile": a["profile"],
                    "human": False, "independentThirdParty": False},
        "forkedFrom": {"template": p["template"],
                       "source": "https://github.com/hanzo-templates/" + p["template"],
                       "via": "POST /v1/projects/fork",
                       "derived": "built from the template source and rebuilt"},
        "runtime": ["https://a.hanzo.ai/analytics.js", "https://a.hanzo.ai/chat.js"],
        "syntheticData": True, "notice": B.NOTICE,
    }, indent=2).encode()


def upload(p, entries):
    """Publish through POST /v1/projects/<slug>/deploy — the ARTIFACT lane, which
    is the binary-safe one. The JSON file-manifest lane cannot carry a woff2."""
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tf:
        for rel, data in entries:
            ti = tarfile.TarInfo(rel)
            ti.size = len(data)
            ti.mtime = 0
            tf.addfile(ti, io.BytesIO(data))
    req = urllib.request.Request(
        "https://api.hanzo.ai/v1/projects/%s/deploy" % p["slug"], data=buf.getvalue(),
        method="POST", headers={"Authorization": "Bearer " + B.TOKEN, "X-Org-Id": "hanzo",
                                "Content-Type": "application/gzip"})
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            return r.status, ""
    except urllib.error.HTTPError as e:
        return e.code, e.read()[:200].decode("utf-8", "replace")
    except Exception as e:
        return 0, str(e)[:200]


def one(p, diff_only=False):
    d = os.path.join(TPL, p["derive"]["repo"])
    if not os.path.isdir(os.path.join(d, ".git")):
        return p["slug"], "no template checkout at " + d, ""
    reset(d)
    edited = brand(d, p) + content(d, p)
    stat = git(d, "diff", "--stat").strip().splitlines()
    diff = stat[-1].strip() if stat else "no change"
    if diff_only:
        return p["slug"], "diff-only", diff
    root, rc, err = buildsite(d)
    if not root:
        return p["slug"], "BUILD FAILED rc=%s %s" % (rc, err.replace("\n", " ")[:180]), diff
    fs = files(os.path.join(d, root), p)
    fs.append((".well-known/hanzo-example.json", manifest(p)))
    code, err = upload(p, fs)
    return p["slug"], "%s https://%s.hanzo.app (%d files from %s/, %d source files edited) %s" % (
        code, p["slug"], len(fs), root, edited, err), diff


def main():
    diff_only = "--diff" in sys.argv
    names = [a for a in sys.argv[1:] if not a.startswith("-")]
    todo = [p for p in B.PRODUCTS if p.get("derive") and (not names or p["slug"] in names)]
    print("deriving %d products from their parent templates\n" % len(todo))
    for p in todo:
        slug, res, diff = one(p, diff_only)
        print("%-13s %-11s %s" % (slug, p["derive"]["repo"], res))
        print("%-13s %-11s diff vs template: %s\n" % ("", "", diff), flush=True)


if __name__ == "__main__":
    main()
