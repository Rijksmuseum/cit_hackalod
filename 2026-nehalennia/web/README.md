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
- **Type** — Iosevka for all three roles, falling back to the system sans.

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

| | |
|---|---|
| `index.html` | the whole page |
| `js/app.js` | [petite-vue](https://github.com/vuejs/petite-vue) app, loaded from a CDN |
| `scss/` | one partial per section |
| `data/timeline.json` | generated — do not edit by hand |
| `data/verhaal.json` | the five story steps, hand-written |
| `maak_demo_data.py` | builds `timeline.json` |

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
- **The board is empty by design.** Three placeholder tabs are wired up; the panel
  is blank. Dropping the real interaction in means filling `.bord__paneel` and
  replacing `BORD_TABS` in `js/app.js`.
- **Only RMO is in the data.** `bronNaam` / `bronLink` are per object and the
  footer reads from a `bronnen` list, so a multi-source set needs no UI changes.

## Notes

- RMO images are CC BY and the credit is required — every card links back to its
  record, and the footer names the source. Keep that if you restyle.
- The RMO image proxy rate-limits when a grid loads at once, and a few images are
  genuinely 403. `beeldMislukt()` in `js/app.js` retries twice, then shows a
  placeholder, so neither case shows a broken-image icon.
- petite-vue (unpkg), Iosevka (jsDelivr / Fontsource) and the images (RMO) are
  all remote, so **the page needs internet**. Worth knowing before demoing on
  venue wifi; self-hosting all three is the fix if that turns out to be a
  problem. Iosevka is not on Google Fonts, hence Fontsource — four stylesheets,
  for 400, 600, 700 and 400-italic.
- `assets/title.gif` is black line art, so it is flipped with `filter: invert(1)`
  to read on the dark background. A light-on-dark original would drop that.
- `<template v-if>` / `<template v-for>` are avoided: petite-vue does not document
  support for them. Use a real element with `v-if` instead.

## Tested

Rendered and checked in headless Chromium: all three timeline states (populated,
paged, empty), the story steps, the board tabs, and the image fallback. Not yet
checked in Firefox or Safari, and not on a real mobile device.
