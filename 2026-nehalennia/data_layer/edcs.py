"""Match inscription transcriptions to the Epigraphik-Datenbank Clauss/Slaby (EDCS).
"""

import difflib
import re
import unicodedata
from pathlib import Path

import pandas as pd

WORKBOOK = Path("enrichment/edcs_nehalennia_analyse.xlsx")
SHEET = "Inscripties"
ID_COLUMN = "EDCS ID"
TEXT_COLUMN = "Inscription text"
MONUMENT_URL = "https://edcs.hist.uzh.ch/monument/{}"  

MIN_SCORE = 0.78
MIN_LENGTH = 10  

_CORRECTION = re.compile(r"<[^<>]*?=([^<>]*)>")  
_EXPANSION = re.compile(r"\([^()]*\)")  
_NONLETTER = re.compile(r"[^a-z]")
_FOLD = str.maketrans("vj", "ui")  
_ID = re.compile(r"EDCS-(\d+)", re.I)


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


def load(workbook=WORKBOOK):
    frame = pd.read_excel(workbook, sheet_name=SHEET)
    frame["normalised"] = frame[TEXT_COLUMN].map(normalise)
    return frame[frame["normalised"].str.len() > 0].reset_index(drop=True)


def best_match(text, inscriptions):
    needle = normalise(text)
    if len(needle) < MIN_LENGTH:
        return None, None
    score, edcs_id = max(
        (difflib.SequenceMatcher(None, needle, normalised).ratio(), edcs_id)
        for normalised, edcs_id in zip(inscriptions["normalised"], inscriptions[ID_COLUMN])
    )
    return (edcs_id, round(score, 3)) if score >= MIN_SCORE else (None, round(score, 3))


def enrich(frame, column="inscripties", workbook=WORKBOOK, progress=True):
    inscriptions = load(workbook)
    matches = [best_match(text, inscriptions) for text in frame[column]]

    frame = frame.copy()
    frame["edcs_id"] = [edcs_id for edcs_id, _ in matches]
    frame["edcs_pid"] = frame["edcs_id"].map(monument_url)
    frame["edcs_score"] = [score for _, score in matches]

    if progress:
        texts = frame[column].notna().sum()
        print(f"{frame['edcs_id'].notna().sum()} of {texts} inscriptions matched to"
              f" {frame['edcs_id'].nunique()} of {len(inscriptions)} EDCS entries", flush=True)
    return frame
