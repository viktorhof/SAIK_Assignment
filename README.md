# Plant Management Knowledge Graph

Semantic AI and Knowledge Systems assignment based on the
[Trefle](https://trefle.io/) species dataset. The project builds an OWL
ontology, loads plant and mock-shop data into SQLite, materializes an RDF
knowledge graph, imports it into GraphDB, and answers natural-language questions
by generating SPARQL with an LLM.

The application runtime uses Python and Docker Desktop.

## Runtime Flow

```text
Natural-language question
  -> retrieve relevant ontology terms from the local OWL ontology
  -> retrieve matching labeled entities from GraphDB
  -> ask the configured LLM to generate a read-only SPARQL SELECT query
  -> validate and execute the query against GraphDB
  -> ask the LLM to answer only from the returned rows
```

The knowledge graph stays in GraphDB. There is no vector database, embedding
index, local-TTL query mode, or template fallback.

## Prerequisites

- Python 3.12 or newer
- Docker Desktop with Linux containers enabled
- An OpenAI API key, or a local [Ollama](https://ollama.com/) installation
- `data/plantms_full_kg.ttl` for the initial GraphDB import

The generated full KG is approximately 1.9 GB and is intentionally ignored by
git.

## Quick Start

### 1. Install Python dependencies

PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

macOS or Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

### 2. Configure the LLM

For OpenAI, create the ignored local `.env` file:

```powershell
Copy-Item .env.example .env
```

Set your key in `.env`:

```dotenv
LLM_PROVIDER=openai
OPENAI_API_KEY=replace-me
OPENAI_MODEL=gpt-5-mini
OPENAI_API_BASE=https://api.openai.com
```

The query CLI loads `.env` automatically. `gpt-5-mini` is the default OpenAI
model because SPARQL generation benefits from a capable model while remaining
inexpensive.

For a local Ollama setup:

```bash
ollama pull llama3
```

Then use `--provider ollama` when running queries.

### 3. Start GraphDB

```bash
docker compose up -d
```

Open [http://localhost:7200](http://localhost:7200).

The Compose service:

- runs the pinned image `ontotext/graphdb:10.8.14`
- persists repository data in a Docker volume
- exposes `./data` as GraphDB's read-only server import directory
- publishes Workbench on `http://localhost:7200`

### 4. Import the KG once

Skip this section if repository `plantms` already exists and contains the data.

In GraphDB Workbench:

1. Open `Setup -> Repositories`.
2. Create a repository named `plantms` with the default settings.
3. Open `Import`.
4. Upload `ontology/plant_management_oops_fixed.ttl` from `User data`.
5. Import `plantms_full_kg.ttl` from `Server files`.
6. Wait for the full KG import to finish.

The server-file import is important because the KG is too large for a browser
upload. On the tested machine the full import took approximately 10 minutes.

Verified local repository counts:

| Measure | Value |
| --- | ---: |
| Explicit statements | 11,105,948 |
| Inferred statements | 6,977,509 |
| Total statements | 18,083,457 |
| `plant:Plant` instances | 416,473 |
| `plant:ShopProduct` instances | 95 |

### 5. Ask a question

OpenAI:

```bash
python scripts/rag_query.py --provider openai --show-plan --query "What is the total stock of all Araceae plants in the shop?"
```

Expected grounded answer:

```text
The total stock of all Araceae plants in the shop is 88.
```

Interactive mode:

```bash
python scripts/rag_query.py --provider openai
```

Run all demo questions:

```bash
python scripts/rag_query.py --provider openai --demo
```

Use Ollama instead:

```bash
python scripts/rag_query.py --provider ollama --query "Which plants have blue flowers?"
```

## Rebuild the Data and KG

The normal query workflow only requires GraphDB to be running. Use this section
when regenerating artifacts from source.

### 1. Provide the Trefle input

Place the Trefle export at:

```text
data/raw/species.csv
```

### 2. Generate the ontology

```bash
python scripts/generate_ontology.py
python scripts/apply_oops_fixes.py
```

Generated ontology artifacts:

```text
ontology/plant_management.ttl
ontology/plant_management.rdf
ontology/plant_management_oops_fixed.ttl
ontology/plant_management_oops_fixed.rdf
```

### 3. Generate the mock shop data and SQLite database

```bash
python scripts/generate_shop_data.py
python scripts/load_database.py
```

Generated data artifacts:

```text
data/shop/inventory.csv
data/plantms.db
```

Current SQLite counts:

| Table | Rows |
| --- | ---: |
| `plant` | 416,473 |
| `family` | 580 |
| `genus` | 15,540 |
| `plant_distribution` | 1,306,113 |
| `shop_product` | 95 |

### 4. Materialize the full RDF knowledge graph

The tested materialization command is:

```bash
python scripts/materialize_full_kg.py
```

It writes:

```text
data/plantms_full_kg.ttl
```

The generated KG currently contains `11,104,833` RDF triples before GraphDB
inference.

## R2RML and Ontop

The course OBDA artifact is:

```text
plant_management_r2rml.ttl
```

It maps normalized SQLite tables to the ontology, including plants, taxonomy,
multi-valued trait relations, distributions, plant parts, colors, and shop
products.

The Ontop configuration is:

```text
config/ontop.properties
```

The intended Ontop command is:

```bash
ontop materialize \
  -m plant_management_r2rml.ttl \
  -t ontology/plant_management_oops_fixed.ttl \
  -p config/ontop.properties \
  -f turtle \
  -o data/plantms_full_kg.ttl
```

Ontop 5.4.0 was tested with the SQLite JDBC driver, but its generated SQL failed
against SQLite near `UNION` for predicates produced by multiple triples maps.
The direct materializer is retained as the working full-KG generation path. It
follows the same normalized database structure and RDF predicate structure.

## Verification Artifacts

### OOPS

The original OOPS scan and follow-up notes are stored in:

```text
data/oops_scan/
OOPS_FINDINGS.md
OOPS_FIXES.md
```

### SHACL

The SHACL rules are stored in:

```text
plant_management_shapes.ttl
```

Manual submission step: run validation with the TopBraid SHACL engine using:

- data graph: `data/plantms_full_kg.ttl`
- additional data graph: `ontology/plant_management_oops_fixed.ttl`
- shapes graph: `plant_management_shapes.ttl`

Export the final Turtle report as:

```text
plant_management_validation_report.ttl
```

The checked-in report is provisional until it is replaced with the TopBraid
export.

### Alignment

The first-stage Plant Ontology alignment is:

```text
plant_management_po_alignment.ttl
```

## Smoke Checks

Run these in GraphDB Workbench under `SPARQL`:

```sparql
PREFIX plant: <http://www.semanticweb.org/plantms/ontology#>

SELECT (COUNT(?plant) AS ?plants) WHERE {
  ?plant a plant:Plant .
}
```

```sparql
PREFIX plant: <http://www.semanticweb.org/plantms/ontology#>

SELECT (COUNT(?product) AS ?products) WHERE {
  ?product a plant:ShopProduct .
}
```

Run the Python regression suite:

```bash
python -m unittest tests.test_rag_query -v
```

## Important Files

```text
compose.yaml                         GraphDB Docker service
.env.example                         Local LLM configuration template
flake.nix                            Optional Nix development shell
scripts/rag_query.py                  GraphDB-backed natural-language query CLI
scripts/materialize_full_kg.py        Working full-KG materializer
scripts/generate_ontology.py          Base ontology generator
scripts/apply_oops_fixes.py           OOPS follow-up fixes
scripts/generate_shop_data.py         Mock inventory generator
scripts/load_database.py              SQLite loader
plant_management_r2rml.ttl            R2RML OBDA mapping
plant_management_shapes.ttl           SHACL rules
plant_management_po_alignment.ttl     Plant Ontology alignment
ontology/README.md                    Ontology schema documentation
report.tex                            Technical report source
```

## Optional Developer Convenience

The checked-in `.envrc` only loads `.env` for users who already use direnv.
Direnv is optional and is not part of the required workflow.

An optional Nix development shell is also available:

```bash
nix develop
```

The flake provides Python, SQLite, Java, the SQLite JDBC driver, TeX, and basic
utilities for artifact generation. It is not used by the normal Python and
Docker workflow. It intentionally excludes the removed vector-search
dependencies.
