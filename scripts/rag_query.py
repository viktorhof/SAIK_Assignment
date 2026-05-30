#!/usr/bin/env python3
"""
Step 5 query interface for the Plant Management knowledge graph.

The default route follows the lecture's SPARQL-generation approach: retrieve
relevant ontology terms and KG entities, ask an LLM to construct a read-only
SPARQL query, execute it against GraphDB, and generate an answer grounded in the
returned rows. There is no vector index or embedding search.

"""

import argparse
import json
import os
from pathlib import Path
import re
import textwrap
import urllib.error
import urllib.parse
import urllib.request


ROOT = Path(__file__).resolve().parent.parent


def load_dotenv(path):
    if not path.exists():
        return

    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        name = name.strip()
        value = value.strip().strip("\"'")
        if name and name not in os.environ:
            os.environ[name] = value


load_dotenv(ROOT / ".env")

DEFAULT_ENDPOINT = os.getenv(
    "GRAPHDB_ENDPOINT",
    "http://localhost:7200/repositories/plantms",
)
DEFAULT_ONTOLOGY = ROOT / "ontology" / "plant_management_oops_fixed.ttl"
DEFAULT_PROVIDER = os.getenv("LLM_PROVIDER", "ollama")
DEFAULT_OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
DEFAULT_OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")
DEFAULT_OPENAI_API_BASE = os.getenv("OPENAI_API_BASE", "https://api.openai.com")
DEFAULT_OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5-mini")
PLANT_PREFIX = "http://www.semanticweb.org/plantms/ontology#"

PREFIXES = """
PREFIX plant: <http://www.semanticweb.org/plantms/ontology#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
"""

DEMO_QUERIES = [
    "What is the total stock of all Araceae plants in the shop?",
    "Do we have enough Orchidaceae stock for an order of 5?",
    "What easy-care climbing plants cost under EUR 30?",
    "Which shop products require warm temperature and have been on the shelf for a long time?",
    "Which low-light plants tolerate high soil salinity?",
    "Which plants are edible and have edible leaves and roots?",
    "Which plants have blue flowers?",
    "Which plants grow in poor soil?",
    "Which plants bloom in January?",
    "Which plants belong to family Pinaceae?",
    "What is the maximum height of Pinaceae plants?",
]

STOP_WORDS = {
    "about", "after", "all", "also", "among", "answer", "are", "been",
    "belong", "belongs", "can", "cost", "does", "enough", "for", "from",
    "given", "have", "how", "into", "long", "many", "much", "need", "old",
    "only", "order", "plant", "plants", "product", "products", "require",
    "requires", "shop", "should", "show", "that", "the", "their", "them",
    "there", "these", "they", "this", "under", "what", "which", "with",
}

TERM_ALIASES = {
    "bloom": ["flower", "month"],
    "climbing": ["vine", "growth habit"],
    "cost": ["price", "eur"],
    "easy-care": ["easy", "care level"],
    "family": ["belongs to family"],
    "height": ["maximum height"],
    "old": ["shelf date"],
    "salinity": ["soil salinity"],
    "stock": ["stock quantity"],
    "warm": ["temperature category"],
}

CORE_SCHEMA_NAMES = {
    "Plant", "ShopProduct", "Family", "Genus", "Flower", "belongsToFamily",
    "belongsToGenus", "hasScientificName", "hasProductName", "hasStockQuantity",
    "hasPriceEur", "isShopProductFor", "hasComponent", "hasColor",
}

EXAMPLE_PLANS = """
Question: What is the total stock of all Araceae plants in the shop?
SPARQL:
SELECT (SUM(?stock) AS ?totalStock) WHERE {
  ?product a plant:ShopProduct ;
           plant:hasStockQuantity ?stock ;
           plant:isShopProductFor ?plant .
  ?plant plant:belongsToFamily ?family .
  ?family rdfs:label "Araceae" .
}

Question: Which plants have blue flowers?
SPARQL:
SELECT ?scientificName WHERE {
  ?plant a plant:Plant ;
         plant:hasScientificName ?scientificName ;
         plant:hasComponent ?flower .
  ?flower a plant:Flower ;
          plant:hasColor plant:FlowerColor_Blue .
}
LIMIT 50

Question: What is the maximum height of Pinaceae plants?
SPARQL:
SELECT (MAX(?height) AS ?maximumHeightCm) WHERE {
  ?plant a plant:Plant ;
         plant:hasMaximumHeightCm ?height ;
         plant:belongsToFamily ?family .
  ?family rdfs:label "Pinaceae" .
}
"""


