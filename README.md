# Plant Management Knowledge Graph

Semantic AI and Knowledge Systems assignment based on the
[Trefle](https://trefle.io/) species dataset. The project builds an OWL2
ontology, loads plant and shop data into SQLite, materializes a full RDF
knowledge graph, imports it into GraphDB, and answers natural-language questions
by generating SPARQL with an LLM.

## RAG pipeline

```text
Natural-language question
  -> retrieve relevant ontology terms from the local OWL file
  -> retrieve matching labeled entities from GraphDB
  -> ask the LLM to generate a read-only SPARQL SELECT query
  -> validate and execute the query against GraphDB
  -> ask the LLM to answer only from the returned rows
```

No vector database or embedding index is used. The knowledge graph lives
entirely in GraphDB.

---

## Prerequisites

| Requirement | Notes |
|---|---|
| Python 3.12+ | `python3 --version` to verify |
| Docker Desktop | Linux containers enabled; used to run GraphDB |
| OpenAI API key | Stored in `.env` (never committed) |
| `data/raw/species.csv` | Trefle plant dataset — must be present before running any script |

---

## Full pipeline (from scratch)

Run these steps in order. Each step's output becomes the next step's input.

### Step 0 — Python environment

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Step 1 — Configure the LLM

```bash
cp .env.example .env
```

Edit `.env` and set your OpenAI API key:

```dotenv
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
OPENAI_API_BASE=https://api.openai.com
```

### Step 2 — Generate the ontology

```bash
python scripts/generate_ontology.py
python scripts/apply_oops_fixes.py
```

Generated files:

```
ontology/plant_management.ttl
ontology/plant_management.rdf
ontology/plant_management_oops_fixed.ttl      ← used by all downstream steps
ontology/plant_management_oops_fixed.rdf
```

Runtime: a few seconds.

### Step 3 — Generate shop data and load SQLite

```bash
python scripts/generate_shop_data.py
python scripts/load_database.py
```

Generated files:

```
data/shop/inventory.csv
data/plantms.db
```

Expected SQLite row counts:

| Table | Rows |
|---|---:|
| `plant` | 416,473 |
| `family` | 580 |
| `genus` | 15,540 |
| `plant_distribution` | 1,306,113 |
| `shop_product` | 95 |

Runtime: `load_database.py` takes 5–10 minutes on a standard machine.

### Step 4 — Materialize the full RDF knowledge graph

```bash
python scripts/materialize_full_kg.py
```

Generated file:

```
data/plantms_full_kg.ttl        (~1.9 GB, ~11.1 million triples)
```

Runtime: 30–60 minutes. Progress is printed to stdout.

> **Note on R2RML/Ontop:** The course OBDA artifact is `plant_management_r2rml.ttl`.
> Ontop 5.4.0 was tested but its generated SQL failed against SQLite near `UNION`
> clauses for predicates produced by multiple triples maps. The Python materializer
> above follows the same schema and predicate structure and is the working path.

### Step 5 — Start GraphDB

```bash
docker compose up -d
```

Open [http://localhost:7200](http://localhost:7200). The Compose service runs
`ontotext/graphdb:10.8.14`, persists data in a Docker volume, and exposes
`./data` as GraphDB's server import directory.

### Step 6 — Import the KG into GraphDB

Do this once. Skip if repository `plantms` already exists with data.

1. Open `Setup → Repositories` → create a repository named **`plantms`** with default settings.
   For GraphDB 10.8, the default inference ruleset is **RDFS-Plus (optimized)**
   (`rdfsplus-optimized`). This is the setting used for the statement counts below.
2. Open `Import → Server files` → select `plantms_full_kg.ttl` → import.
3. Open `Import → User data` → upload `ontology/plant_management_oops_fixed.ttl` → import.
4. Wait for both imports to finish (the KG import takes ~10 minutes).

Inference in GraphDB is configured on the repository through the **Ruleset**
setting. The main built-in choices are:

| Ruleset | Meaning |
|---|---|
| `empty` | No inference; GraphDB behaves as a plain RDF store. |
| `rdfs` / `rdfs-optimized` | RDFS reasoning such as `rdfs:subClassOf`, `rdf:type`, and `rdfs:subPropertyOf`. |
| `rdfsplus` / `rdfsplus-optimized` | RDFS plus selected OWL features such as symmetric, inverse, and transitive properties. This is the default used here. |
| `owl-horst` / `owl-horst-optimized` | OWL-Horst-style rule reasoning. |
| `owl-max` / `owl-max-optimized` | Broader OWL Lite/DLP-style rule coverage, including more OWL constructs. |
| `owl2-ql` | OWL 2 QL profile reasoning. |
| `owl2-rl` / `owl2-rl-optimized` | OWL 2 RL profile reasoning, suitable for rule-based materialisation. |
| custom `.pie` file | Project-specific axioms, consistency checks, and entailment rules. |

Related repository options are **Disable owl:sameAs**, which controls GraphDB's
`owl:sameAs` optimization independently from the selected ruleset, and
**Enable consistency checks**, which applies consistency rules at transaction
commit time. Both were left at default settings for this project.

Verify the import in `SPARQL`:

```sparql
PREFIX plant: <http://www.semanticweb.org/plantms/ontology#>
SELECT (COUNT(?p) AS ?plants) WHERE { ?p a plant:Plant . }
```

Expected: **416,473 plants**.

```sparql
PREFIX plant: <http://www.semanticweb.org/plantms/ontology#>
SELECT (COUNT(?p) AS ?products) WHERE { ?p a plant:ShopProduct . }
```

Expected: **95 products**.

| Measure | Value |
|---|---:|
| Explicit statements | 11,105,948 |
| Inferred statements | 6,977,509 |
| Total statements | 18,083,457 |

### Step 7 — Run a query (CLI)

Single query:

```bash
python scripts/rag_query.py --query "What is the total stock of all Araceae plants in the shop?"
```

Expected answer: `The total stock of all Araceae plants in the shop is 88.`

Run all 11 demo questions:

```bash
python scripts/rag_query.py --demo
```

Interactive mode:

```bash
python scripts/rag_query.py
```

### Step 8 — Launch the web UI

```bash
streamlit run scripts/app.py
```

Opens at [http://localhost:8501](http://localhost:8501). The sidebar lets you
configure the model and GraphDB endpoint. Demo questions appear as buttons.

---

## Verification artifacts

### OOPS

The OOPS pitfall scan results and applied fixes are documented in:

```
OOPS_FINDINGS.md
OOPS_FIXES.md
```

### SHACL validation

Rules: `plant_management_shapes.ttl`

Run validation manually with the TopBraid SHACL engine:
- Data graph: `data/plantms_full_kg.ttl`
- Additional data: `ontology/plant_management_oops_fixed.ttl`
- Shapes graph: `plant_management_shapes.ttl`

Export the result as `plant_management_validation_report.ttl`.

### Ontology alignment

First-stage alignment with the Plant Ontology: `plant_management_po_alignment.ttl`

---

## Regression tests

```bash
python -m unittest tests.test_rag_query -v
```

---

## Repository layout

```
compose.yaml                          GraphDB Docker service
.env.example                          LLM configuration template
requirements.txt                      Python dependencies
report.tex                            Technical report (LaTeX)

scripts/
  generate_ontology.py                Step 2a — builds OWL2 TBox
  apply_oops_fixes.py                 Step 2b — applies OOPS fixes
  generate_shop_data.py               Step 3a — generates mock shop inventory
  load_database.py                    Step 3b — loads SQLite database
  materialize_full_kg.py              Step 4  — materializes full RDF KG
  rag_query.py                        Step 7  — CLI query interface
  app.py                              Step 8  — Streamlit web UI

ontology/
  plant_management_oops_fixed.ttl     Canonical OWL2 ontology (post-OOPS)
  README.md                           Full ontology schema documentation

plant_management_r2rml.ttl            R2RML OBDA mapping
plant_management_shapes.ttl           SHACL rules
plant_management_po_alignment.ttl     Plant Ontology alignment
plant_management_validation_report.ttl  SHACL validation report

data/
  raw/species.csv                     Trefle input (must be provided)
  shop/inventory.csv                  Generated mock shop inventory
  plantms.db                          Generated SQLite database
  plantms_full_kg.ttl                 Generated full RDF knowledge graph (~1.9 GB)

OOPS_FINDINGS.md                      OOPS scan findings
OOPS_FIXES.md                         Applied OOPS fixes
tests/test_rag_query.py               Regression tests
```
