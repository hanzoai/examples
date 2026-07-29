#!/usr/bin/env python3
"""Emit hanzo-app/products.json — the ONE product roster.

Each row: the product's slug (which IS its app source, its host and its project
slug — one name, everywhere), its name, tagline, brand hue + mark, the named
agent that builds it, and the gallery template it is forked from.
"""
import json, os, re, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
APPS = os.path.join(ROOT, "apps")
OUT = os.path.join(ROOT, "products.json")
# The gallery catalog cloud embeds — the ONE list of what a template slug means.
# Read, never copied, so a parent that does not exist fails here instead of
# producing a fork edge that points at nothing.
TPL = os.environ.get("HZ_TEMPLATE_CATALOG",
                     os.path.expanduser("~/work/hanzo/cloud/clients/templates/catalog.json"))

# old-slug, new-slug, Name, hue, mark, agent, template, tagline
R = [
 ("ex-admin","northgate","Northgate",214,"N","atlas","metrics","The admin console for the tables nobody else will look after."),
 ("ex-agent","cog","Cog",268,"C","sage","synapse","An agent that shows its work: every tool call, argument and result, in order."),
 ("ex-apiref","almanac","Almanac",44,"A","muse","changelog","API reference that a human can read and a machine can check."),
 ("ex-arena","skirmish","Skirmish",320,"S","echo","kart-racer","Two-minute multiplayer matches in a browser tab. No install, no lobby."),
 ("ex-askdocs","footnote","Footnote",268,"F","sage","synapse","Ask your documentation a question and get the paragraph it came from."),
 ("ex-assistant","halcyon","Halcyon",268,"H","sage","synapse","A calm assistant: streaming answers, threads that persist, nothing that shouts."),
 ("ex-booking","timeslot","Timeslot",214,"T","nomad","deploy","Pick a slot. That is the whole product, and it is harder than it looks."),
 ("ex-budget","pennyworth","Pennyworth",8,"P","juno","analytics-dashboard","Household budgeting for people who want the envelope back."),
 ("ex-checkout","tender","Tender",8,"T","juno","ecommerce-storefront","A checkout that says the total once and never changes it."),
 ("ex-cms","quill","Quill",44,"Q","muse","blog-platform","Model the content, then edit it. Fields first, WYSIWYG second."),
 ("ex-collab","scribe","Scribe",178,"S","echo","markdown-editor","One document, several cursors, no merge conflicts."),
 ("ex-console","helm","Helm",214,"H","atlas","analytics-dashboard","The SaaS dashboard you can hand to a customer on day one."),
 ("ex-contacts","kith","Kith",214,"K","atlas","beta","Everyone you know, and the last thing you said to them."),
 ("ex-course","syllabus","Syllabus",44,"S","muse","blog-platform","Lessons, progress and a certificate at the end. Learning, not a video wall."),
 ("ex-crm","relay","Relay",214,"R","atlas","beta","A pipeline you can actually move deals through with one hand."),
 ("ex-deck","podium","Podium",28,"P","solaris","mosaic","Slides in the browser. Present, or send the link and let them read it."),
 ("ex-diff","redline","Redline",152,"R","delta","metrics","Code review as a reading experience: the diff, the reason, the decision."),
 ("ex-etl","sluice","Sluice",152,"S","delta","analytics-dashboard","Move data from where it is to where it is useful, and watch it go."),
 ("ex-events","convene","Convene",96,"C","nomad","circle","Publish an event, take RSVPs, and know who is actually coming."),
 ("ex-expenses","outlay","Outlay",8,"O","juno","analytics-dashboard","Receipts in, reimbursement out, with the approval in between."),
 ("ex-feed","current","Current",28,"C","solaris","circle","A feed with a reading position, because you have a life."),
 ("ex-feedback","chorus","Chorus",28,"C","solaris","deploy","Let the people who use it tell you what to build next, and count the votes."),
 ("ex-flags","bellwether","Bellwether",152,"B","delta","metrics","Ship it to one percent first. Feature flags with a blast radius."),
 ("ex-fleet","armada","Armada",200,"A","kestrel","analytics-dashboard","Every machine you run, on one screen, sorted by how worried you should be."),
 ("ex-flow","conduit","Conduit",214,"C","atlas","matrix","Wire steps together and watch the data flow through the graph."),
 ("ex-folio","atelier","Atelier",28,"A","solaris","kinetic","A portfolio that gets out of the way of the work."),
 ("ex-forms","fieldwork","Fieldwork",214,"F","atlas","deploy","Build the form, take the answers, keep the answers."),
 ("ex-forum","commons","Commons",28,"C","solaris","circle","A place to argue in public and still be able to find the thread tomorrow."),
 ("ex-globe","meridian","Meridian",320,"M","iris","three-webgpu","The whole planet at sixty frames a second, with your data on it."),
 ("ex-habit","streaks","Streaks",214,"S","atlas","deploy","Do the thing. Mark the box. Do not break the chain."),
 ("ex-handbook","vellum","Vellum",44,"V","muse","serif","The company handbook, written to be read rather than filed."),
 ("ex-helpdesk","deskline","Deskline",214,"D","atlas","beta","Tickets in, answers out, with a queue that tells the truth."),
 ("ex-i18n","polyglot","Polyglot",152,"P","delta","metrics","Every string, every locale, and the ones nobody translated yet."),
 ("ex-imagine","daydream","Daydream",268,"D","sage","synapse","Describe it, generate it, keep the good ones, and keep the prompt."),
 ("ex-inbox","courier","Courier",178,"C","echo","circle","Messages that arrive while you are looking at them."),
 ("ex-inventory","stockroom","Stockroom",8,"S","juno","unity","What you have, where it is, and how long before you run out."),
 ("ex-invoice","remit","Remit",8,"R","juno","unity","Line items in, PDF out, paid or not paid — nothing else."),
 ("ex-jobs","shortlist","Shortlist",28,"S","solaris","jobfinder","A job board that respects the applicant's afternoon."),
 ("ex-journal","longform","Longform",44,"L","muse","blog-platform","Publishing for people with something long to say."),
 ("ex-jsonlab","sift","Sift",152,"S","delta","metrics","Paste the JSON. Find the field. Copy the path. Get on with it."),
 ("ex-kanban","lanes","Lanes",214,"L","atlas","kanban-board","A board with WIP limits that mean something, because they stop you."),
 ("ex-map","cartograph","Cartograph",96,"C","nomad","three-webgpu","Points, routes and regions on a map you can actually read."),
 ("ex-market","bazaar","Bazaar",8,"B","juno","ecommerce-storefront","A marketplace with two sides and one set of rules."),
 ("ex-meet","roundtable","Roundtable",178,"R","echo","circle","A call that starts when you open the link."),
 ("ex-menu","bistro","Bistro",8,"B","juno","savor","The menu, the table, the order. Nobody downloads an app to eat."),
 ("ex-notes","marginalia","Marginalia",44,"M","muse","markdown-editor","Notes that link to each other, and a backlink panel that earns its space."),
 ("ex-onboard","threshold","Threshold",214,"T","atlas","quantum","The first five minutes of an account, designed like they matter."),
 ("ex-orbit","apogee","Apogee",320,"A","iris","three-webgpu","Orbital mechanics you can drag with a mouse."),
 ("ex-orgchart","trellis","Trellis",214,"T","atlas","unity","Who reports to whom, and who is standing on their own."),
 ("ex-particles","swarm","Swarm",320,"S","iris","three-webgpu","A hundred thousand particles obeying three rules."),
 ("ex-photos","darkroom","Darkroom",28,"D","solaris","mint","A gallery that gives the photograph the whole screen."),
 ("ex-pixels","tessera","Tessera",178,"T","echo","voxel-craft","A shared canvas where every pixel has an owner and a timestamp."),
 ("ex-poll","ballot","Ballot",152,"B","delta","deploy","Ask the room, and watch the bars move while they answer."),
 ("ex-prompts","grimoire","Grimoire",268,"G","sage","synapse","A prompt library with versions, variables and a diff between them."),
 ("ex-pulse","cadence","Cadence",152,"C","delta","analytics-dashboard","The four numbers that matter, above the fold, always."),
 ("ex-qa","quorum","Quorum",28,"Q","solaris","circle","Questions with accepted answers, and a reason the answer was accepted."),
 ("ex-queue","spool","Spool",200,"S","kestrel","metrics","Jobs, retries and the dead-letter queue you have been ignoring."),
 ("ex-regex","needle","Needle",152,"N","delta","markdown-editor","Write the pattern, see the match, understand the group."),
 ("ex-releases","milestone","Milestone",44,"M","muse","changelog","A changelog your users will read, because it is written for them."),
 ("ex-roadmap","compass","Compass",214,"C","atlas","kanban-board","What ships when, and what it is waiting on."),
 ("ex-screen","peek","Peek",178,"P","echo","video-streaming","Share the screen, record the screen, send the file."),
 ("ex-sheets","gridline","Gridline",178,"G","echo","metrics","A spreadsheet several people can be wrong in at the same time."),
 ("ex-shell","cutlass","Cutlass",152,"C","delta","metrics","A companion for the command line that remembers what you ran."),
 ("ex-shop","kindling","Kindling",8,"K","juno","hygge","A storefront small enough to launch this afternoon."),
 ("ex-studio","reverb","Reverb",320,"R","iris","video-streaming","A player with a waveform, because audio is a shape."),
 ("ex-terrain","highland","Highland",320,"H","iris","three-webgpu","Generated landscape you can fly over, seeded by a number."),
 ("ex-timezones","antipode","Antipode",96,"A","nomad","deploy","What time it is for everyone else, before you send the invite."),
 ("ex-tokens","tincture","Tincture",320,"T","iris","blocks","Design tokens with contrast checked at the point you pick the colour."),
 ("ex-uptime","watchtower","Watchtower",200,"W","kestrel","changelog","A status page that is honest during the incident, not after it."),
 ("ex-vectors","lodestone","Lodestone",268,"L","sage","synapse","Embedding search you can inspect: the vector, the neighbours, the distance."),
 ("ex-video","reel","Reel",28,"R","solaris","video-streaming","Video streaming with a shelf, a player and a resume position."),
 ("ex-voxel","cubit","Cubit",320,"C","iris","voxel-craft","Build a world one cube at a time, then walk around inside it."),
 ("ex-waitlist","liftoff","Liftoff",28,"L","solaris","launch","A launch page with one job: take the email address."),
 ("ex-whiteboard","slate","Slate",178,"S","echo","canvas","A whiteboard that several people can draw on without fighting."),
]

