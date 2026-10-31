"""Match objects to the timeline periods in presentation_layer/data/perioden.json.

An object lands in a period when one of its date spans overlaps the period's
datum_van..datum_tot. RMO objects carry two spans, their dating and their find date, so
an altar made around 200 and dredged up in 1970 belongs to both "200" and "20ste".
"""

import json
from pathlib import Path

import pandas as pd

PERIODEN = Path("../presentation_layer/data/perioden.json")

DATE_SPANS = [
    ("datering_datum_start", "datering_datum_eind"),
    ("gevonden_datum_van", "gevonden_datum_tot"),
]


def load(path=PERIODEN):
    return json.loads(Path(path).read_text(encoding="utf-8"))["perioden"]


def _year(value):
    try:
        year = int(value)
    except (TypeError, ValueError):
        return None
    return year or None  # 0 is how both sources write an unknown year


def _spans(row):
    for start, end in DATE_SPANS:
        van, tot = _year(row.get(start)), _year(row.get(end))
        if van or tot:
            yield min(van or tot, tot or van), max(van or tot, tot or van)


def period_ids(row, perioden):
    found = []
    for period in perioden:
        if any(van <= period["datum_tot"] and tot >= period["datum_van"]
               for van, tot in _spans(row)):
            found.append(period["period_id"])
    return found


def assign(frame, path=PERIODEN, progress=True):
    perioden = load(path)
    frame = frame.copy()
    frame["period_ids"] = [period_ids(row, perioden) for _, row in frame.iterrows()]

    if progress:
        matched = frame["period_ids"].str.len().gt(0).sum()
        print(f"{matched} of {len(frame)} objects placed in a period", flush=True)
    return frame
