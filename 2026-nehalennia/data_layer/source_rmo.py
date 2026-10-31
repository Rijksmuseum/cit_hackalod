"""Harvest the Rijksmuseum van Oudheden: its XML search API, plus the object pages
for the acquisition and the main image, which the API does not give."""

import html
import re
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

import pandas as pd

import enrich
from const import DELAY, CACHE_DIR, SEP, USER_AGENT, make_cache_dir

API_URL = "http://api.rmo.nl:17521/"
IMAGE_BASE = "https://www.rmo.nl/imageproxy/"
DETAIL_URL = "https://www.rmo.nl/collectie/collectiezoeker/collectiestuk/?object={}"

PAGE_SIZE = 100

YEAR_COLUMNS = ("datering_datum_start", "datering_datum_eind",
                "gevonden_datum_van", "gevonden_datum_tot")

QUERIES = {
    "nehalennia": None,
    "colijnsplaat": ("Vindplaats", "colijnsplaat"),
}

FIELDS = {
    "objectnummer": "Inventarisnummer",
    "titel": "Titel",
    "objectnaam": "Objectnaam",
    "periode": "Periode",
    "datering_datum_start": "datebegin",
    "datering_datum_eind": "dateend",
    "vindplaats": "Vindplaats",
    "inscripties_text": "Inscripties",
    "beschrijving": "Beschrijving",
    "bron": "europeana_provider",
}

_LIST_ITEM = re.compile(r'<div class="data-list-item">\s*<label>(.*?)</label>(.*?)</div>', re.S)
_MAIN_IMAGE = re.compile(r'<div class="topstuk-main-image">(.*?)</div>', re.S)
_SRC = re.compile(r'(?:data-)?src="/imageproxy/[^"]*?/([^"/]+)"')
_YEAR_RANGE = re.compile(r"(\d{4})\s*-\s*(\d{4})")
_YEAR = re.compile(r"\d{4}")
_TAGS = re.compile(r"<[^>]+>")


def _download(url, cache, decode=False):
    if not cache.exists():
        make_cache_dir(cache.parent)
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(request, timeout=60) as response:
            cache.write_bytes(response.read())
        time.sleep(DELAY)  # be polite
    body = cache.read_bytes()
    return body.decode("utf-8", errors="replace") if decode else body


def _search(query, cache_dir):
    def page(start, end):
        params = (f"action=get&command=search&query={urllib.parse.quote(query)}"
                  f"&range={start}-{end}&fields=*")
        return ET.fromstring(_download(API_URL + params,
                                       cache_dir / "raw" / f"{query}_{start}-{end}.xml"))

    first = page(1, PAGE_SIZE)
    total = int(first.findtext("request/count"))
    pages = [first] + [page(start, min(start + PAGE_SIZE - 1, total))
                       for start in range(PAGE_SIZE + 1, total + 1, PAGE_SIZE)]
    return [record for p in pages for record in p.iter("record")]


def _keep(record, field_filter):
    if field_filter is None:
        return True
    field, value = field_filter
    return any(value.lower() in (el.text or "").lower()
               for el in record.findall(f"data/RMO_XML/{field}"))


def _image_url(filename):
    stem, _, extension = filename.rpartition(".")
    return f"{IMAGE_BASE}{extension.lower()}/{stem}"


def _flatten(record):
    fields, images = {}, []
    for el in record.find("data/RMO_XML"):
        text = (el.text or "").strip()
        if el.tag == "image":
            images.append({"filename": text, "image_url": _image_url(text), **el.attrib})
        else:
            fields.setdefault(el.tag, []).append(text)
    fields = {tag: SEP.join(values) for tag, values in fields.items()}

    row = {"pid": fields.get("europeana_isShownAt")}  # the handle link
    row.update({column: fields.get(field) for column, field in FIELDS.items()})
    row["image_url"] = images[0]["image_url"] if images else None
    for image in images:
        image["pid"] = row["pid"]
    return row, images


def _page(pid, cache_dir):
    object_id = pid.rsplit("/", 1)[-1]  # same number as the API's recordnumber
    return _download(DETAIL_URL.format(object_id),
                     cache_dir / "pages" / f"{object_id}.html", decode=True)


def _main_image(page):
    """The image rmo.nl itself leads with.

    The API lists the images in no useful order, so its first one is the right
    one only about half the time. The page knows which one is the object shot.
    """
    block = _MAIN_IMAGE.search(page)
    found = _SRC.findall(block.group(1)) if block else []
    return _image_url(found[0]) if found else None


def _verwerving(page):
    for label, value in _LIST_ITEM.findall(page):
        if " ".join(html.unescape(label).split()) == "Verwerving":
            return " ".join(html.unescape(_TAGS.sub(" ", value)).split())
    return None


def found_years(verwerving):
    """``(van, tot)`` from the years in a verwerving string.

    ``"opgraving RMO 1970-1971"`` -> ``(1970, 1971)``, ``"aankoop 2017 juli"`` ->
    ``(2017, 2017)``, ``"onbekend"`` -> ``(None, None)``.
    Covers all cases as of the development of this script.
    """
    if not verwerving:
        return None, None
    span = _YEAR_RANGE.search(verwerving)
    if span:
        return int(span.group(1)), int(span.group(2))
    year = _YEAR.search(verwerving)
    return (int(year.group()), int(year.group())) if year else (None, None)


def fetch(queries=QUERIES, cache_dir=CACHE_DIR, progress=True):
    def log(message):
        if progress:
            print(message, flush=True)

    records = {}  # pid -> record element, de-duplicated across queries
    for query, field_filter in queries.items():
        hits = [r for r in _search(query, cache_dir) if _keep(r, field_filter)]
        log(f"{query}: {len(hits)} records")
        for record in hits:
            records.setdefault(record.findtext("data/RMO_XML/europeana_isShownAt"), record)
    log(f"{len(records)} unique records")

    rows, images = [], []
    for record in records.values():
        row, image_rows = _flatten(record)
        rows.append(row)
        images.extend(image_rows)

    log(f"reading {len(rows)} object pages for verwerving and the main image,"
        f" cached ones are reused")
    started = time.time()
    for n, row in enumerate(rows, start=1):
        page = _page(row["pid"], cache_dir)
        row["image_url"] = _main_image(page) or row["image_url"]  # fall back to the API's first
        row["verwerving"] = _verwerving(page)
        row["gevonden_datum_van"], row["gevonden_datum_tot"] = found_years(row["verwerving"])
        if n % 25 == 0 or n == len(rows):
            elapsed = time.time() - started
            log(f"  {n:>4}/{len(rows)}  {elapsed:>4.0f}s elapsed,"
                f" ~{(len(rows) - n) * elapsed / n:.0f}s to go")

    frame = pd.DataFrame(rows)
    for column in YEAR_COLUMNS:
        years = pd.to_numeric(frame[column], errors="coerce").astype("Int64")
        frame[column] = years.mask(years == 0)  # 0 is how the API writes an unknown year

    frame = enrich.edcs(frame, column="inscripties_text", progress=progress)

    image_frame = pd.DataFrame(images)
    image_frame = image_frame[["pid"] + [c for c in image_frame.columns if c != "pid"]]
    return frame, image_frame
