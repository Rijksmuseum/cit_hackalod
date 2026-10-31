"""Group the objects that stand for the same altar, across RMO and RMA.

Two reasons put objects in a group:
* a Rijksmuseum record cites an RMO object in link_RMO_objecten (via-onderzoek)
* two objects carry the same EDCS inscription (via-inscriptie)

Flattens into a linked_objecten column so front-end is simpler.
"""

import collections
import re

import pandas as pd

import enrich

VIA_ONDERZOEK = "onderzoek"
VIA_INSCRIPTIE = "inscriptie"
LINK_ORDER = (VIA_ONDERZOEK, VIA_INSCRIPTIE)  # the curated reason reads first

RESEARCH_COLUMN = "link_RMO_objecten"
INSCRIPTION_COLUMN = "inscripties"

_URL = re.compile(r"https?://[^\s;|]+")


def _urls(value):
    return _URL.findall(value) if isinstance(value, str) else []


def _by_research(frames):
    """Keyed on the cited RMO object, so everything citing it lands together."""
    groups = collections.defaultdict(set)
    for frame in frames:
        if RESEARCH_COLUMN not in frame.columns:
            continue
        for pid, cited in zip(frame["pid"], frame[RESEARCH_COLUMN]):
            for url in _urls(cited):
                groups[f"onderzoek-{url.rsplit('/', 1)[-1]}"].update({url, pid})
    return groups


def _by_inscription(frames):
    groups = collections.defaultdict(set)
    for frame in frames:
        if INSCRIPTION_COLUMN not in frame.columns:
            continue
        for pid, cell in zip(frame["pid"], frame[INSCRIPTION_COLUMN]):
            for url in _urls(cell):
                edcs_id = enrich.monument_id(url)
                if edcs_id:
                    groups[f"inscriptie-{edcs_id}"].add(pid)
    return groups


def build(frames, progress=True):
    rows = []
    for link_type, groups in ((VIA_ONDERZOEK, _by_research(frames)),
                              (VIA_INSCRIPTIE, _by_inscription(frames))):
        for group_id, pids in sorted(groups.items()):
            if len(pids) < 2:
                continue  # a group of one links nothing
            rows += [{"group_id": group_id, "pid": pid, "link_type": link_type}
                     for pid in sorted(pids)]

    frame = pd.DataFrame(rows, columns=["group_id", "pid", "link_type"])
    if progress:
        sizes = frame.groupby("link_type")["group_id"].nunique().to_dict()
        print(f"{frame['group_id'].nunique()} groups over {frame['pid'].nunique()}"
              f" objects {sizes}", flush=True)
    return frame


def attach(frames, progress=True):
    groups = build(frames, progress=progress)

    related = collections.defaultdict(lambda: collections.defaultdict(set))
    for _, members in groups.groupby("group_id"):
        link_type = members["link_type"].iloc[0]
        pids = sorted(members["pid"])
        for pid in pids:
            for other in pids:
                if other != pid:
                    related[pid][other].add(link_type)

    attached = []
    for frame in frames:
        frame = frame.copy()
        frame["linked_objecten"] = [
            [{"pid": other, "via": via}
             for other, reasons in sorted(related.get(pid, {}).items())
             for via in LINK_ORDER if via in reasons]
            for pid in frame["pid"]
        ]
        attached.append(frame)
    return attached