META = re.compile(r"^<!--hz\s*(\{.*?\})\s*-->", re.S)

# The agent's edit, per derived product: which parent checkout to build from and
# the copy rewrites that turn the template's demo content into the product's.
# Only products listed here ship TEMPLATE-DERIVED bytes; every other product
# carries the recorded fork edge but ships the kit build. Being explicit about
# which is which is the point — an unmarked mixture is how "scaffolding" got
# called "an app" in the first place.
D = {
 "lanes": {"repo": "kanban-board", "replace": [
   ["Project Board", "Lanes"],
   ["Implement user authentication", "Ship release retention GC"],
   ["Add login/logout functionality using @hanzo/ui forms",
    "Prune releases past the keep window; activate verifies bytes first"],
   ["Design dashboard layout", "Rate-limit anonymous submissions"],
   ["Create responsive dashboard using @hanzo/ui components",
    "Per-IP token bucket in front of the public Base collection"],
   ["Sarah Chen", "Ada L"], ["Alex Rivera", "Grace H"], ["Jordan Park", "Linus T"],
   ["Emily Davis", "Barbara L"], ["Michael Kim", "Ken T"]]},
 "longform": {"repo": "blog-platform", "replace": [
   ["Hanzo Blog", "Longform"],
   ["Sarah Chen", "Ada L"], ["Alex Rivera", "Grace H"], ["Jordan Park", "Linus T"],
   ["Senior Developer Advocate", "Writes about systems that outlive their authors"],
   ["Design Systems at Scale", "What a design system owes its readers"]]},
 # milestone is NOT derived: the changelog template carries a dynamic
 # opengraph-image route, so `output: 'export'` fails at build. Degrading the
 # template to make the derivative work would be the wrong trade — the product
 # keeps its recorded fork edge and ships the kit build.
 "cadence": {"repo": "analytics-dashboard", "replace": [
   ["Analytics Dashboard", "Cadence"],
   ["Total Revenue", "Revenue"], ["Active Now", "Online now"],
   ["Olivia Martin", "Ada L"], ["Jackson Lee", "Grace H"],
   ["Isabella Nguyen", "Linus T"], ["William Kim", "Barbara L"],
   ["Sofia Davis", "Ken T"]]},
 "marginalia": {"repo": "markdown-editor", "replace": [
   ["Markdown Editor", "Marginalia"],
   ["Edit Only", "Write"], ["Split View", "Side by side"], ["Preview Only", "Read"]]},
 # synapse still carries the upstream vendor's brand ("Brainwave") in 26 files.
 # Rebranding it to the product is both the agent's edit and the removal of a
 # third-party name from a Hanzo template.
 "halcyon": {"repo": "synapse", "replace": [
   ["Brainwave", "Halcyon"], ["AI UI Kit", "a calm assistant"]]},
 "reel": {"repo": "video-streaming", "replace": [
   ["Related Videos", "Up next"],
   ["Advanced React Patterns", "How a static host serves 74 products"],
   ["Tailwind CSS Mastery", "Content-addressed releases, end to end"],
   ["State Management in 2024", "What a fork edge is actually for"],
   ["Code Academy", "Hanzo Engineering"], ["Design Pro", "Hanzo Engineering"]]},
 "bazaar": {"repo": "ecommerce-storefront", "replace": [
   [">Store<", ">Bazaar<"],
   ["Premium Wireless Headphones", "Field Recorder"],
   ["Smart Watch Pro", "Pocket Barometer"],
   ["Portable Speaker", "Shortwave Radio"],
   ["Laptop Stand", "Folding Desk Stand"]]},
}


