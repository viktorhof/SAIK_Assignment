#!/usr/bin/env python3
"""
scripts/rag_index.py  –  Step 5: RAG Indexing Pipeline
=======================================================
Builds a semantic vector index from three knowledge sources:

  1. ontology/plant_management_oops_fixed.ttl  — OWL2 TBox (classes, properties,
                                                  named individuals, axioms)
  2. ontology/README.md                        — schema documentation + competency
                                                  questions + column mappings
  3. data/shop/inventory.csv                   — shop product catalogue (~95 rows)

Output written to rag/:
  index.pkl   — list of chunk dicts with 'embedding' numpy arrays
  meta.json   — indexing statistics

Usage:
  python3 scripts/rag_index.py
  python3 scripts/rag_index.py --ttl ontology/plant_management_oops_fixed.ttl \\
                                --readme ontology/README.md \\
                                --csv data/shop/inventory.csv
"""

from __future__ import annotations

import argparse
import json
import pickle
import re
import sys
from pathlib import Path
from typing import Optional

import pandas as pd
from rdflib import Graph, Namespace, RDF, RDFS, OWL, URIRef, Literal

# ─── Paths ────────────────────────────────────────────────────────────────────
PLANT_NS = Namespace("http://www.semanticweb.org/plantms/ontology#")

ROOT           = Path(__file__).resolve().parent.parent
DEFAULT_TTL    = ROOT / "ontology" / "plant_management_oops_fixed.ttl"
DEFAULT_README = ROOT / "ontology" / "README.md"
DEFAULT_CSV    = ROOT / "data" / "shop" / "inventory.csv"
INDEX_DIR      = ROOT / "rag"
INDEX_PATH     = INDEX_DIR / "index.pkl"
META_PATH      = INDEX_DIR / "meta.json"

EMBEDDING_MODEL = "all-MiniLM-L6-v2"   # ~80 MB, fast, good quality


# ─── Helpers ──────────────────────────────────────────────────────────────────
def _local(uri: URIRef) -> str:
    """Return the local part of a URI (after # or last /)."""
    s = str(uri)
    return s.split("#")[-1] if "#" in s else s.split("/")[-1]


def _label(g: Graph, node) -> str:
    if not isinstance(node, URIRef):
        return str(node) if node else ""
    lbl = g.value(node, RDFS.label)
    return str(lbl).split("@")[0] if lbl else _local(node)


def _comment(g: Graph, node) -> str:
    if not isinstance(node, URIRef):
        return ""
    cmt = g.value(node, RDFS.comment)
    return str(cmt).split("@")[0] if cmt else ""


