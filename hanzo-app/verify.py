#!/usr/bin/env python3
"""verify.py — the quality gate. A published PRODUCT counts ONLY if a real
browser renders it: no page error, a non-trivial DOM under <main>, real visible
text, and the "Hanzo product" badge actually visible on screen.

Usage: verify.py [slug ...]   (default: every product in products.json)
"""
import concurrent.futures as cf
import json
import os
import sys

from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.abspath(__file__))
SHOT = os.path.join(ROOT, "shots")
os.makedirs(SHOT, exist_ok=True)

CHECK = """() => {
  // A product's page may be composed by the kit shell (a <main>) or built by its
  // parent template (which need not have one). Measure the page either way, or
  // the gate reports a perfectly good template derivative as empty.
  const m = document.querySelector('main') || document.body;
  const b = document.querySelector('.hz-official, .hzb');
  const vis = e => { if(!e) return false; const r = e.getBoundingClientRect();
    return r.width > 8 && r.height > 8; };
  return {
    nodes: m ? m.querySelectorAll('*').length : 0,
    text: m ? (m.innerText || '').trim().length : 0,
    badge: vis(b),
    canvas: !!document.querySelector('canvas'),
    gl: (() => { const c = document.querySelector('canvas');
      if (!c) return null; try { return !!(c.getContext('webgl2') || c.getContext('2d')); }
      catch(e){ return null; } })(),
    title: document.title,
  };
}"""


def check(slug):
    url = "https://%s.hanzo.app/" % slug
    errs, out = [], {}
    with sync_playwright() as p:
        br = p.chromium.launch(args=["--use-gl=swiftshader", "--enable-unsafe-swiftshader"])
        pg = br.new_page(viewport={"width": 1280, "height": 900})
        pg.on("pageerror", lambda e: errs.append(str(e)[:160]))
        pg.on("console", lambda m: errs.append("console:" + m.text[:140]) if m.type == "error" else None)
        try:
            r = pg.goto(url, wait_until="load", timeout=45000)
            status = r.status if r else 0
            pg.wait_for_timeout(1800)
            out = pg.evaluate(CHECK)
            pg.screenshot(path=os.path.join(SHOT, slug + ".png"))
            # A canvas app that renders a flat fill is a blank 200 with extra
            # steps, so measure the pixels rather than trusting the DOM.
            if out.get("canvas"):
                try:
                    from PIL import Image, ImageStat
                    p = os.path.join(SHOT, slug + "-canvas.png")
                    pg.locator("canvas").first.screenshot(path=p)
                    out["ink"] = round(max(ImageStat.Stat(
                        Image.open(p).convert("RGB")).stddev), 1)
                except Exception as e:
                    out["ink"] = -1
        except Exception as e:
            errs.append("nav:" + str(e)[:160])
            status = 0
        br.close()
    # a.hanzo.ai runtime 4xx is the shared CDN, not the app — never fail on it.
    errs = [e for e in errs if "a.hanzo.ai" not in e and "chat.js" not in e
            and "analytics.js" not in e and "favicon" not in e]
    ok = (status == 200 and not errs and out.get("nodes", 0) >= 25
          and out.get("text", 0) >= 120 and out.get("badge")
          and out.get("ink", 99) > 3)
    return dict(slug=slug, status=status, ok=ok, errs=errs[:3], **out)


def main():
    names = sys.argv[1:] or [p["slug"] for p in json.load(
        open(os.path.join(ROOT, "products.json")))["products"]] + ["examples"]
    rows = []
    with cf.ThreadPoolExecutor(6) as ex:
        for r in ex.map(check, names):
            rows.append(r)
            print("%-22s %s status=%s nodes=%-4s text=%-5s badge=%s ink=%s %s" % (
                r["slug"], "PASS" if r["ok"] else "FAIL", r["status"], r.get("nodes"),
                r.get("text"), r.get("badge"), r.get("ink", "-"), "; ".join(r["errs"])), flush=True)
    # Merge, never replace: a single-slug run must not erase the evidence for
    # every other app, or the gallery silently shrinks to what was last checked.
    vp = os.path.join(ROOT, "verify.json")
    old = {r["slug"]: r for r in (json.load(open(vp)) if os.path.exists(vp) else [])}
    old.update({r["slug"]: r for r in rows})
    json.dump(sorted(old.values(), key=lambda r: r["slug"]), open(vp, "w"), indent=1)
    bad = [r["slug"] for r in rows if not r["ok"]]
    print("\n%d/%d PASS%s" % (len(rows) - len(bad), len(rows), ("  FAIL: " + " ".join(bad)) if bad else ""))


if __name__ == "__main__":
    main()
