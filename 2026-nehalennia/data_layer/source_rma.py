"""Read the hand-picked Rijksmuseum Amsterdam selection, and fill the gaps the csv
leaves from the Linked Art record behind each pid."""

import json
import time
import urllib.request

import pandas as pd

import enrich
from const import DELAY, CACHE_DIR, SOURCE_DIR, USER_AGENT, make_cache_dir

CSV = SOURCE_DIR / "rma_nehalennia.csv"
BRON = "Rijksmuseum Amsterdam"
INSCRIPTION_COLUMN = "inscripties"
TITLE_COLUMN = "titel"
YEAR_COLUMNS = ("datering_datum_start", "datering_datum_eind")
ENCODING = "cp1252"
DELIMITER = ";"

JSON_LD = "application/ld+json"
HTML = "text/html"

DESCRIPTION = "http://vocab.getty.edu/aat/300435452" 
PRIMARY = "http://vocab.getty.edu/aat/300404670"


def _download(url, cache):
    if not cache.exists():
        make_cache_dir(cache.parent)
        request = urllib.request.Request(
            url, headers={"User-Agent": USER_AGENT, "Accept": JSON_LD})
        with urllib.request.urlopen(request, timeout=60) as response:
            cache.write_bytes(response.read())
        time.sleep(DELAY)
    return json.loads(cache.read_bytes())


def _image_url(record):
    for subject in record.get("subject_of", []):
        for carrier in subject.get("digitally_carried_by", []):
            if (carrier.get("format") or "").startswith(HTML):
                continue  # the object page on rijksmuseum.nl, not the image
            for point in carrier.get("access_point", []):
                if point.get("id"):
                    return point["id"]
    return None


def _types(note):
    return {c.get("id") for c in note.get("classified_as", [])}


def _beschrijving(record):
    notes = [note for note in record.get("referred_to_by", []) if DESCRIPTION in _types(note)]
    best = next((note for note in notes if PRIMARY in _types(note)), notes[0] if notes else None)
    return (best.get("content") or None) if best else None


def _first_line(value):
    return value.split("\n")[0].strip() if isinstance(value, str) else value


def _monuments(value):
    if not isinstance(value, str):
        return []
    parts = (part.strip() for part in value.replace(DELIMITER, "\n").splitlines())
    return [part for part in parts if part.startswith("http")]


def load_csv(path=CSV):
    frame = pd.read_csv(path, sep=DELIMITER, encoding=ENCODING)
    frame.columns = [column.strip() for column in frame.columns]
    return frame


def fetch(path=CSV, cache_dir=CACHE_DIR, progress=True):
    def log(message):
        if progress:
            print(message, flush=True)

    frame = load_csv(path)
    frame["bron"] = BRON
    for column in YEAR_COLUMNS:
        frame[column] = pd.to_numeric(frame[column], errors="coerce").astype("Int64")
    log(f"{len(frame)} rows in {path}")

    images, beschrijvingen = [], []
    started = time.time()
    for n, pid in enumerate(frame["pid"], start=1):
        record = _download(pid, cache_dir / "rma" / f"{pid.rsplit('/', 1)[-1]}.json")
        images.append(_image_url(record))
        beschrijvingen.append(_beschrijving(record))
        if n % 25 == 0 or n == len(frame):
            log(f"  {n:>3}/{len(frame)}  {time.time() - started:.0f}s elapsed")
    frame["image_url"] = images
    frame["beschrijving"] = beschrijvingen

    frame[TITLE_COLUMN] = [_first_line(value) for value in frame[TITLE_COLUMN]]
    frame[INSCRIPTION_COLUMN] = [_monuments(value) for value in frame[INSCRIPTION_COLUMN]]

    # the csv has no transcription of its own, so borrow the one EDCS read off the stone
    inscriptions = enrich.load_inscriptions()
    dutch = enrich.by_id(inscriptions, enrich.TRANSLATION_COLUMN)
    latin = enrich.by_id(inscriptions, enrich.TEXT_COLUMN)
    first = [enrich.monument_id(urls[0]) if urls else None
             for urls in frame[INSCRIPTION_COLUMN]]
    frame["edcs_vertaling_concept"] = [dutch.get(edcs_id) for edcs_id in first]
    frame["inscripties_text"] = [latin.get(edcs_id) for edcs_id in first]

    log(f"{frame['image_url'].notna().sum()} image urls,"
        f" {frame['beschrijving'].notna().sum()} beschrijvingen,"
        f" {frame['edcs_vertaling_concept'].notna().sum()} translations")
    return frame