# ─── TTL chunker ──────────────────────────────────────────────────────────────
def parse_ttl(ttl_path: Path) -> list[dict]:
    """
    Parse the OWL2 TBox and return a list of text chunks.

    Chunk types produced:
      ontology_header   – one overview chunk
      ontology_class    – one chunk per OWL class
      ontology_property – one chunk per object / datatype property
      ontology_individual – one chunk per group of named individuals (by type)
      ontology_odp      – one chunk per key axiom group (property chains, disjoint, etc.)
    """
    g = Graph()
    g.parse(str(ttl_path), format="turtle")
    print(f"  Loaded {len(g)} triples from {ttl_path.name}")

    chunks: list[dict] = []
    cid = 0

    def add(source_tag: str, title: str, text: str):
        nonlocal cid
        chunks.append({
            "chunk_id": f"ttl_{cid:04d}",
            "source": source_tag,
            "title": title,
            "text": text.strip(),
        })
        cid += 1

    # 1. Ontology header chunk
    ont_iri = URIRef("http://www.semanticweb.org/plantms/ontology#")
    add(
        "ontology_header",
        "Plant Management System Ontology – Overview",
        (
            "Plant Management System Ontology\n"
            "Version: 1.1.0\n"
            "Namespace prefix: plant: <http://www.semanticweb.org/plantms/ontology#>\n"
            "This OWL2 TBox models plant species and their biological, ecological, "
            "geographic, and use-related properties based on the Trefle species.csv "
            "dataset (~416k rows, 54 columns). It has 38 classes, 27 object properties, "
            "33 datatype properties, and 86 named individuals. The ABox (individual "
            "plants) is produced in Step 2 via OBDA. The shop product layer is sourced "
            "from data/shop/inventory.csv (~95 Vienna-appropriate products)."
        ),
    )

    # 2. OWL Classes
    classes = sorted(
        [u for u in g.subjects(RDF.type, OWL.Class) if isinstance(u, URIRef)],
        key=lambda u: _label(g, u),
    )
    for cls in classes:
        label   = _label(g, cls)
        comment = _comment(g, cls)

        # Direct superclasses (only URIRef, skip blank nodes)
        supers = [_label(g, s) for s in g.objects(cls, RDFS.subClassOf)
                  if isinstance(s, URIRef)]

        # Which properties have this class as domain?
        dom_of = sorted({_label(g, p) for p in g.subjects(RDFS.domain, cls)
                         if isinstance(p, URIRef)})
        # Which properties have this class as range?
        rng_of = sorted({_label(g, p) for p in g.subjects(RDFS.range, cls)
                         if isinstance(p, URIRef)})

        # disjointUnionOf members
        duj_members: list[str] = []
        for duj in g.objects(cls, OWL.disjointUnionOf):
            node = duj
            while node:
                first = g.value(node, RDF.first)
                if first:
                    duj_members.append(_label(g, first))
                node = g.value(node, RDF.rest)
                if str(node) == str(RDF.nil):
                    break

        lines = [f"OWL Class: {label}"]
        if comment:
            lines.append(f"Description: {comment}")
        if supers:
            lines.append(f"Subclass of: {', '.join(supers)}")
        if duj_members:
            lines.append(f"disjointUnionOf: {', '.join(duj_members)}")
        if dom_of:
            lines.append(f"Domain of: {', '.join(dom_of)}")
        if rng_of:
            lines.append(f"Range of: {', '.join(rng_of)}")
        add("ontology_class", f"Class: {label}", "\n".join(lines))

    # 3. Object Properties
    obj_props = sorted(
        [u for u in g.subjects(RDF.type, OWL.ObjectProperty) if isinstance(u, URIRef)],
        key=lambda u: _label(g, u),
    )
    for prop in obj_props:
        label   = _label(g, prop)
        comment = _comment(g, prop)
        domain  = g.value(prop, RDFS.domain)
        rng     = g.value(prop, RDFS.range)
        chars: list[str] = []
        if (prop, RDF.type, OWL.FunctionalProperty) in g:
            chars.append("Functional")
        if (prop, RDF.type, OWL.TransitiveProperty) in g:
            chars.append("Transitive")
        inv = g.value(prop, OWL.inverseOf)

        lines = [f"Object Property: {label}"]
        if comment:
            lines.append(f"Description: {comment}")
        if domain:
            lines.append(f"Domain: {_label(g, domain)}")
        if rng:
            lines.append(f"Range: {_label(g, rng)}")
        if chars:
            lines.append(f"Characteristics: {', '.join(chars)}")
        if inv and isinstance(inv, URIRef):
            lines.append(f"Inverse of: {_label(g, inv)}")
        add("ontology_property", f"ObjectProperty: {label}", "\n".join(lines))

    # 4. Datatype Properties
    dt_props = sorted(
        [u for u in g.subjects(RDF.type, OWL.DatatypeProperty) if isinstance(u, URIRef)],
        key=lambda u: _label(g, u),
    )
    for prop in dt_props:
        label   = _label(g, prop)
        comment = _comment(g, prop)
        domain  = g.value(prop, RDFS.domain)
        chars: list[str] = []
        if (prop, RDF.type, OWL.FunctionalProperty) in g:
            chars.append("Functional")

        lines = [f"Datatype Property: {label}"]
        if comment:
            lines.append(f"Description: {comment}")
        if domain:
            lines.append(f"Domain: {_label(g, domain)}")
        if chars:
            lines.append(f"Characteristics: {', '.join(chars)}")
        add("ontology_property", f"DatatypeProperty: {label}", "\n".join(lines))

    # 5. Named individuals – group by type for denser, more useful chunks
    individuals = [u for u in g.subjects(RDF.type, OWL.NamedIndividual)
                   if isinstance(u, URIRef)]
    by_type: dict[str, list[str]] = {}
    for ind in individuals:
        ind_label = _label(g, ind)
        types = [_label(g, t) for t in g.objects(ind, RDF.type)
                 if t != OWL.NamedIndividual and isinstance(t, URIRef)]
        for t in types:
            by_type.setdefault(t, []).append(ind_label)
    for type_name, labels in sorted(by_type.items()):
        add(
            "ontology_individual",
            f"Named Individuals: {type_name}",
            f"Type: {type_name}\nInstances: {', '.join(sorted(labels))}",
        )

    # 6. Key ODP summary chunks (added manually for richer retrieval)
    odp_texts = [
        (
            "Componency ODP – Plant parts",
            "The Componency ODP models structural plant parts.\n"
            "Plant hasComponent Flower / Foliage / Fruit / Root (direct, non-transitive).\n"
            "hasPart is transitive: covers all parts at any depth.\n"
            "hasComponent is a sub-property of hasPart.\n"
            "owl:AllDisjointClasses (Flower Foliage Fruit Root) prevents cross-typing.\n"
            "Example: to find plants with blue flowers use:\n"
            "  ?p plant:hasComponent ?f . ?f a plant:Flower ;\n"
            "     plant:hasColor plant:FlowerColor_Blue .",
        ),
        (
            "N-ary Relation ODP – Plant distribution",
            "The N-ary ODP models the three-way relation Plant × Region × DistributionStatus.\n"
            "Classes: PlantDistribution (reification node), DistributionStatus.\n"
            "Properties: hasDistribution, inRegion, hasDistributionStatus.\n"
            "Status values: NativeStatus, IntroducedStatus, EndemicStatus, AbsentStatus.\n"
            "Example: to find plants native to a region:\n"
            "  ?p plant:hasDistribution ?d .\n"
            "  ?d plant:inRegion plant:Austria ;\n"
            "     plant:hasDistributionStatus plant:NativeStatus .",
        ),
        (
            "AgentRole ODP – Plant uses",
            "The AgentRole ODP avoids class explosion for plant uses.\n"
            "Plants point to PlantUse role individuals rather than subclassing.\n"
            "Classes: PlantUse (abstract), EdibleUse, VegetableUse, OrnamentalUse.\n"
            "Property: hasPlantUse (domain Plant, range PlantUse).\n"
            "Named individuals: EdibleLeavesUse, EdibleFruitsUse, EdibleRootsUse,\n"
            "  EdibleStemsUse, EdibleSeedsUse, EdibleTubersUse, EdibleFlowersUse,\n"
            "  VegetableUseIndividual, OrnamentalUseIndividual.\n"
            "Also: hasEdiblePart → FlowerPart, FruitPart, LeafPart, RootPart,\n"
            "  SeedPart, StemPart, TuberPart.\n"
            "isEdible (boolean) and isVegetable (boolean) are datatype properties on Plant.",
        ),
        (
            "Property chain axiom – Taxonomy inference",
            "OWL2 property chain:\n"
            "  belongsToGenus ∘ isSubsumedByFamily ⊑ belongsToFamily\n"
            "If a plant belongs to genus Abies, and Abies isSubsumedByFamily Pinaceae,\n"
            "then the plant belongsToFamily Pinaceae (inferred by the reasoner).\n"
            "Classes: Family, Genus (both subclasses of TaxonomicRank).\n"
            "owl:AllDisjointClasses (Family Genus Plant) prevents cross-classification.",
        ),
        (
            "Shop product layer – classes and properties",
            "The Shop layer connects the Trefle plant data to a mock Vienna shop inventory.\n"
            "Class: ShopProduct – one row per product line in data/shop/inventory.csv.\n"
            "  owl:hasKey (hasProductId) – SKU uniquely identifies a product.\n"
            "  rdfs:subClassOf ∃isShopProductFor.Plant – every product links to a species.\n"
            "Properties on ShopProduct:\n"
            "  hasProductId (integer, Functional, hasKey)\n"
            "  hasProductName (string, Functional)\n"
            "  hasPriceEur (decimal ≥ 0)\n"
            "  hasStockQuantity (integer ≥ 0)\n"
            "  hasShelfDate (xsd:date)\n"
            "  hasCareLevel → CareLevel: EasyCare, MediumCare, HardCare\n"
            "  hasTemperatureCategory → TemperatureCategory: WarmCategory, CoolCategory, ModerateCategory\n"
            "Property isShopProductFor links ShopProduct → Plant (Functional, inverseOf hasShopProduct).\n"
            "TemperatureCategory is NOT in the Trefle CSV – assigned manually per species.",
        ),
    ]
    for title, text in odp_texts:
        add("ontology_odp", title, text)

    return chunks