def load_ontology_graph(ontology_path):
    try:
        from rdflib import Graph
    except ImportError:
        raise SystemExit("rdflib is required for ontology retrieval.")

    if not ontology_path.exists():
        raise SystemExit(f"Ontology file not found: {ontology_path}")

    graph = Graph()
    graph.parse(str(ontology_path), format="turtle")
    return graph


def query_graphdb(endpoint, sparql):
    data = urllib.parse.urlencode({"query": sparql}).encode("utf-8")
    request = urllib.request.Request(
        endpoint,
        data=data,
        headers={
            "Accept": "application/sparql-results+json",
            "Content-Type": "application/x-www-form-urlencoded; charset=utf-8",
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as error:
        raise SystemExit(
            "Could not query GraphDB. Start GraphDB, create repository 'plantms', "
            f"and load the materialized KG.\n"
            f"Endpoint: {endpoint}\n"
            f"Error: {error}"
        )

    variables = payload.get("head", {}).get("vars", [])
    rows = []
    for binding in payload.get("results", {}).get("bindings", []):
        row = {}
        for variable in variables:
            value = binding.get(variable)
            row[variable] = value.get("value") if value else ""
        rows.append(row)
    return rows


def run_sparql(endpoint, sparql):
    return query_graphdb(endpoint, sparql)


def local_name(uri):
    text = str(uri)
    if "#" in text:
        return text.rsplit("#", 1)[1]
    return text.rstrip("/").rsplit("/", 1)[-1]


def question_terms(question):
    terms = set(re.findall(r"[a-z0-9]+(?:-[a-z0-9]+)?", question.lower()))
    expanded = set(terms)
    for term in terms:
        if term in TERM_ALIASES:
            for alias in TERM_ALIASES[term]:
                expanded.update(alias.split())
    return sorted(
        term for term in expanded
        if len(term) >= 3 and term not in STOP_WORDS
    )


def ontology_schema_terms(graph):
    from rdflib import URIRef
    from rdflib.namespace import OWL, RDF, RDFS

    type_names = [
        (OWL.Class, "class"),
        (OWL.ObjectProperty, "object property"),
        (OWL.DatatypeProperty, "datatype property"),
    ]

    terms = []
    for rdf_type, kind in type_names:
        for subject in graph.subjects(RDF.type, rdf_type):
            label = graph.value(subject, RDFS.label)
            comment = graph.value(subject, RDFS.comment)
            domain = graph.value(subject, RDFS.domain)
            range_value = graph.value(subject, RDFS.range)
            terms.append({
                "uri": str(subject),
                "name": local_name(subject),
                "kind": kind,
                "label": str(label) if label else local_name(subject),
                "comment": str(comment) if comment else "",
                "domain": local_name(domain) if isinstance(domain, URIRef) else "",
                "range": local_name(range_value) if isinstance(range_value, URIRef) else "",
            })
    return terms


def schema_score(term, words):
    haystack = " ".join([
        term["name"], term["label"], term["comment"], term["domain"], term["range"],
    ]).lower()
    score = 0
    for word in words:
        if word in term["name"].lower():
            score += 5
        elif word in term["label"].lower():
            score += 4
        elif word in haystack:
            score += 1
    if term["name"] in CORE_SCHEMA_NAMES:
        score += 2
    return score


def retrieve_schema_terms(ontology_graph, question, limit=35):
    words = question_terms(question)
    terms = ontology_schema_terms(ontology_graph)
    terms.sort(key=lambda term: (-schema_score(term, words), term["kind"], term["name"]))
    return terms[:limit]


def retrieve_entity_candidates(endpoint, question, limit=30):
    try:
        from rdflib import Literal
    except ImportError:
        raise SystemExit("rdflib is required for KG entity retrieval.")

    words = question_terms(question)
    if not words:
        return []

    needle_values = " ".join(Literal(word).n3() for word in words[:15])
    sparql = PREFIXES + f"""
SELECT DISTINCT ?entity ?label
WHERE {{
  VALUES ?needle {{ {needle_values} }}
  ?entity rdfs:label ?label .
  FILTER(CONTAINS(LCASE(STR(?label)), ?needle))
}}
ORDER BY ?label
LIMIT {limit}
"""
    return run_sparql(endpoint, sparql)


def format_schema_terms(terms):
    lines = []
    for term in terms:
        details = [term["kind"], f"plant:{term['name']}", f"label={term['label']}"]
        if term["domain"]:
            details.append(f"domain={term['domain']}")
        if term["range"]:
            details.append(f"range={term['range']}")
        lines.append("- " + "; ".join(details))
    return "\n".join(lines)


def format_entity_candidates(rows):
    if not rows:
        return "- No labeled KG entity matched the question lexically."

    lines = []
    for row in rows:
        lines.append(
            f"- <{row.get('entity', '')}>; label={row.get('label', '')}"
        )
    return "\n".join(lines)


def ensure_ollama_ready(ollama_url):
    endpoint = ollama_url.rstrip("/") + "/api/tags"
    request = urllib.request.Request(endpoint, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=5):
            return
    except (urllib.error.URLError, TimeoutError) as error:
        raise SystemExit(
            "Could not reach Ollama. Start Ollama and pull the configured model, "
            "or use --provider openai with OPENAI_API_KEY.\n"
            f"Ollama URL: {ollama_url}\n"
            f"Error: {error}"
        )


def call_ollama(prompt, ollama_url, model):
    endpoint = ollama_url.rstrip("/") + "/api/generate"
    payload = json.dumps({
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0},
    }).encode("utf-8")
    request = urllib.request.Request(
        endpoint,
        data=payload,
        headers={"Content-Type": "application/json"},
    )

    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            result = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError) as error:
        raise SystemExit(
            "Could not query Ollama. Start Ollama and pull the configured model, "
            "or use --provider openai with OPENAI_API_KEY.\n"
            f"Ollama URL: {ollama_url}\n"
            f"Model: {model}\n"
            f"Error: {error}"
        )

    answer = result.get("response", "").strip()
    if not answer:
        raise SystemExit("Ollama returned an empty response.")
    return answer


