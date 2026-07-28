# hanzo-app — the official first-party example apps

74 live example applications published at `<slug>.hanzo.app`, indexed at
**<https://examples.hanzo.app>**.

These are **first-party Hanzo examples**, not community content. Every app says
so, in three places that cannot be removed without removing the app:

- a visible `Hanzo Example · official` badge in the header **and** the footer,
- `<meta name="hanzo:official" content="true">` plus `hanzo:seeded`,
  `hanzo:first-party` and `hanzo:creator` in the document head, and JSON-LD
  naming Hanzo AI as publisher,
- a machine-readable `/.well-known/hanzo-example.json` on every app declaring
  `official: true`, `seeded: true`, `firstParty: true`, `syntheticData: true`,
  and the seeded creator account with `independentThirdParty: false`.

None of it is per-app: the labelling lives in `build.py`'s shell, which is the
only way an app is built, so an unlabelled example cannot be published.

Nothing here fabricates social proof. There are no invented biographies,
employers, photographs, testimonials, star counts or download counts. People in
the demo data are placeholder names on generated initial avatars, addresses use
the reserved `.invalid` domain, and every metric is generated from a fixed seed
and says so on the page.

## Shape

    kit/hz.css   one stylesheet: tokens + the primitives every archetype composes from
    kit/hz.js    one runtime: DOM helpers, a persisted store, deterministic demo
                 data, four inline-SVG chart marks, a data grid, a hash router,
                 and the ONE backend call — @hanzo/base
    apps/*.html  one file per app: an `<!--hz {...}-->` header + body + <script>
    build.py     compose → syntax-gate → POST /v1/sites/deploy
    verify.py    the quality gate: a real browser must render it
    gallery.py   derives apps/examples.html from the app headers + verify.json

## The three invariants

**One deploy path.** Every app — including the gallery — is published by
`POST https://api.hanzo.ai/v1/sites/deploy` with a `{slug, name, files[]}`
manifest. There is no second path.

**One backend.** Every app that stores anything calls
`POST /v1/base/collections/submissions/records` on **its own origin**. That is
`@hanzo/base` reached through host-as-project-ref (HIP-0014): a published
`<slug>.hanzo.app` host serves the org's Base, so an anonymous page persists a
real record with no credential in the page and no bespoke backend.

**One runtime.** Every app loads `a.hanzo.ai/analytics.js` and
`a.hanzo.ai/chat.js` from the shared host — injected by the shell, never
vendored, so the runtime is updated in one place instead of 74.

## Gates

`build.py` refuses to publish a page whose script does not parse (`node --check`).
A syntax error ships a 200 that renders nothing, which is exactly the failure
mode this catalogue exists to avoid, so the check belongs before the deploy.

`verify.py` drives headless Chromium against the **live** URL and requires:
HTTP 200, no page or console error, ≥25 elements and ≥120 characters of visible
text under `<main>`, the official badge visibly rendered, and — for any app with
a canvas — pixel standard deviation above 3, so a flat fill cannot pass as a
render. `gallery.py` lists only what that run confirmed.

## Running it

    python3 build.py [slug ...]     # compose + publish (all apps when no slug given)
    python3 verify.py [slug ...]    # browser-verify the live URLs, write verify.json
    python3 gallery.py              # regenerate apps/examples.html from what passed

`build.py` reads a hanzo-org bearer token from `/home/z/.cache/work/token`; it is
never committed.

## Seeded creator accounts

Six first-party Hanzo studios, named as what they are, with no invented human
identity: `hanzo-examples-web`, `-apps`, `-ai`, `-live`, `-gfx`, `-data`. Each
carries `official: true` / `seeded: true` in every app manifest it publishes and
is listed with those flags on the gallery.
