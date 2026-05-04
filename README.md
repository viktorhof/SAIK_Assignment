# SAIK_Assignment

Semantic AI and Knowledge Systems (SAIK) assignment - Plant Management System Ontology.
Data source: [Trefle](https://trefle.io/) `species.csv` (54 columns, ~416k plant species rows).

---

## Project Structure

```text
data/raw/species.csv          # Local Trefle dataset input (ignored by git)
data/shop/inventory.csv       # Generated mock shop inventory (ignored by git)
data/plantms.db               # Generated SQLite database (ignored by git)
scripts/generate_ontology.py  # Step 1: generates the OWL2 TBox
scripts/apply_oops_fixes.py   # Step 3: applies OOPS follow-up fixes
scripts/generate_shop_data.py # Step 2 prep: generates the mock shop inventory CSV
scripts/load_database.py      # Step 2 prep: loads both CSVs into normalized SQLite
ontology/plant_management.ttl # Generated OWL2 ontology (TBox + named individuals)
ontology/plant_management.rdf # Generated RDF/XML export of the ontology
ontology/plant_management_oops_fixed.ttl # Step 3: OOPS-fixed ontology
ontology/plant_management_oops_fixed.rdf # Step 3: OOPS-fixed RDF/XML export
ontology/README.md            # Full ontology schema documentation
plant_management_r2rml.ttl    # Step 2: R2RML mappings for Ontop / GraphDB
plant_management_shapes.ttl   # Step 3: SHACL rules for KG validation
plant_management_po_alignment.ttl # Step 4: Plant Ontology alignment
report.tex                    # Technical project report
OOPS_FINDINGS.md              # Step 3: original OOPS findings
OOPS_FIXES.md                 # Step 3: fixes applied after OOPS scan
requirements.txt             # Python dependencies
```

---

## Assignment Status

| Step | Status | Notes |
| --- | --- | --- |
| Step 1: Ontology engineering | Done | Base ontology has more than 30 classes and 25 properties, OWL2 features, and ODPs. |
| Step 2: OBDA KG creation | Partly done | R2RML mappings and generation scripts exist. Local CSV/DB artifacts are ignored by git. GraphDB materialized KG export is still open. |
| Step 3: Verification | Partly done | OOPS scan, OOPS fixes, and SHACL rules exist. SHACL validation report is still open. |
| Step 4: Alignment | First stage done | Plant Ontology was selected and a manual alignment artifact exists. Tool-based Alignment API result is still open if required. |
| Step 5: RAG application | Open | Source code and usage documentation still need to be created. |

---

## Step 1 - Generate the OWL2 Ontology (TBox)

```bash
python3 scripts/generate_ontology.py
```

This writes `ontology/plant_management.ttl` and prints a summary of the generated
classes, properties, and named individuals.

See [ontology/README.md](ontology/README.md) for the full schema documentation
(class hierarchy, properties, OWL2 features, ODPs, competency questions).

## Step 2 prep - Generate Mock Shop Inventory

```bash
python3 scripts/generate_shop_data.py
```

This reads `data/raw/species.csv`, selects ~100 Vienna-appropriate species across 12
plant families, and writes `data/shop/inventory.csv` with realistic shop attributes
(price, stock quantity, shelf date, care level, temperature category).

The CSV is the second data source for Step 2 OBDA. During loading, its Trefle ids are
linked to the normalized `plant` table so shop competency questions stay easy to map.

---

## Step 2 - R2RML / Ontop Mapping

The R2RML mapping file is:

```bash
plant_management_r2rml.ttl
```

It maps:
- `plant` rows to `plant:Plant` individuals
- taxonomy dimension rows to `plant:Family` and `plant:Genus`
- normalized link tables such as `plant_common_name`, `plant_synonym`,
  `plant_bloom_month`, `plant_distribution`, and component/color tables
- `shop_product` rows to `plant:ShopProduct`

The database is normalized for OBDA: multi-valued CSV fields are materialized into relation
tables during loading, so the R2RML file mostly uses direct table scans and small lookup joins
instead of recursive string-splitting SQL.

---

## Step 2 prep - Load SQLite Database

```bash
python3 scripts/load_database.py
```

This reads both CSVs and creates `data/plantms.db` - the SQLite database used by Ontop for
OBDA. All Trefle species are loaded into a normalized schema so the ontology also serves as a
general plant encyclopedia without pushing cleanup logic into the mapping layer.

Example summary from the current dataset:

```text
Database: data/plantms.db
  plant                : 416,473 rows
  family               : 580 rows
  genus                : 15,540 rows
  plant_distribution   : 1,306,113 rows
  shop_product         : 95 rows
  shop <> plant joins  : 95 rows matched
```

Core tables:
- `plant` - one row per Trefle species with scalar attributes only
- `family`, `genus`, `region`, `month_dim`, and enum dimensions for growth form/rate,
  habits, edible parts, care levels, temperature categories, foliage textures, and colors
- link tables such as `plant_common_name`, `plant_synonym`, `plant_growth_habit`,
  `plant_bloom_month`, `plant_distribution`, `plant_edible_part`, and component/color tables
- `shop_product` - normalized shop inventory linked by FK `plant_id -> plant.plant_id`

Uses only Python stdlib (`csv`, `sqlite3`, `pathlib`, `time`, `re`) - no extra dependencies.

The large CSV and SQLite files are not tracked in git. Keep the Trefle export at
`data/raw/species.csv` locally, then regenerate `data/shop/inventory.csv` and
`data/plantms.db` with the commands above.

---

## Step 3 first stage - Apply OOPS Fixes

```bash
python3 scripts/apply_oops_fixes.py
```

This reads `ontology/plant_management.ttl` and writes separate OOPS-fixed
artifacts:
- `ontology/plant_management_oops_fixed.ttl`
- `ontology/plant_management_oops_fixed.rdf`

The original scan notes stay in `OOPS_FINDINGS.md`; the fix summary is in
`OOPS_FIXES.md`.

## Step 3 second stage - SHACL Rules

```bash
plant_management_shapes.ttl
```

The SHACL rules validate plant identity, taxonomy, numeric ranges, months and
seasons, plant parts, distributions, and shop products. Validation reports
should be stored as `plant_management_validation_report.ttl` after running a SHACL engine such as
TopBraid SHACL or SHACL4Protege.

The rules are meant to run on the materialized Step 2 knowledge graph,
preferably together with the OOPS-fixed ontology:

```bash
ontology/plant_management_oops_fixed.ttl
```

The rules follow the current data state. For example, plant genus and family
links are checked when present, but they are not mandatory because some Trefle
rows do not contain taxonomy ids.

Expected future report artifact:

```bash
plant_management_validation_report.ttl
```

## Step 4 first stage - Ontology Alignment

The selected external ontology is the Plant Ontology (PO):

```bash
http://purl.obolibrary.org/obo/po.owl
```

PO was selected because it is focused on plant anatomy, morphology, and plant
development. This matches the strongest part of the local ontology: plant parts
such as flower, fruit, root, foliage, and general plant structure.

The first alignment artifact is:

```bash
plant_management_po_alignment.ttl
```

The alignment is manual and conservative:

- `owl:equivalentClass` is used only when the local class and PO class have the same meaning.
- `rdfs:subClassOf` is used when the local class is clearly narrower.
- `skos:closeMatch` is used when the concepts are related but not exactly the same.
- `plant:Plant` is not mapped to PO `whole plant`, because the local class represents a species/data record and not one physical organism.

Candidate overview:

| Ontology | Fit | Reason |
| --- | --- | --- |
| Plant Ontology (PO) | Best | Direct match for plant structures and development stages. |
| Plant Trait Ontology (TO) | Good | Useful for traits, but local traits are mostly modeled as properties and values. |
| AGROVOC | Medium | Broad agriculture thesaurus, but less precise for OWL class alignment. |
| Crop Ontology (CO) | Medium-low | Strong for crop breeding variables, but the project covers many plant types. |
| ENVO | Medium-low | Useful for environment and habitat, but not the main project focus. |
| NCBI Taxonomy | Low for now | Useful for taxa, but the data does not contain NCBI taxon ids. |

## Report

The report source is:

```bash
report.tex
```

Build it with:

```bash
pdflatex report.tex
```
