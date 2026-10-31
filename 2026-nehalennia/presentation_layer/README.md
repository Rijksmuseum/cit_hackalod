# One-pager

Alles staat op één pagina (`index.html`): hero, filmplek, verhaal, tijdlijn,
collectiestukken, altaarbouwer, meer lezen en colofon. `altaar.html` bestaat niet meer.

Serve locally over HTTP:

```bash
cd presentation_layer
python3 -m http.server 8000
```

Regenerate (`css/main.css` and `data/timeline.json` are generated; edit `scss/` and the script):

```bash
npx sass scss/main.scss css/main.css --no-source-map
python3 -I maak_demo_data.py
python3 -I maak_collectie.py pad/naar/edcs_nehalennia_analyse_6.xlsx   # data/collectie.json (concept)
```

`js/altaar.js` is generated from the altar-builder sources (images embedded as WebP).
Not used any more: `assets/title.gif`, `tint_filter.py`, the Source Code Pro fonts (removed).
