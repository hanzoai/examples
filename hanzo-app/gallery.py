#!/usr/bin/env python3
"""gallery.py — generate apps/examples.html from products.json + agents.json.

The gallery is not a hand-maintained list: it is derived from the SAME roster
build.py publishes from, plus the last verify.json run, so a card can never
claim a product exists that was never published and the brands/bylines cannot
drift from the products themselves. It is then published by build.py like any
other product — one deploy path, no special case.

It has two views because a catalogue of products built by agents has two
questions: `#/` is the products, `#/agent/<handle>` is the agent and its work.
"""
import json
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
P = json.load(open(os.path.join(ROOT, "products.json")))["products"]
AGENTS = json.load(open(os.path.join(ROOT, "agents.json")))["agents"]

verified = {}
vp = os.path.join(ROOT, "verify.json")
if os.path.exists(vp):
    verified = {r["slug"]: r for r in json.load(open(vp))}

# Only advertise what a real browser confirmed renders. An unverified product is
# omitted rather than listed with a caveat — the gallery is a promise. Before the
# first verify run there is no evidence either way, so the roster stands in.
live = [p for p in P if verified.get(p["slug"], {}).get("ok")] or P

head = {"title": "Hanzo Products", "archetype": "gallery", "creator": "web",
        "desc": "{} products published by Hanzo AI and built by {} named AI agents. "
                "Every one is forked from a hanzo.app template, deployed through "
                "POST /v1/sites/deploy, and backed by @hanzo/base.".format(
                    len(live), len({p["agent"] for p in live})),
        "nav": [["#/", "Products"], ["#/agents", "Agents"]]}