def openai_api_key():
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise SystemExit(
            "OPENAI_API_KEY is not set. Copy .env.example to .env, add your key, "
            "and run the command again. The .env file is ignored by git."
        )
    return api_key


def extract_openai_output_text(result):
    output_text = result.get("output_text", "").strip()
    if output_text:
        return output_text

    parts = []
    for item in result.get("output", []):
        for content in item.get("content", []):
            if content.get("type") == "output_text" and content.get("text"):
                parts.append(content["text"])
    return "\n".join(parts).strip()


def call_openai(prompt, api_base, model):
    endpoint = api_base.rstrip("/") + "/v1/responses"
    payload = json.dumps({
        "model": model,
        "input": prompt,
        "max_output_tokens": 2000,
    }).encode("utf-8")
    request = urllib.request.Request(
        endpoint,
        data=payload,
        headers={
            "Authorization": "Bearer " + openai_api_key(),
            "Content-Type": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            result = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        details = error.read().decode("utf-8", errors="replace")
        raise SystemExit(
            "OpenAI Responses API request failed.\n"
            f"Endpoint: {endpoint}\n"
            f"Model: {model}\n"
            f"HTTP status: {error.code}\n"
            f"Response: {details}"
        )
    except (urllib.error.URLError, TimeoutError) as error:
        raise SystemExit(
            "Could not query the OpenAI Responses API.\n"
            f"Endpoint: {endpoint}\n"
            f"Model: {model}\n"
            f"Error: {error}"
        )

    answer = extract_openai_output_text(result)
    if not answer:
        raise SystemExit("The OpenAI Responses API returned no text output.")
    return answer


def ensure_llm_ready(provider, ollama_url):
    if provider == "openai":
        openai_api_key()
        return
    ensure_ollama_ready(ollama_url)


def call_llm(prompt, provider, ollama_url, openai_api_base, model):
    if provider == "openai":
        return call_openai(prompt, openai_api_base, model)
    return call_ollama(prompt, ollama_url, model)


def parse_planner_response(response, ontology_graph=None):
    text = response.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json|sparql)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)

    reason = ""
    try:
        result = json.loads(text)
        sparql = result.get("sparql", "")
        reason = result.get("reason", "")
    except json.JSONDecodeError:
        match = re.search(r"(?is)(PREFIX\s+.+?\bSELECT\b.+)", text)
        if not match:
            match = re.search(r"(?is)(\bSELECT\b.+)", text)
        sparql = match.group(1) if match else ""

    return validate_read_only_sparql(sparql, ontology_graph), reason


