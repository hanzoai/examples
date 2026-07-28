# hanzo-app — 74 products, published by Hanzo, built by named agents

74 live products at `<slug>.hanzo.app`, indexed at **<https://examples.hanzo.app>**.

They used to be called `ex-admin`, `ex-kanban`, `ex-shop` — which is not a name,
it is a filing code, and it told a visitor that what they were looking at was a
sample rather than a thing. Every one of them now has a product identity: a name,
a mark, a hue, a tagline in its own voice, and a byline.

## The byline

> **Lanes** — published by **Hanzo AI**, built by **Atlas**, an AI agent working
> on internal tools.

Three claims, all true, none inflated:

**Published by Hanzo AI.** Machine-readable in three places that cannot be
removed without removing the product: `<meta name="hanzo:official">`, JSON-LD
naming Hanzo AI as publisher, and `/.well-known/hanzo-example.json`. The
`official` flag on the *project record* is not set from here and cannot be —
api.hanzo.ai gates it on a SuperAdmin principal. It is declared platform-side in
`cloud/clients/projects/firstparty.json` off the same slugs, and
`build.py --verify-official` asserts the two halves agree.

**Built by a named agent.** Ten agents (`agents.json`), each with a discipline
and a body of work, each with a generated avatar. They are described as what they
are — AI agents — and never dressed as people. No biography, no employer, no
photograph, no testimonial. HIP-903, *The Agentic Company*: an agent that
genuinely built the thing needs none of that, and inventing it would turn a true
story into a false one.

**Forked from a template.** Every product's project was created by
`POST /v1/projects/fork` from a gallery template, so `projects.forked_from` is a
fact the platform recorded at fork time rather than a claim this repo makes about
itself. 74/74 carry that edge across 28 distinct parent templates.

## Two kinds of product

**Derived (6).** `derive.py` checks out the parent template, applies the agent's
edit to its **source**, runs the template's own build, and publishes that output.
The `git diff` it prints is the point: it is simultaneously the proof the product
is a derivative and the proof a template is agent-editable.

    lanes      ← kanban-board          4 files changed, 27 insertions(+), 19 deletions(-)
    longform   ← blog-platform         5 files changed, 44 insertions(+), 36 deletions(-)
    bazaar     ← ecommerce-storefront  5 files changed, 30 insertions(+), 22 deletions(-)
    marginalia ← markdown-editor       6 files changed, 25 insertions(+), 17 deletions(-)
    cadence    ← analytics-dashboard   6 files changed, 31 insertions(+), 23 deletions(-)
    reel       ← video-streaming       6 files changed, 49 insertions(+), 41 deletions(-)

The edit has two halves. **Brand** is generic — metadata becomes the product's,
the design system's `--primary`/`--ring` become its hue, hard-coded accent
utilities (`bg-amber-600` on a CTA) are pointed at the token instead, and the
byline is rendered *by the template* rather than stapled onto its output, because
a Next.js app owns `<body>` after hydration and drops anything it did not render.
**Content** is per-product `replace` pairs in `products.json`.

Doing this found real defects the pre-built demos were hiding: four templates did
not compile at all (`Module not found: '@/components/ui/…'` — the dependency was
declared and the wrapper was never committed), and several 404'd on an
`/api/placeholder/…` route that does not exist on a static host. Both are fixed:
the wrappers upstream in `hanzo-templates/*`, the placeholders in the agent's edit.

**Kit-built (68).** The product's app is one file, `apps/<slug>.html`, on the
shared kit. Their fork edge is recorded and honest, but their bytes come from the
kit, not from the parent's source. That gap is stated here rather than papered
over.

## Shape

    products.json  the ONE roster: slug, name, tagline, hue, mark, agent,
                   parent template, and (for the 6) the agent's edit
    agents.json    the ten agents: name, discipline, profile, hue
    kit/hz.css     one stylesheet: tokens + the primitives every archetype uses
    kit/hz.js      one runtime: DOM helpers, a persisted store, deterministic
                   demo data, chart marks, a data grid, a router, and the ONE
                   backend call — @hanzo/base
    apps/<slug>.html   one file per product: `<!--hz {...}-->` + body + <script>
    build.py       fork → compose → syntax-gate → POST /v1/sites/deploy
    derive.py      reset → agent edit → template's own build → artifact deploy
    verify.py      the quality gate: a real browser must render it
    gallery.py     derives apps/examples.html from products.json + verify.json

One slug names all three: the source file, the project, and the host.

## The three invariants

**One deploy path.** Every product — including the gallery — is published through
api.hanzo.ai: `POST /v1/sites/deploy` for a file manifest, `POST
/v1/projects/<slug>/deploy` for a built artifact (the binary-safe lane, which is
what a `woff2` needs). There is no third path and no path that is not the API.

**One backend.** Every product that stores anything calls
`POST /v1/base/collections/submissions/records` on **its own origin** — `@hanzo/base`
through host-as-project-ref (HIP-0014), so an anonymous page persists a real
record with no credential in the page and no bespoke backend.

**One runtime.** `a.hanzo.ai/analytics.js` and `a.hanzo.ai/chat.js`, injected by
the shell, never vendored, so the runtime is updated in one place instead of 74.

## Gates

`build.py` refuses to publish a page whose script does not parse (`node --check`).

`derive.py` treats a non-zero build exit as fatal even when `out/` exists — `out/`
is gitignored, so it survives `git clean` from the previous run, and trusting its
presence is exactly how a failed build ships yesterday's bytes under today's
brand. That is not hypothetical; it happened here, and this is the fix.

`verify.py` drives headless Chromium against the **live** URL and requires HTTP
200, no page or console error, ≥25 elements, ≥120 characters of visible text, a
visible Hanzo-product badge, and — for canvas products — measured pixel variance,
because a canvas that renders a flat fill is a blank 200 with extra steps.

Nothing here fabricates proof about Hanzo or its agents: no invented adoption
numbers, no testimonials, no human credentials behind an agent. The *contents*
of a demo are openly synthetic — placeholder names on generated avatars,
`.invalid` addresses, seeded metrics, a storefront's ratings — and every page
says so in its footer and in its manifest (`"syntheticData": true`).
