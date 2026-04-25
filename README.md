# SAIK_Assignment

Semantic AI and Knowledge Systems (SAIK) assignment — Plant Management System Ontology.
Data source: [Trefle](https://trefle.io/) `species.csv` (54 columns, ~35 k plant species rows).

---

## Project Structure

```
data/raw/species.csv          # Trefle species dataset (TSV format)
data/shop/inventory.csv       # Mock shop inventory (~95 rows, Vienna corner plant shop)
data/plantms.db               # SQLite database (generated — not committed to git)
scripts/generate_ontology.py  # Step 1: generates the OWL2 TBox
scripts/generate_shop_data.py # Step 2 prep: generates the mock shop inventory CSV
scripts/load_database.py      # Step 2 prep: loads both CSVs into SQLite
ontology/plant_management.ttl # Generated OWL2 ontology (TBox + named individuals)
ontology/README.md            # Full ontology schema documentation
requirements.txt              # Python dependencies
```

---

## Step 1 — Generate the OWL2 Ontology (TBox)

```bash
python3 scripts/generate_ontology.py
```

This writes `ontology/plant_management.ttl` and prints a summary:

```
Ontology written to: ontology/plant_management.ttl
  Triples            : 1,064
  Classes            : 38
  Object properties  : 27
  Datatype properties: 32
  Named individuals  : 86
```

See [ontology/README.md](ontology/README.md) for the full schema documentation
(class hierarchy, properties, OWL2 features, ODPs, competency questions).

---

## Step 2 prep — Generate Mock Shop Inventory

```bash
python3 scripts/generate_shop_data.py
```

This reads `data/raw/species.csv`, selects ~100 Vienna-appropriate species across 12
plant families, and writes `data/shop/inventory.csv` with realistic shop attributes
(price, stock quantity, shelf date, care level, temperature category).

The CSV is the second database for Step 2 OBDA — Ontop joins it with the Trefle
species table via `trefle_id` to answer shop owner competency questions.

---

## Step 2 prep — Load SQLite Database

```bash
python3 scripts/load_database.py
```

This reads both CSVs and creates `data/plantms.db` — the SQLite database used by
Ontop for OBDA. All 416k Trefle species are loaded (not just shop-relevant ones) so
the ontology also serves as a general plant encyclopedia.

```
Database: data/plantms.db
  species        : 416,476 rows
  shop_inventory : 95 rows
  File size      : ~55 MB
  shop ⋈ species : 95 rows matched (of 95 shop rows)
```

Tables:
- `species` — 44 columns (all ontology-mapped Trefle columns; URL reference columns omitted)
- `shop_inventory` — 9 columns matching `data/shop/inventory.csv`; FK `trefle_id → species.id`

Uses only Python stdlib (`csv`, `sqlite3`, `pathlib`) — no extra dependencies.