def ontology_vocabulary_names(ontology_graph):
    from rdflib import URIRef

    names = set()
    for term in ontology_graph.all_nodes():
        if isinstance(term, URIRef) and str(term).startswith(PLANT_PREFIX):
            names.add(local_name(term))
    return names


def validate_ontology_vocabulary(query, ontology_graph):
    if ontology_graph is None:
        return

    used_names = set(re.findall(r"\bplant:([A-Za-z_][A-Za-z0-9._-]*)", query))
    used_names.update(
        re.findall(r"<" + re.escape(PLANT_PREFIX) + r"([^>]+)>", query)
    )
    unknown_names = sorted(used_names - ontology_vocabulary_names(ontology_graph))
    if unknown_names:
        raise SystemExit(
            "Rejected generated SPARQL: unknown ontology term(s): "
            + ", ".join("plant:" + name for name in unknown_names)
        )


def validate_read_only_sparql(sparql, ontology_graph=None):
    query = sparql.strip()
    if not query:
        raise SystemExit("The LLM did not return a SPARQL query.")

    blocked_keywords = [
        "ADD", "CLEAR", "COPY", "CREATE", "DELETE", "DROP", "INSERT", "LOAD",
        "MOVE", "SERVICE", "WITH",
    ]
    for keyword in blocked_keywords:
        if re.search(rf"\b{keyword}\b", query, flags=re.IGNORECASE):
            raise SystemExit(f"Rejected generated SPARQL: {keyword} is not allowed.")

    operation = re.sub(
        r"(?im)^\s*PREFIX\s+\w*:\s*<[^>]+>\s*$",
        "",
        query,
    ).lstrip()
    if not re.match(r"(?i)^SELECT\b", operation):
        raise SystemExit("Rejected generated SPARQL: only SELECT queries are allowed.")

    validate_ontology_vocabulary(query, ontology_graph)

    if re.search(r"\bLIMIT\s+(\d+)", query, flags=re.IGNORECASE):
        query = re.sub(
            r"\bLIMIT\s+(\d+)",
            lambda match: f"LIMIT {min(int(match.group(1)), 100)}",
            query,
            flags=re.IGNORECASE,
        )
    else:
        query += "\nLIMIT 100"

    return query


def planner_prompt(question, schema_terms, entity_candidates):
    return f"""
You construct a read-only SPARQL SELECT query for a plant-management RDF graph.
Use only the supplied ontology vocabulary and exact entity URIs or labels.
Do not invent classes, properties, or entity identifiers.
Do not use SERVICE, updates, or markdown fences.
Return JSON with exactly two strings: "sparql" and "reason".

Prefixes:
{PREFIXES.strip()}

Relevant ontology vocabulary:
{format_schema_terms(schema_terms)}

Lexically linked KG entities:
{format_entity_candidates(entity_candidates)}

Examples:
{EXAMPLE_PLANS.strip()}

Question: {question}
""".strip()


def answer_prompt(question, sparql, rows):
    row_json = json.dumps(rows[:100], ensure_ascii=True, indent=2)
    return f"""
Answer the user's question only from the SPARQL result rows below.
Do not add facts that are not present in the rows.
If the rows are empty, state that no matching KG rows were found.
Keep the answer concise and mention important counts or values.

Question:
{question}

Executed SPARQL:
{sparql}

SPARQL result rows:
{row_json}
""".strip()


