#!/usr/bin/env python3
"""gallery.py — generate apps/examples.html from the app sources.

The gallery is not a hand-maintained list: it is derived from the `<!--hz {...}-->`
header of every app plus the last verify.json run, so a card can never claim an
app exists that was never published, and the archetype/creator facets stay in
step with the apps themselves. It is then PUBLISHED by build.py like any other
app — one deploy path, no special case.
"""
import json
import os
import re

ROOT = os.path.dirname(os.path.abspath(__file__))
META = re.compile(r"^<!--hz\s*(\{.*?\})\s*-->", re.S)

apps = []
for f in sorted(os.listdir(os.path.join(ROOT, "apps"))):
    if not f.endswith(".html") or f == "examples.html":
        continue
    m = META.match(open(os.path.join(ROOT, "apps", f), encoding="utf-8").read())
    if not m:
        continue
    meta = json.loads(m.group(1))
    meta["slug"] = f[:-5]
    apps.append(meta)

verified = {}
vp = os.path.join(ROOT, "verify.json")
if os.path.exists(vp):
    verified = {r["slug"]: r for r in json.load(open(vp))}

# Only advertise what a real browser confirmed renders. An unverified app is
# omitted rather than listed with a caveat — the gallery is a promise.
live = [a for a in apps if verified.get(a["slug"], {}).get("ok")]

CREATORS = {
    "web": "Hanzo Examples — Web Studio",
    "apps": "Hanzo Examples — App Studio",
    "ai": "Hanzo Examples — AI Studio",
    "live": "Hanzo Examples — Realtime Studio",
    "gfx": "Hanzo Examples — Graphics Studio",
    "data": "Hanzo Examples — Data Studio",
}

head = {"title": "Hanzo Examples", "archetype": "gallery", "creator": "web",
        "desc": "Every official first-party Hanzo example app: {} live demos across {} "
                "archetypes, each published through POST /v1/sites/deploy and backed by "
                "@hanzo/base.".format(len(live), len({a["archetype"] for a in live})),
        "nav": [["#/", "All"]]}

body = """
<div class="row" style="margin-bottom:6px">
  <h1 style="margin:0">Official Hanzo examples</h1>
  <span class="tag acc" id="n"></span>
  <span class="spacer"></span>
  <input id="q" placeholder="Search examples…" style="max-width:250px">
</div>
<p style="max-width:74ch">Every app below is a <b>first-party Hanzo example</b> published by Hanzo AI,
not independent community content. Each one is a live site on <code>hanzo.app</code>, published through
<code>POST /v1/sites/deploy</code>, backed by <code>@hanzo/base</code> for its data, and carrying the
shared <code>a.hanzo.ai</code> analytics and chat runtime. Every app also serves a machine-readable
<code>/.well-known/hanzo-example.json</code> declaring <code>official: true</code> and
<code>seeded: true</code>. All records, people and metrics shown inside them are synthetic.</p>
<div class="row" id="facets" style="gap:5px;margin:14px 0"></div>
<div class="grid wide" id="grid"></div>
<div class="pane" style="margin-top:22px"><header>Seeded creator accounts</header>
  <ul class="list" id="creators"></ul>
  <div class="body"><p class="hz-note" style="margin:0">These are Hanzo's own example studios. They are
  labelled as first-party everywhere they appear, carry no invented biography, employer or photograph,
  and are not presented as independent authors.</p></div></div>
<script>
const {h,fill,$,store,avatar,toast} = hz;
const APPS = __APPS__;
const CREATORS = __CREATORS__;
let q='', facet='All';
const FACETS = ['All', ...[...new Set(APPS.map(a=>a.archetype.split(' / ')[0]))].sort()];

function facets(){
  fill($('#facets'), FACETS.map(f=>h('button.sm'+(f===facet?' p':''),
    {onclick:()=>{facet=f;render();}}, f)));
}
function render(){
  const d = APPS.filter(a => (facet==='All'||a.archetype.startsWith(facet)) &&
    (!q || (a.title+' '+a.archetype+' '+a.desc).toLowerCase().includes(q)));
  $('#n').textContent = d.length+' live example'+(d.length===1?'':'s');
  fill($('#grid'), d.length ? d.map(a=>h('a.card',{href:'https://'+a.slug+'.hanzo.app',
      target:'_blank', rel:'noopener', style:{textDecoration:'none',color:'inherit'}},
    h('div',{style:{height:'6px',borderRadius:'99px',marginBottom:'12px',
      background:'linear-gradient(90deg,hsl('+a.hue+' 60% 55%),hsl('+((a.hue+60)%360)+' 60% 45%))'}}),
    h('div.row',{style:{gap:'8px'}}, h('h3',{style:{margin:0}},a.title),
      h('span.spacer'), h('span.hz-official','◆ official')),
    h('div.small.muted',{style:{margin:'4px 0 8px'}}, a.archetype),
    h('p.small',{style:{margin:'0 0 10px'}}, a.desc),
    h('div.row',{style:{gap:'6px'}}, h('span.tag',a.slug+'.hanzo.app'),
      h('span.tag.acc',CREATORS[a.creator].replace('Hanzo Examples — ','')))))
    : h('div.empty','Nothing matches that search.'));
}
fill($('#creators'), Object.entries(CREATORS).map(([k,name])=>h('li',
  avatar(name,30),
  h('div',{style:{minWidth:0}}, h('div.b',name),
    h('div.small.muted','handle hanzo-examples-'+k+' · official: true · seeded: true · first-party')),
  h('span.spacer'),
  h('span.tag', APPS.filter(a=>a.creator===k).length+' apps'))));
$('#q').oninput = e => { q = e.target.value.toLowerCase(); render(); };
facets(); render();
</script>
"""
body = body.replace("__APPS__", json.dumps(
    [{"slug": a["slug"], "title": a["title"], "archetype": a["archetype"],
      "desc": a["desc"], "creator": a["creator"],
      "hue": (sum(ord(c) for c in a["slug"]) * 37) % 360} for a in live],
    separators=(",", ":")))
body = body.replace("__CREATORS__", json.dumps(CREATORS, separators=(",", ":")))

out = "<!--hz " + json.dumps(head) + " -->\n" + body
open(os.path.join(ROOT, "apps", "examples.html"), "w", encoding="utf-8").write(out)
print("gallery: %d live of %d apps, %d archetypes" % (
    len(live), len(apps), len({a["archetype"] for a in live})))
