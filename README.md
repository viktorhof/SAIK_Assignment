# SAIK_Assignment

Semantic AI and Knowledge Systems (SAIK) assignment — Plant Management System Ontology.
Data source: [Trefle](https://trefle.io/) `species.csv` (54 columns, ~35 k plant species rows).

---

## Project Structure

```
data/raw/species.csv          # Trefle species dataset (TSV format)
scripts/generate_ontology.py  # Step 1: generates the OWL2 TBox
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
  Triples            : 890
  Classes            : 35
  Object properties  : 23
  Datatype properties: 27
  Named individuals  : 80
```

See [ontology/README.md](ontology/README.md) for the full schema documentation
(class hierarchy, properties, OWL2 features, ODPs, competency questions).