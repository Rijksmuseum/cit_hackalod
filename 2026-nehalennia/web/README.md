# One-pager (demo)

A single page about Nehalennia: a story in five steps, a placeholder board, and a
timeline of objects. Built for showing the idea, not for production.

## Design

The layout and component patterns follow
[vliegenthert.dekok.xyz](https://vliegenthert.dekok.xyz) — pill buttons, 6px
panels, uppercase accent eyebrow, the image hover treatment. The colours and
type have since moved away from it:

- **Surfaces** — a neutral `hsl(214 10% …)` ramp, `--surface-0` … `--surface-4`,
  built around `#202327`.
- **Accent** — vermilion `#ff5533`, with `--accent-bright` for hover and
  `--op-accent` for text on a filled accent surface.
- **Type** — Source Serif 4 for running text, Source Code Pro for headings. Same
  Adobe superfamily, both variable (weight 200–900), both **self-hosted** from
  `assets/fonts/` with the `@font-face` rules in `scss/_fonts.scss`. SIL OFL 1.1,
  licence in `assets/fonts/OFL.txt`. Two weights carry the page: `--licht` (300)
  for running text and `--halfvet` (600) for headings and UI.

  **ABC Ginto** was considered and dropped: it is a paid Dinamo typeface with no
  free CDN, and the trial licence does not cover public web use. If a licence
  covering web use turns up, add its `@font-face` rules to `_fonts.scss` and
  repoint the three font tokens.

`--foam` / `--text` / `--mute` still carry their original names and a slight
teal tint, left over from the sea palette.

The tokens were read off that site and reimplemented here; none of its CSS is
copied. It is someone else's design (Gerhard de Kok, for the Zeeuws Maritiem
MuZEEum and the Rijksmuseum) — worth checking before this goes anywhere public.

## Running it

The page fetches JSON, so `file://` will not work — serve it over HTTP:

```bash
cd 2026-nehalennia/web
python3 -m http.server 8000
```

Then open <http://localhost:8000/>.

## Hosting

Static, no build step — `css/main.css` is committed and every path is relative,
so the directory can be dropped on any static host, including under a subpath.

Deployed on **Cloudflare Pages**, connected to this (private) repo so the repo
stays private. Settings, when wiring it up:

| | |
|---|---|
| Framework preset | None |
| Build command | *(leave empty)* |
| Build output directory | `2026-nehalennia/web` |
| Root directory | *(leave empty — repo root)* |

Connecting a `Rijksmuseum` repo needs an org admin to approve the Cloudflare
GitHub app once. Netlify works identically if that approval stalls; it reads the
same `_headers` file, it just needs the output directory set in its own UI.

The site is **link-only**: `_headers` sends `X-Robots-Tag: noindex, nofollow`
for every path, and both HTML files carry a matching `<meta name="robots">`.
There is deliberately no `robots.txt` — a `Disallow` would stop crawlers
fetching the pages at all, so they would never see the `noindex` and could still
list the URL from an inbound link. Remove both the header and the meta tags to
make it indexable, but settle the three open items under *Still to do* and the
design credit above before doing that.

`js/app.js` still pulls petite-vue from unpkg and the card images come from RMO,
so the hosted page needs internet just like the local one.

## Regenerating

```bash
# demo data: out/rmo_nehalennia_colijnsplaat.xlsx -> data/timeline.json
python3 -I maak_demo_data.py

# styles: scss/ -> css/main.css
npx sass scss/main.scss css/main.css --no-source-map
```

`css/main.css` is committed so the page opens without a build step. Regenerate it
after editing anything under `scss/`.

## Layout

Two pages, `Verhaal` and `Altaar`, linked by the bar at the top.

| | |
|---|---|
| `index.html` | Verhaal — the story steps and the timeline |
| `altaar.html` | Altaar — intentionally empty, nothing built yet |
| `js/app.js` | [petite-vue](https://github.com/vuejs/petite-vue) app, loaded from a CDN. Only `index.html` uses it |
| `scss/` | one partial per block (`_balk`, `_kop`, `_verhaal`, `_tijdlijn`) |
| `data/timeline.json` | generated — do not edit by hand |
| `data/verhaal.json` | the five story steps, hand-written |
| `maak_demo_data.py` | builds `timeline.json` |

The top bar is duplicated in both HTML files — there is no templating step, so a
change to the nav has to be made twice.

## What is fake, and what is real

**The years are invented.** The objects, titles, images and source links are real
RMO records; the 1950–2000 years they sit under are not. The real dating cannot
drive a timeline — 245 of the 411 records share `Periode = "Romeins 150-250
n.Chr."` and 124 have no date at all. That is one bucket, not a timeline.

When the combined dataset lands, the most promising real axis is the acquisition
year encoded in `Inventarisnummer` (`i 1970/12.7` → 1970), which spreads over
1970, 1971, 1974, 1976, 1982, 1991, 2017, 2018 and matches the Colijnsplaat
story. Note that a naive `\d{4}` also matches non-inventory IDs like `GN-K_1612`,
so that needs an anchored pattern.

`maak_demo_data.py` shapes the per-year counts on purpose so every UI state is
visible: three empty years (1950, 1979, 1989), two years with 25+ objects
(1956, 1986), the rest small. Output is seeded, so reruns are stable.

## Still to do

- **The story text is placeholder.** Written to length and roughly accurate, but
  it has not been checked by anyone who knows the material.
- **`assets/title.gif` is a copy** of `../presentation/title.gif`, duplicated so
  the `web/` directory can be served on its own. Re-copy it if the original changes.
- **`altaar.html` is empty by design.** It has the top bar and an empty `<main>`,
  held open by a `min-height` so it does not collapse to a bare bar. No styles
  and no JS of its own yet.
- **Only RMO is in the data.** `bronNaam` / `bronLink` are per object and the
  footer reads from a `bronnen` list, so a multi-source set needs no UI changes.

## Notes

- RMO images are CC BY and the credit is required — every card links back to its
  record, and the footer names the source. Keep that if you restyle.
- The RMO image proxy rate-limits when a grid loads at once, and a few images are
  genuinely 403. `beeldMislukt()` in `js/app.js` retries twice, then shows a
  placeholder, so neither case shows a broken-image icon.
- The fonts are self-hosted, but **petite-vue (unpkg) and the images (RMO) are
  still remote**, so the page needs internet. Worth knowing before demoing on
  venue wifi; vendoring petite-vue is a one-file fix, the images less so.
- `assets/title.gif` is black line art, recoloured towards the accent by the
  filter chain on `.clipart`. The chain cannot read `var(--accent)` — refit it
  with `tint_filter.py` if the accent changes, and note it renders a little off
  (see that script's docstring).
- **`css/main.css` is generated.** Edit `scss/`, then recompile. Anything written
  straight into `css/main.css` is wiped by the next `sass` run.
- `<template v-if>` / `<template v-for>` are avoided: petite-vue does not document
  support for them. Use a real element with `v-if` instead.

## Tested

Rendered and checked in headless Chromium: all three timeline states (populated,
paged, empty), the story steps, the board tabs, and the image fallback. Not yet
checked in Firefox or Safari, and not on a real mobile device.