# ─── README chunker ───────────────────────────────────────────────────────────
def parse_readme(readme_path: Path) -> list[dict]:
    """
    Split README.md into section-level chunks on ## headings.
    Each chunk carries its section title and full section body.
    """
    text = readme_path.read_text(encoding="utf-8")
    # Split on top-level ## (not ###, not ####)
    raw_sections = re.split(r"\n(?=## )", text)
    chunks: list[dict] = []
    for i, section in enumerate(raw_sections):
        lines = section.strip().splitlines()
        if not lines:
            continue
        title = lines[0].lstrip("#").strip()
        body  = "\n".join(lines).strip()
        if len(body) < 40:   # skip near-empty sections
            continue
        chunks.append({
            "chunk_id": f"readme_{i:03d}",
            "source": "readme",
            "title": title,
            "text": body,
        })
    return chunks


# ─── Shop CSV chunker ─────────────────────────────────────────────────────────
def parse_csv(csv_path: Path) -> list[dict]:
    """
    One text chunk per shop product row.
    Includes all available columns so retrieval catches price, stock, care, etc.
    """
    df = pd.read_csv(csv_path)
    print(f"  Loaded {len(df)} rows × {len(df.columns)} cols from {csv_path.name}")

    # Core columns we know about from the schema
    CORE_COLS = {
        "product_id", "product_name", "trefle_id", "scientific_name",
        "price_eur", "stock_quantity", "care_level", "temperature_category",
        "shelf_date",
    }

    chunks: list[dict] = []
    for _, row in df.iterrows():
        product_name = row.get("product_name", row.get("scientific_name", "Unknown"))
        product_id   = row.get("product_id", "")

        lines: list[str] = [
            f"Shop product: {product_name}",
            f"Product ID (SKU): {product_id}",
        ]
        if pd.notna(row.get("scientific_name")):
            lines.append(f"Scientific name: {row['scientific_name']}")
        if pd.notna(row.get("trefle_id")):
            lines.append(f"Trefle ID: {row['trefle_id']}")
        if pd.notna(row.get("price_eur")):
            lines.append(f"Price: €{row['price_eur']}")
        if pd.notna(row.get("stock_quantity")):
            lines.append(f"Stock quantity: {int(row['stock_quantity'])} units")
        if pd.notna(row.get("care_level")):
            lines.append(f"Care level: {row['care_level']}")
        if pd.notna(row.get("temperature_category")):
            lines.append(f"Temperature category: {row['temperature_category']}")
        if pd.notna(row.get("shelf_date")):
            lines.append(f"Shelf date: {row['shelf_date']}")

        # Any extra columns (family, growth_habit, etc. added by generate_shop_data.py)
        for col in df.columns:
            if col not in CORE_COLS:
                val = row.get(col)
                if pd.notna(val) and str(val).strip():
                    lines.append(f"{col.replace('_', ' ').title()}: {val}")

        text = "\n".join(lines)
        chunk_id = f"shop_{int(product_id):04d}" if str(product_id).isdigit() else f"shop_{_}",
        chunks.append({
            "chunk_id": f"shop_{str(product_id).zfill(4)}",
            "source": "shop_inventory",
            "title": f"Shop: {product_name}",
            "text": text,
        })
    return chunks


