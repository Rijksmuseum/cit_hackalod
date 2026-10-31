"""Add the EDCS inscription matches and the timeline periods to a harvested frame."""

import difflib
import json
import re
import unicodedata
from pathlib import Path

import pandas as pd

from const import DATA_DIR, SEP, SOURCE_DIR

WORKBOOK = SOURCE_DIR / "edcs_nehalennia_analyse.xlsx"
SHEET = "Inscripties"
ID_COLUMN = "EDCS ID"
TEXT_COLUMN = "Inscription text"
TRANSLATION_COLUMN = "Nederlandse vertaling (concept)"
MONUMENT_URL = "https://edcs.hist.uzh.ch/monument/{}"

MIN_SCORE = 0.75
EXACT_SCORE = 0.99
MAX_CANDIDATES = 3
MIN_LENGTH = 10

_CORRECTION = re.compile(r"<[^<>]*?=([^<>]*)>")
_EXPANSION = re.compile(r"\([^()]*\)")
_NONLETTER = re.compile(r"[^a-z]")
_FOLD = str.maketrans("vj", "ui")
_ID = re.compile(r"EDCS-(\d+)", re.I)
_URL_ID = re.compile(r"/monument/(\d+)")


def normalise(text):
    if not isinstance(text, str):
        return ""
    text = _CORRECTION.sub(r"\1", unicodedata.normalize("NFKD", text))
    while True:
        text, replaced = _EXPANSION.subn("", text)
        if not replaced:
            break
    return _NONLETTER.sub("", text.lower()).translate(_FOLD)


def monument_url(edcs_id):
    found = _ID.search(edcs_id) if isinstance(edcs_id, str) else None
    return MONUMENT_URL.format(found.group(1)) if found else None


def monument_id(url):
    found = _URL_ID.search(url) if isinstance(url, str) else None
    return f"EDCS-{found.group(1)}" if found else None


def by_id(inscriptions, column):
    return {
        edcs_id: value
        for edcs_id, value in zip(inscriptions[ID_COLUMN], inscriptions[column])
        if isinstance(value, str)
    }


def load_inscriptions(workbook=WORKBOOK):
    frame = pd.read_excel(workbook, sheet_name=SHEET)
    frame["normalised"] = frame[TEXT_COLUMN].map(normalise)
    return frame[frame["normalised"].str.len() > 0].reset_index(drop=True)


def matches(text, inscriptions):
    needle = normalise(text)
    if len(needle) < MIN_LENGTH:
        return []
    scored = sorted(
        ((difflib.SequenceMatcher(None, needle, normalised).ratio(), edcs_id)
         for normalised, edcs_id in zip(inscriptions["normalised"], inscriptions[ID_COLUMN])),
        reverse=True,
    )
    hits = [(edcs_id, score) for score, edcs_id in scored if score >= MIN_SCORE]
    hits = hits[:1] if hits and hits[0][1] > EXACT_SCORE else hits[:MAX_CANDIDATES]
    return [(edcs_id, round(score, 3)) for edcs_id, score in hits]


def edcs(frame, column="inscripties", workbook=WORKBOOK, progress=True):
    inscriptions = load_inscriptions(workbook)
    found = [matches(text, inscriptions) for text in frame[column]]
    dutch = by_id(inscriptions, TRANSLATION_COLUMN)

    def joined(values):
        return SEP.join(values) or None

    frame = frame.copy()
    frame["edcs_id"] = [joined(i for i, _ in hits) for hits in found]
    frame["inscripties"] = [[monument_url(i) for i, _ in hits] for hits in found]
    frame["edcs_score"] = [joined(f"{s:.3f}" for _, s in hits) for hits in found]
    frame["edcs_vertaling_concept"] = [dutch.get(hits[0][0]) if hits else None for hits in found]

    if progress:
        sizes = [len(hits) for hits in found if hits]
        print(f"{len(sizes)} of {frame[column].notna().sum()} inscriptions matched at"
              f" >={MIN_SCORE:.0%}, {sum(sizes) / len(sizes):.0f} candidates each on average,"
              f" worst {max(sizes)} of {len(inscriptions)}", flush=True)
    return frame


PERIODEN = DATA_DIR / "perioden.json"

DATE_SPANS = [
    ("datering_datum_start", "datering_datum_eind"),
    ("gevonden_datum_van", "gevonden_datum_tot"),
]


def load_periods(path=PERIODEN):
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


def periods(frame, path=PERIODEN, progress=True):
    perioden = load_periods(path)
    frame = frame.copy()
    frame["period_ids"] = [period_ids(row, perioden) for _, row in frame.iterrows()]

    if progress:
        matched = frame["period_ids"].str.len().gt(0).sum()
        print(f"{matched} of {len(frame)} objects placed in a period", flush=True)
    return frame
