# One-pager
Serve locally over HTTP:

```bash
cd 2026-nehalennia/presentation_layer
python3 -m http.server 8000
```

Then open <http://localhost:8000/>.

Regenerate (`css/main.css` and `data/timeline.json` are both generated — edit
`scss/` and the script, not the output):

```bash
npx sass scss/main.scss css/main.css --no-source-map
python3 -I maak_demo_data.py
```
