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
from const import SEP

VIA_ONDERZOEK = "onderzoek"
VIA_INSCRIPTIE = "inscriptie"
LINK_ORDER = (VIA_ONDERZOEK, VIA_INSCRIPTIE)  # the curated reason reads first

RESEARCH_COLUMN = "link_RMO_objecten"
INSCRIPTION_COLUMN = "inscripties"
SCORE_COLUMN = "edcs_score"
CERTAIN = 1.0  # a link somebody typed by hand, not one the matcher guessed

_URL = re.compile(r"https?://[^\s;|]+")


def _urls(value):
    if isinstance(value, (list, tuple)):
        return [str(url) for url in value]
    return _URL.findall(value) if isinstance(value, str) else []


def _scores(value):
    return [float(part) for part in value.split(SEP)] if isinstance(value, str) else []


def _by_research(frames):
    """Keyed on the cited RMO object, so everything citing it lands together."""
    groups = collections.defaultdict(set)
    for frame in frames:
        if RESEARCH_COLUMN not in frame.columns:
            continue
        for pid, cited in zip(frame["pid"], frame[RESEARCH_COLUMN]):
            for url in _urls(cited):
                groups[f"onderzoek-{url.rsplit('/', 1)[-1]}"].update({url, pid})
    return groups, {}


def _by_inscription(frames):
    """Scores ride along: RMO matched its inscriptions, RMA had them typed in."""
    groups = collections.defaultdict(set)
    scores = {}
    for frame in frames:
        if INSCRIPTION_COLUMN not in frame.columns:
            continue
        matched = (frame[SCORE_COLUMN] if SCORE_COLUMN in frame.columns
                   else [None] * len(frame))
        for pid, cell, joined in zip(frame["pid"], frame[INSCRIPTION_COLUMN], matched):
            confidence = _scores(joined)
            for n, url in enumerate(_urls(cell)):
                edcs_id = enrich.monument_id(url)
                if not edcs_id:
                    continue
                group_id = f"inscriptie-{edcs_id}"
                groups[group_id].add(pid)
                scores[group_id, pid] = confidence[n] if n < len(confidence) else CERTAIN
    return groups, scores


def build(frames, progress=True):
    rows = []
    for link_type, (groups, scores) in ((VIA_ONDERZOEK, _by_research(frames)),
                                        (VIA_INSCRIPTIE, _by_inscription(frames))):
        for group_id, pids in sorted(groups.items()):
            if len(pids) < 2:
                continue  # a group of one links nothing
            rows += [{"group_id": group_id, "pid": pid, "link_type": link_type,
                      "score": scores.get((group_id, pid), CERTAIN)}
                     for pid in sorted(pids)]

    frame = pd.DataFrame(rows, columns=["group_id", "pid", "link_type", "score"])
    if progress:
        sizes = frame.groupby("link_type")["group_id"].nunique().to_dict()
        print(f"{frame['group_id'].nunique()} groups over {frame['pid'].nunique()}"
              f" objects {sizes}", flush=True)
    return frame


def attach(frames, progress=True):
    groups = build(frames, progress=progress)

    related = collections.defaultdict(dict)  # pid -> {(other pid, via): score}
    for _, members in groups.groupby("group_id"):
        link_type = members["link_type"].iloc[0]
        scored = sorted(zip(members["pid"], members["score"]))
        for pid, score in scored:
            for other, other_score in scored:
                if other == pid:
                    continue
                # a link is only as good as its weaker end, and the best group wins
                weakest = min(score, other_score)
                related[pid][other, link_type] = max(
                    related[pid].get((other, link_type), 0), weakest)

    attached = []
    for frame in frames:
        frame = frame.copy()
        column = []
        for pid in frame["pid"]:
            found = related.get(pid, {})
            column.append([
                {"pid": other, "via": via, "score": round(found[other, via], 3)}
                for other in sorted({other for other, _ in found})
                for via in LINK_ORDER if (other, via) in found
            ])
        frame["linked_objecten"] = column
        attached.append(frame)
    return attached
