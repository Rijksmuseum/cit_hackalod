# One-pager

Alles staat op één pagina (`index.html`): hero, filmplek, verhaal, tijdlijn,
collectiestukken, altaarbouwer, meer lezen en colofon. `altaar.html` bestaat niet meer.

Serve locally over HTTP:

```bash
cd presentation_layer
python3 -m http.server 8000
```

Regenerate (`css/main.css` is generated; edit `scss/`):

```bash
npx sass scss/main.scss css/main.css --no-source-map
```

Data: `data/objecten.json` (alle objecten, koppelingen, opschriften, periodes), `data/perioden.json`, `data/personen.json` (personen en beroepen per inscriptie, afgeleid met `maak_personen.py`; nog te controleren),
`data/verhaal.json`. De collectie leest `objecten.json` rechtstreeks; er is geen bouwscript meer voor.
Vervallen: `data/timeline.json`, `data/collectie.json`, `data/rma_beelden.json`, `maak_demo_data.py`, `maak_collectie.py`.

`js/altaar.js` is generated from the altar-builder sources (images embedded as WebP).
Not used any more: `assets/title.gif`, `tint_filter.py`, the Source Code Pro fonts (removed).
