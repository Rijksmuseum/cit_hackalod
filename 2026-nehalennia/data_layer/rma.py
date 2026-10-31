"""Read the hand-picked Rijksmuseum (RMA) Nehalennia selection and fill in two gaps.
* image_url, followed from the pid into the Linked Art record at data.rijksmuseum.nl
* edcs_vertaling, joined on the EDCS monument links already in the inscripties column
"""

import json
import time
import urllib.request
from pathlib import Path

import pandas as pd

import edcs

CSV = Path("source/rma_nehalennia.csv")
BRON = "Rijksmuseum Amsterdam"
ENCODING = "cp1252"
DELIMITER = ";"

USER_AGENT = "hackalod-harvester/1.0"
JSON_LD = "application/ld+json"
DELAY = 0.5
HTML = "text/html"


def _download(url, cache):
    if not cache.exists():
        cache.parent.mkdir(parents=True, exist_ok=True)
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


def _first_monument(value):
    """The first EDCS link in a cell that may list one per depicted altar."""
    if not isinstance(value, str):
        return None
    for part in value.replace(DELIMITER, "\n").splitlines():
        if part.strip().startswith("http"):
            return part.strip()
    return None


def load_csv(path=CSV):
    frame = pd.read_csv(path, sep=DELIMITER, encoding=ENCODING)
    frame.columns = [column.strip() for column in frame.columns]
    return frame


def fetch(path=CSV, cache_dir=Path("out"), progress=True):
    def log(message):
        if progress:
            print(message, flush=True)

    frame = load_csv(path)
    frame["bron"] = BRON
    log(f"{len(frame)} rows in {path}")

    images = []
    started = time.time()
    for n, pid in enumerate(frame["pid"], start=1):
        record = _download(pid, cache_dir / "rma" / f"{pid.rsplit('/', 1)[-1]}.json")
        images.append(_image_url(record))
        if n % 25 == 0 or n == len(frame):
            log(f"  {n:>3}/{len(frame)}  {time.time() - started:.0f}s elapsed")
    frame["image_url"] = images

    dutch = edcs.translations(edcs.load())
    frame["edcs_vertaling"] = [
        dutch.get(edcs.monument_id(_first_monument(value))) for value in frame["inscripties"]
    ]

    log(f"{frame['image_url'].notna().sum()} image urls,"
        f" {frame['edcs_vertaling'].notna().sum()} translations")
    return frame
