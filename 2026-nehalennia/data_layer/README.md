# Data layer

Harvests each source, enriches it, links the objects and writes
`../presentation_layer/data/objecten.json`. As of 2026-10-31 that is **459
objects**, 411 from the Rijksmuseum van Oudheden and 48 from the Rijksmuseum
Amsterdam.


For simplicity, entry point is currently `export.ipynb`.
```bash
pip install pandas openpyxl rdflib   # once
```

Hand-made inputs live in `source/` and are committed. Downloads go to `cache/`, which is gitignored and safe to delete.
Each module says at the top what it does. Collectie Zeeland was harvested too, but is not used in the end since it does not feed the export.