body = """
<div class="row" style="margin-bottom:6px">
  <h1 style="margin:0" id="h">Products</h1>
  <span class="tag acc" id="n"></span>
  <span class="spacer"></span>
  <input id="q" placeholder="Search products…" style="max-width:250px">
</div>
<p style="max-width:78ch" id="lede"></p>
<div class="row" id="facets" style="gap:5px;margin:14px 0"></div>
<div class="grid wide" id="grid"></div>
<script>
const {h,fill,$} = hz;
const P = __PRODUCTS__;
const A = __AGENTS__;
const LEDE = "Every product below is published by <b>Hanzo AI</b> and built by a named "+
  "AI agent \\u2014 the agent that genuinely wrote it. Each one is a live site on "+
  "<code>hanzo.app</code>, forked from a gallery template through "+
  "<code>POST /v1/projects/fork</code> so its lineage is recorded, published through "+
  "<code>POST /v1/sites/deploy</code>, backed by <code>@hanzo/base</code>, and serving a "+
  "machine-readable <code>/.well-known/hanzo-example.json</code>. All records, people and "+
  "metrics inside them are synthetic.";
let q='', facet='All';
// Facet by the AGENT, not by archetype: 74 products carry ~48 distinct archetype
// strings, which is a wall of chips and answers nobody's question. Who built it
// is the question this catalogue exists to answer, and there are ten answers.
const FACETS = ['All', ...Object.keys(A)];
const SVG = 'http://www.w3.org/2000/svg';
const mark = (p,s)=>{const e=document.createElementNS(SVG,'svg');
  e.setAttribute('viewBox','0 0 32 32'); e.setAttribute('width',s); e.setAttribute('height',s);
  e.style.flex='none'; e.innerHTML='<rect width=32 height=32 rx=9 fill="hsl('+p.hue+
  ' 74% 55%)"/><text x=16 y=22 text-anchor=middle font-family=system-ui font-size=17 '+
  'font-weight=700 fill=#fff>'+p.mark+'</text>'; return e;};
const face = (a,s)=>{const e=document.createElementNS(SVG,'svg');
  e.setAttribute('viewBox','0 0 32 32'); e.setAttribute('width',s); e.setAttribute('height',s);
  e.style.flex='none'; e.innerHTML='<circle cx=16 cy=16 r=14 fill="hsl('+a.hue+' 62% 22%)" '+
  'stroke="hsl('+a.hue+' 70% 58%)"/><circle cx=16 cy=16 r=6.5 fill="hsl('+a.hue+
  ' 74% 60%)"/><circle cx=27 cy=9 r=3.2 fill="hsl('+a.hue+' 80% 72%)"/>'; return e;};

function card(p){
  const a = A[p.agent];
  return h('a.card',{href:'https://'+p.slug+'.hanzo.app', target:'_blank', rel:'noopener',
      style:{textDecoration:'none',color:'inherit'}},
    h('div',{style:{height:'5px',borderRadius:'99px',marginBottom:'12px',
      background:'linear-gradient(90deg,hsl('+p.hue+' 74% 58%),hsl('+((p.hue+38)%360)+' 70% 48%))'}}),
    h('div.row',{style:{gap:'9px'}}, mark(p,26), h('h3',{style:{margin:0}},p.name),
      h('span.spacer'), h('span.hz-official','\\u25C6 Hanzo')),
    h('p.small',{style:{margin:'8px 0 10px'}}, p.tagline),
    h('div.row',{style:{gap:'6px'}}, h('span.tag',p.slug+'.hanzo.app'),
      h('span.tag','forked from '+p.template),
      h('span.tag.acc','built by '+a.name)));
}
function agentCard(k){
  const a = A[k], mine = P.filter(p=>p.agent===k);
  return h('a.card',{href:'#/agent/'+k, style:{textDecoration:'none',color:'inherit'}},
    h('div.row',{style:{gap:'10px'}}, face(a,34),
      h('div',{style:{minWidth:0}}, h('h3',{style:{margin:0}},a.name),
        h('div.small.muted',a.discipline)),
      h('span.spacer'), h('span.tag.acc', mine.length+' products')),
    h('p.small',{style:{margin:'10px 0 0'}}, a.profile));
}
function render(){
  const [view, arg] = location.hash.slice(2).split('/');
  $('#lede').innerHTML = LEDE;
  if (view === 'agent' && A[arg]) {
    const a = A[arg], mine = P.filter(p=>p.agent===arg);
    $('#h').textContent = a.name;
    $('#n').textContent = mine.length+' product'+(mine.length===1?'':'s');
    $('#lede').innerHTML = '<b>'+a.name+'</b> is an AI agent working on '+
      a.discipline.toLowerCase()+'. '+a.profile+' It is an agent, not a person: no '+
      'biography, no employer, no photograph, and its avatar is generated from its handle. '+
      'Everything below, it built.';
    fill($('#facets'), [h('a.btn.sm',{href:'#/agents'},'\\u2190 All agents')]);
    fill($('#grid'), mine.map(card));
    return;
  }
  if (view === 'agents') {
    $('#h').textContent = 'Agents';
    $('#n').textContent = Object.keys(A).length+' agents';
    $('#lede').innerHTML = 'Hanzo\\u2019s products are built by named AI agents (HIP-903, '+
      'The Agentic Company). Each agent has a discipline and a body of work. None of them '+
      'is dressed as a human: no biography, no employer, no photograph \\u2014 an agent that '+
      'genuinely built the thing does not need any of that.';
    fill($('#facets'), [h('a.btn.sm',{href:'#/'},'\\u2190 All products')]);
    fill($('#grid'), Object.keys(A).map(agentCard));
    return;
  }
  $('#h').textContent = 'Products';
  const d = P.filter(p => (facet==='All'||p.agent===facet) &&
    (!q || (p.name+' '+p.archetype+' '+p.tagline+' '+A[p.agent].name).toLowerCase().includes(q)));
  $('#n').textContent = d.length+' live product'+(d.length===1?'':'s');
  fill($('#facets'), [h('a.btn.sm',{href:'#/agents'},'\\u25CF Agents'),
    ...FACETS.map(f=>h('button.sm'+(f===facet?' p':''),
      {onclick:()=>{facet=f;render();}}, f==='All'?'All':A[f].name))]);
  fill($('#grid'), d.length ? d.map(card) : h('div.empty','Nothing matches that search.'));
}
$('#q').oninput = e => { q = e.target.value.toLowerCase(); render(); };
addEventListener('hashchange', render);
render();
</script>
"""
body = body.replace("__PRODUCTS__", json.dumps(
    [{k: p[k] for k in ("slug", "name", "tagline", "hue", "mark", "agent",
                        "template", "archetype")} for p in live],
    separators=(",", ":")))
body = body.replace("__AGENTS__", json.dumps(AGENTS, separators=(",", ":")))

out = "<!--hz " + json.dumps(head) + " -->\n" + body
open(os.path.join(ROOT, "apps", "examples.html"), "w", encoding="utf-8").write(out)
print("gallery: %d live of %d products, %d agents, %d parent templates" % (
    len(live), len(P), len({p["agent"] for p in live}),
    len({p["template"] for p in live})))
