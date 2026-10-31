#!/usr/bin/env python3
"""Leidt per inscriptie de genoemde personen (opdragers) en beroepen/functies af.

Bron: de Latijnse inscripties (inscripties_text) in data/objecten.json. Waar een Nederlandse
vertaling beschikbaar is, helpt die om de afgekorte Latijnse namen uit te schrijven; voor
inscripties zonder vertaling staan de handmatig gelezen gegevens in HANDMATIG hieronder.
Uitvoer: data/personen.json (te controleren door een epigraaf voordat het wordt gepubliceerd).
"""
import json, re, sys

OBJECTEN = sys.argv[1] if len(sys.argv) > 1 else 'data/objecten.json'
UIT = sys.argv[2] if len(sys.argv) > 2 else 'data/personen.json'

# trefwoord in vertaling of Latijn  ->  genormaliseerd beroep/functie
# Herkomst van de Nederlandse termen (nog te controleren door een epigraaf):
#   zouthandelaar, handelaar in vissaus, schipper, handelaar op Brittannië: Varga 2023 (JAHA 14) en de vertalingen in objecten.json
#   consulaire begunstigde: aangeleverd door het team
#   sevir Augustalis, veteraan, handelaar op Kent, klei/aardewerk, beheerder (actor): vertalingen in objecten.json (niet onafhankelijk geverifieerd)
#   decurio: bewust niet vertaald; geen betrouwbare Nederlandse term gevonden
BEROEPEN = [
    (r'zouthandelaar|negotiator salarius|NEGOTIATOR\s*/?\s*SALARIVS|SALARIVS', 'zouthandelaar (negotiator salarius)'),
    (r'handelaren? in vissaus|allecarius|ALLECARIVS', 'handelaar in vissaus (negotiator allecarius)'),
    (r'handelaar in klei|cretarius|CRETARIVS', 'handelaar in klei/aardewerk (negotiator cretarius)'),
    (r'handelaar op Brittannië|Britannicianus|BRITANNICIANV|BRITANNICIA\s*/?\s*NI', 'handelaar op Brittannië (negotiator Britannicianus)'),
    (r'Kent|Cantianus|NEGOT CAN', 'handelaar op Kent (negotiator Cantianus)'),
    (r'schipper|nauta', 'schipper (nauta)'),
    (r'beheerder \(actor\)', 'beheerder (actor)'),
    (r'beneficiarius consularis|EX BF|BF COS|\bBF\b', 'consulaire begunstigde (beneficiarius consularis)'),
    (r'decurio', 'decurio'),
    (r'sevir Augustalis', 'lid van het collegium van de keizercultus (sevir Augustalis)'),
    (r'veteraan|VETERANVS', 'veteraan (veteranus)'),
]
ALGEMEEN = (r'handelaar(?:en)?\b|negotiator|NEGOTIATOR|NEGOTI|NEGOT\b', 'handelaar (negotiator)')

# inscripties zonder (bruikbare) vertaling, of waar de automatische lezing niet volstaat:
# sleutel = herkenbaar stuk Latijn, waarde = (personen, beroepen)
HANDMATIG = {
    'IMMVNI / PRIMVS': (['Primus', 'Ibliomarus'], []),
    'NEVTO LVCANI': (['Neuto'], []),   # let op: de gekoppelde vertaling noemt hier Securus; het Latijn zegt Neuto, zoon van Lucanus
    'Q() B()': (['Marcus Assonius Aelius'], []),
    'MERCATOR / AMABILIS': (['Mercatorius Amabilis'], []),
    'EXOMNIVS / ISAVRICI': (['Exomnius'], []),
    'Q . PHOEB . HILARVS / D M B': (['Quintus Phoebius Hilarus'], ['decurio']),
    'C CRE / SCENTIVS FLO': (['Gaius Crescentius Florus'], []),
    'C . VITALINIVS': (['Gaius Vitalinius Genialis'], []),
    'MEMNON': (['Memnon'], []),
    'AES[....] / IVNI SILVISERVS': (['Aestivus Iunius', 'Silviserus', 'Manchissa'], []),
    'RAVRACORVM': (['Marcellus'], ['lid van het collegium van de keizercultus (sevir Augustalis)']),
    'GALLICANV': (['Gallicanus'], []),
    'C . MAXIMINIVS': (['Gaius Maximinius Rusticus', 'Titus Iulius Tacitus'], []),
    'L SILVIVS VIC': (['Lucius Silvius Victor'], []),
    'C . CATVLLINIVS': (['Gaius Catullinius Secco'], ['handelaar in vissaus (negotiator allecarius)']),
    'C . IVL . FLOREN': (['Gaius Iulius Florentinus'], ['zouthandelaar (negotiator salarius)']),
    '[A]PRILIS VETERAN': (['Gaius Iulius Aprilis'], ['veteraan (veteranus)', 'consulaire begunstigde (beneficiarius consularis)']),
}

def schoon(naam):
    naam = re.sub(r'\s*\(.*?\)', '', naam)             # haakjes met uitleg weg
    naam = re.sub(r'^(?:\[\.\.\.\]\s*)+', '', naam)    # ontbrekend begin
    naam = naam.strip(' ,.')
    if not naam or '[' in naam or '...' in naam or '?' in naam or 'onleesbaar' in naam or 'onvolledig' in naam:
        return None
    if len(naam.split()) == 1 and len(naam) < 4:
        return None
    return naam

def personen_uit_vertaling(v):
    m = re.search(r'Nehalennia(?:\(\?\))?\]?\.?\s*(.*)', v, re.S)
    if not m: return []
    r = m.group(1)
    r = re.sub(r'^Voor[^:]*:\s*', '', r)
    r = re.split(r'\s+\[?(?:heeft|hebben)\b', r)[0]
    r = re.sub(r'\(fragment.*?\)|\(afgebroken\)', '', r)
    uit = []
    for stuk in re.split(r'\s+en\s+(?=[A-Z\[])', r):
        n = schoon(stuk.split(',')[0])
        if n and n not in uit: uit.append(n)
    return uit

def beroepen_uit(vert, latijn):
    gevonden = []
    tekst = (vert or '') + ' | ' + latijn.upper()
    for rx, label in BEROEPEN:
        if re.search(rx, (vert or '')) or re.search(rx, latijn, re.I):
            gevonden.append(label)
    if not gevonden and re.search(ALGEMEEN[0], tekst):
        gevonden.append(ALGEMEEN[1])
    # 'handelaar op Kent' mag alleen via echte Kent-trefwoorden
    return gevonden

objecten = json.load(open(OBJECTEN, encoding='utf-8'))
inscripties = {}
for o in objecten:
    t = o.get('inscripties_text')
    if not t: continue
    e = inscripties.setdefault(t, {'vert': None})
    if o.get('edcs_vertaling_concept'): e['vert'] = o['edcs_vertaling_concept']

resultaat = []
for t, e in inscripties.items():
    hand = next((v for k, v in HANDMATIG.items() if k in t), None)
    if hand:
        p, b = hand
    else:
        p = personen_uit_vertaling(e['vert']) if e['vert'] else []
        b = beroepen_uit(e['vert'], t)
    if p or b:
        resultaat.append({'tekst': t, 'personen': p, 'beroepen': b})

json.dump({
    '_let_op': 'Afgeleid uit de inscripties (en waar beschikbaar de vertaling); nog te controleren. Alleen de opdragers worden genoemd, geen vaders, patroons of consuls.',
    'inscripties': resultaat,
}, open(UIT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(len(inscripties), 'inscripties,', len(resultaat), 'met personen of beroepen')
