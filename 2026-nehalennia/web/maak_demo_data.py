"""Some random demo timeline data for the one-pager.
python3 -I maak_demo_data.py
"""

import json
import random
from datetime import date
from pathlib import Path

import pandas as pd

HIER = Path(__file__).parent
XLSX = HIER.parent / "data" / "out" / "rmo_nehalennia_colijnsplaat.xlsx"
UIT = HIER / "data" / "timeline.json"

SEP = " | "  # the harvest joins repeated fields with this separator
EERSTE_JAAR, LAATSTE_JAAR = 1950, 2000
SEED = 42
LEGE_JAREN = 3        # years without objects, to show the empty state
VOLLE_JAREN = 2       # years with 25+ objects, to show multi-page paging
VOLLE_OMVANG = (25, 32)
GEWONE_OMVANG = (1, 10)

BRON = {
    "naam": "Rijksmuseum van Oudheden",
    "licentie": "CC BY",
    "url": "https://www.rmo.nl/",
}


def korte_vindplaats(waarde):
    """'Nederland, Zeeland, Noord-Beveland, Colijnsplaat, Oosterschelde' -> 'Colijnsplaat'.

    The field is Land, Provincie, Gemeente, Plaats and sometimes a fifth detail
    (a water body, a grave number). The place we want is the fourth segment.
    """
    if pd.isna(waarde):
        return None
    eerste = str(waarde).split(SEP)[0]  # a few records list two findspots
    delen = [d.strip() for d in eerste.split(",")]
    plaats = delen[3] if len(delen) >= 4 else delen[-1]
    if plaats.lower() in ("", "onbekend", "nan"):
        return None
    return plaats


def leeg_naar_none(waarde):
    if pd.isna(waarde):
        return None
    tekst = str(waarde).strip()
    return tekst or None


def laad_objecten():
    df = pd.read_excel(XLSX, sheet_name="records")
    df = df[df["image_url"].notna() & df["europeana_isShownAt"].notna()]
    return [
        {
            "id": str(rij["recordnumber"]),
            "titel": leeg_naar_none(rij["Titel"]) or "Zonder titel",
            "objectnaam": leeg_naar_none(rij["Objectnaam"]),
            "materiaal": leeg_naar_none(rij["Materiaal"]),
            "vindplaats": korte_vindplaats(rij["Vindplaats"]),
            "afbeelding": rij["image_url"],
            "bronNaam": BRON["naam"],
            "bronLink": rij["europeana_isShownAt"],
        }
        for _, rij in df.iterrows()
    ]


def verdeel_over_jaren(objecten, rng):
    """Return {jaar: aantal}, with the deliberate mix of empty, full and small years."""
    jaren = list(range(EERSTE_JAAR, LAATSTE_JAAR + 1))
    bijzonder = rng.sample(jaren, LEGE_JAREN + VOLLE_JAREN)
    leeg, vol = bijzonder[:LEGE_JAREN], bijzonder[LEGE_JAREN:]

    aantallen = {}
    for jaar in jaren:
        if jaar in leeg:
            aantallen[jaar] = 0
        elif jaar in vol:
            aantallen[jaar] = rng.randint(*VOLLE_OMVANG)
        else:
            aantallen[jaar] = rng.randint(*GEWONE_OMVANG)

    gevraagd = sum(aantallen.values())
    if gevraagd > len(objecten):
        raise SystemExit(
            f"{gevraagd} objecten nodig maar er zijn er {len(objecten)}; "
            "verlaag GEWONE_OMVANG of VOLLE_OMVANG"
        )
    return aantallen


def main():
    rng = random.Random(SEED)
    objecten = laad_objecten()
    rng.shuffle(objecten)
    aantallen = verdeel_over_jaren(objecten, rng)

    jaren, positie = [], 0
    for jaar in range(EERSTE_JAAR, LAATSTE_JAAR + 1):
        aantal = aantallen[jaar]
        jaren.append(
            {
                "jaar": jaar,
                "onderschrift": f"Demo-onderschrift bij {jaar}.",
                "objecten": objecten[positie : positie + aantal],
            }
        )
        positie += aantal

    UIT.parent.mkdir(parents=True, exist_ok=True)
    UIT.write_text(
        json.dumps(
            {
                "gegenereerd": date.today().isoformat(),
                "demo": True,
                "bronnen": [BRON],
                "jaren": jaren,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    leeg = [j["jaar"] for j in jaren if not j["objecten"]]
    vol = [j["jaar"] for j in jaren if len(j["objecten"]) >= 25]
    print(f"{positie} objecten over {LAATSTE_JAAR - EERSTE_JAAR + 1} jaren -> {UIT}")
    print(f"lege jaren: {leeg}")
    print(f"volle jaren: {vol}")


if __name__ == "__main__":
    main()