def answer_with_llm(endpoint, ontology_graph, question, provider, ollama_url, openai_api_base, model, show_plan=False, plan_only=False):
    ensure_llm_ready(provider, ollama_url)
    schema_terms = retrieve_schema_terms(ontology_graph, question)
    entity_candidates = retrieve_entity_candidates(endpoint, question)
    response = call_llm(
        planner_prompt(question, schema_terms, entity_candidates),
        provider,
        ollama_url,
        openai_api_base,
        model,
    )
    sparql, reason = parse_planner_response(response, ontology_graph)

    if show_plan or plan_only:
        print("Retrieved schema candidates:")
        print(format_schema_terms(schema_terms))
        print("\nRetrieved entity candidates:")
        print(format_entity_candidates(entity_candidates))
        if reason:
            print("\nPlanner reason:")
            print(reason)
        print("\nGenerated SPARQL:")
        print(sparql)

    if plan_only:
        return ""

    rows = run_sparql(endpoint, sparql)
    return call_llm(
        answer_prompt(question, sparql, rows),
        provider,
        ollama_url,
        openai_api_base,
        model,
    )


def interactive_loop(answer_function):
    print("=" * 60)
    print("Plant Management KG Query CLI")
    print("KG-based RAG with SPARQL retrieval. Type 'help' for examples, 'quit' to exit.")
    print("=" * 60)

    while True:
        try:
            question = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye.")
            break

        if not question:
            continue
        if question.lower() in ("quit", "exit", "q"):
            print("Bye.")
            break
        if question.lower() == "help":
            for demo_query in DEMO_QUERIES:
                print("- " + demo_query)
            continue

        print_wrapped(answer_function(question))


def print_wrapped(text):
    for line in text.splitlines():
        if len(line) > 110:
            print(textwrap.fill(line, width=110, subsequent_indent="  "))
        else:
            print(line)


def main():
    parser = argparse.ArgumentParser(
        description="Plant Management KG-based RAG query interface"
    )
    parser.add_argument("--query", "-q", help="Single question to answer.")
    parser.add_argument("--demo", action="store_true", help="Run the demo questions.")
    parser.add_argument(
        "--endpoint",
        default=DEFAULT_ENDPOINT,
        help=f"GraphDB SPARQL endpoint (default: {DEFAULT_ENDPOINT})",
    )
    parser.add_argument(
        "--ontology",
        default=str(DEFAULT_ONTOLOGY),
        help=f"Ontology Turtle file for schema retrieval (default: {DEFAULT_ONTOLOGY}).",
    )
    parser.add_argument(
        "--provider",
        choices=["ollama", "openai"],
        default=DEFAULT_PROVIDER,
        help=f"LLM provider for planning and answers (default: {DEFAULT_PROVIDER}).",
    )
    parser.add_argument(
        "--ollama-url",
        default=DEFAULT_OLLAMA_URL,
        help=f"Ollama API base URL (default: {DEFAULT_OLLAMA_URL}).",
    )
    parser.add_argument(
        "--openai-api-base",
        default=DEFAULT_OPENAI_API_BASE,
        help=f"OpenAI API base URL (default: {DEFAULT_OPENAI_API_BASE}).",
    )
    parser.add_argument(
        "--model",
        help="Model used for planning and answers. Defaults to llama3 for Ollama or gpt-5-mini for OpenAI.",
    )
    parser.add_argument(
        "--show-plan",
        action="store_true",
        help="Print retrieved candidates and generated SPARQL before the answer.",
    )
    parser.add_argument(
        "--plan-only",
        action="store_true",
        help="Generate and print SPARQL without executing it.",
    )
    args = parser.parse_args()

    model = args.model
    if not model:
        model = DEFAULT_OPENAI_MODEL if args.provider == "openai" else DEFAULT_OLLAMA_MODEL
    ontology_graph = load_ontology_graph(Path(args.ontology))
    answer_function = lambda question: answer_with_llm(
        args.endpoint,
        ontology_graph,
        question,
        args.provider,
        args.ollama_url,
        args.openai_api_base,
        model,
        show_plan=args.show_plan,
        plan_only=args.plan_only,
    )

    if args.demo:
        for index, question in enumerate(DEMO_QUERIES, 1):
            print(f"\n[{index}] {question}")
            print("-" * 60)
            print_wrapped(answer_function(question))
        return

    if args.query:
        print_wrapped(answer_function(args.query))
        return

    interactive_loop(answer_function)


if __name__ == "__main__":
    main()