# ─── Embedding ────────────────────────────────────────────────────────────────
def embed_chunks(chunks: list[dict], model_name: str = EMBEDDING_MODEL) -> list[dict]:
    """
    Add an 'embedding' key (numpy float32 array) to each chunk.
    Uses sentence-transformers with the specified model.
    """
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        print(
            "ERROR: sentence-transformers not installed.\n"
            "Run:  pip install sentence-transformers",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"Loading embedding model '{model_name}' …", flush=True)
    model = SentenceTransformer(model_name)

    # Concatenate title + body so the model sees both signals
    texts = [c["title"] + "\n" + c["text"] for c in chunks]
    print(f"Embedding {len(texts)} chunks …", flush=True)
    embeddings = model.encode(
        texts,
        batch_size=64,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=True,   # unit-norm → dot product = cosine similarity
    )
    for chunk, emb in zip(chunks, embeddings):
        chunk["embedding"] = emb
    return chunks


# ─── Entry point ──────────────────────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser(
        description="RAG indexing – Plant Management System (Step 5)"
    )
    parser.add_argument("--ttl",    default=str(DEFAULT_TTL),    help="Path to OWL2 TTL file")
    parser.add_argument("--readme", default=str(DEFAULT_README), help="Path to README.md")
    parser.add_argument("--csv",    default=str(DEFAULT_CSV),    help="Path to shop inventory CSV")
    parser.add_argument("--model",  default=EMBEDDING_MODEL,     help="sentence-transformers model name")
    parser.add_argument("--out",    default=str(INDEX_PATH),     help="Output index .pkl path")
    args = parser.parse_args()

    ttl_path    = Path(args.ttl)
    readme_path = Path(args.readme)
    csv_path    = Path(args.csv)
    out_path    = Path(args.out)

    print("═" * 55)
    print("  Plant Management RAG – Indexing Phase")
    print("═" * 55)

    all_chunks: list[dict] = []

    # 1. TTL
    if ttl_path.exists():
        print(f"\n[1/3] Parsing TTL ontology: {ttl_path}")
        ttl_chunks = parse_ttl(ttl_path)
        print(f"      → {len(ttl_chunks)} chunks")
        all_chunks.extend(ttl_chunks)
    else:
        print(f"WARNING: TTL not found at {ttl_path}", file=sys.stderr)

    # 2. README
    if readme_path.exists():
        print(f"\n[2/3] Parsing README: {readme_path}")
        readme_chunks = parse_readme(readme_path)
        print(f"      → {len(readme_chunks)} chunks")
        all_chunks.extend(readme_chunks)
    else:
        print(f"WARNING: README not found at {readme_path}", file=sys.stderr)

    # 3. Shop CSV
    if csv_path.exists():
        print(f"\n[3/3] Parsing shop CSV: {csv_path}")
        csv_chunks = parse_csv(csv_path)
        print(f"      → {len(csv_chunks)} chunks")
        all_chunks.extend(csv_chunks)
    else:
        print(
            f"\n[3/3] Shop CSV not found at {csv_path} – skipping.\n"
            "      Run `python3 scripts/generate_shop_data.py` first to create it.",
            file=sys.stderr,
        )

    if not all_chunks:
        print("ERROR: No chunks produced. Check file paths.", file=sys.stderr)
        sys.exit(1)

    # 4. Embed all chunks
    print(f"\nEmbedding {len(all_chunks)} total chunks …")
    all_chunks = embed_chunks(all_chunks, model_name=args.model)

    # 5. Save
    out_path.parent.mkdir(parents=True, exist_ok=True)
    meta_path = out_path.parent / "meta.json"

    with open(out_path, "wb") as f:
        pickle.dump(all_chunks, f)

    by_source: dict[str, int] = {}
    for c in all_chunks:
        by_source[c["source"]] = by_source.get(c["source"], 0) + 1
    meta = {
        "total_chunks": len(all_chunks),
        "by_source": by_source,
        "embedding_model": args.model,
        "index_path": str(out_path),
    }
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2)

    print("\n" + "═" * 55)
    print(f"  ✓ Index saved → {out_path}")
    print(f"  ✓ Meta  saved → {meta_path}")
    print(f"  Total chunks : {meta['total_chunks']}")
    for src, n in sorted(by_source.items()):
        print(f"    {src:<35s} {n:>4d}")
    print("═" * 55)
    print("\nNext step: python3 scripts/rag_query.py")


if __name__ == "__main__":
    main()
