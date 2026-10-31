"""Harvest objects from the Zeeuws erfgoedplatform (Collectie Zeeland) linked-data dump.
"""

import gzip
import urllib.request

import pandas as pd
from rdflib import BNode, Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF, RDFS

from const import SEP, USER_AGENT

DUMP_URL = ("https://zoeken.collectiezeeland.nl/Atlantispubliek/data/set/"
            "Zeeuws+erfgoedplatform+-+Museum+objecten.nq.gz")

CRM = Namespace("http://www.cidoc-crm.org/cidoc-crm/")
SDO = Namespace("https://schema.org/")

# 3 of these turn up by searching the dump for "Nehalennia". The dolium does not since its
# museum description mentions her, but the export carries no free-text description
# field, so no search of the file can find it. Hardcoded, as the set is this small.
PIDS = [
    "https://hdl.handle.net/21.12128/326160703",  # Nehalennia
    "https://hdl.handle.net/21.12128/326163937",  # Nehalennia
    "https://hdl.handle.net/21.12128/327230837",  # Votiefaltaar (replica) voor de godin Nehalennia
    "https://hdl.handle.net/21.12128/327052914",  # Randfragment van een groot voorraadvat of dolium
]

_DESCRIBE = """
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
DESCRIBE ?root ?linked WHERE {{
  VALUES ?root {{ {values} }}
  OPTIONAL {{
    ?root (!rdf:type)* ?mid .
    ?mid ?lp ?linked .
    FILTER(isIRI(?linked) && ?lp != rdf:type)
    FILTER EXISTS {{ ?linked ?x ?y }}
  }}
}}"""


def load_dump():
    """The whole published dump as a Graph."""
    request = urllib.request.Request(DUMP_URL, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=300) as response:
        nquads = gzip.decompress(response.read())

    graph = Graph()
    graph.parse(data=nquads, format="nt")  # .nq extension, but the file has no graph column
    graph.bind("crm", CRM)
    graph.bind("schema", SDO)
    graph.bind("aat", "http://vocab.getty.edu/aat/")
    return graph


def select(graph, pids=PIDS):
    """The part of `graph` describing `pids`, plus one hop out so nothing dangles."""
    values = " ".join(f"<{pid}>" for pid in pids)
    subset = graph.query(_DESCRIBE.format(values=values)).graph
    subset.namespace_manager = graph.namespace_manager
    return subset


def _label(graph, node):
    """Literal -> its text; IRI or blank node -> its rdfs:label if known, else the IRI."""
    if node is None:
        return None
    if isinstance(node, Literal):
        return str(node)
    label = graph.value(node, RDFS.label)
    return str(label) if label else str(node)


def _joined(values):
    return SEP.join(dict.fromkeys(v for v in values if v))


def _row(graph, pid):
    obj = URIRef(pid)

    numbers, title_variants = [], []
    for node in graph.objects(obj, CRM.P1_is_identified_by):
        content = graph.value(node, CRM.P190_has_symbolic_content)
        if (node, RDF.type, CRM.E33_E41_Linguistic_Appellation) in graph:
            title_variants.append(str(content))
        else:
            numbers.append(f"{_label(graph, graph.value(node, CRM.P2_has_type))}: {content}")

    materials, notes = [], []
    for node in graph.objects(obj, CRM.P45_consists_of):
        materials.append(_label(graph, graph.value(node, CRM.P2_has_type)))
        notes += [str(note) for note in graph.objects(node, CRM.P3_has_note)]

    sizes = [str(size) for part in graph.objects(obj, CRM.P46_is_composed_of)
             for size in graph.objects(part, SDO.size)]

    makers, places, begins, ends = [], [], [], []
    for production in graph.objects(obj, CRM.P108i_was_produced_by):
        makers += [_label(graph, a) for a in graph.objects(production, CRM.P14_carried_out_by)]
        places += [_label(graph, p) for p in graph.objects(production, CRM.P7_took_place_at)]
        for span in graph.objects(production, CRM["P4_has_time-span"]):  # hyphen, no attribute access
            begins += [str(v)[:10] for v in graph.objects(span, CRM.P82a_begin_of_the_begin)]
            ends += [str(v)[:10] for v in graph.objects(span, CRM.P82b_end_of_the_end)]

    images = [str(i) for i in graph.objects(obj, SDO.image) if isinstance(i, Literal)]
    manifests = [str(url) for node in graph.objects(obj, SDO.image) if isinstance(node, BNode)
                 for url in graph.objects(node, SDO.contentUrl)]

    return {
        "objectnummer": str(graph.value(obj, SDO.identifier) or ""),
        "titel": _label(graph, obj),
        "pid": pid,
        "objecttype": _joined(_label(graph, t) for t in graph.objects(obj, CRM.P2_has_type)),
        "materiaal": _joined(materials),
        "materiaal_toelichting": _joined(notes),
        "afmetingen": _joined(sizes),
        "datering_begin": _joined(begins),
        "datering_eind": _joined(ends),
        "vervaardiger": _joined(makers),
        "vindplaats": _joined(places),
        "andere_nummers": _joined(numbers),
        "titelvarianten": _joined(title_variants),
        "iiif_manifest": _joined(manifests),
        "afbeelding_count": len(images),
        "afbeelding_url": images[0] if images else None,
        "afbeeldingen": _joined(images),
        "licentie": str(graph.value(obj, SDO.license) or ""),
    }


def fetch(pids=PIDS, ttl_path=None, progress=True):
    """Harvest the given objects, one row each. If `ttl_path` is given, the selected subset is also written there as Turtle"""
    def log(message):
        if progress:
            print(message, flush=True)

    graph = load_dump()
    log(f"{len(graph)} triples in dump")

    subset = select(graph, pids)
    if ttl_path is not None:
        subset.serialize(ttl_path, format="turtle")
        log(f"wrote {len(subset)} triples to {ttl_path}")

    return pd.DataFrame([_row(subset, pid) for pid in pids])