def main():
    tpl = {t["slug"] for t in json.load(open(TPL))}
    agents = json.load(open(os.path.join(os.path.dirname(OUT), "agents.json")))["agents"]
    seen, out = set(), []
    for _old, slug, name, hue, mark, agent, parent, tagline in R:
        src = os.path.join(APPS, slug + ".html")
        assert os.path.exists(src), f"missing app {src}"
        assert agent in agents, f"unknown agent {agent}"
        assert parent in tpl, f"unknown template {parent}"
        assert slug not in seen, f"duplicate slug {slug}"
        assert re.fullmatch(r"[a-z0-9]([a-z0-9-]{0,38}[a-z0-9])?", slug), slug
        seen.add(slug)
        m = META.match(open(src, encoding="utf-8").read())
        h = json.loads(m.group(1))
        out.append({
            "slug": slug, "name": name, "tagline": tagline, "hue": hue,
            "mark": mark, "agent": agent, "template": parent,
            "archetype": h.get("archetype", ""),
            "nav": h.get("nav", [["#/", "Home"]]),
            "desc": h.get("desc", ""),
            **({"derive": D[slug]} if slug in D else {}),
        })
    assert len(out) == 74, len(out)
    json.dump({"products": out}, open(OUT, "w"), indent=1)
    print(f"wrote {OUT}: {len(out)} products, "
          f"{len({p['agent'] for p in out})} agents, "
          f"{len({p['template'] for p in out})} parent templates")


if __name__ == "__main__":
    main()
