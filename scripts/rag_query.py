#!/usr/bin/env python3
"""
scripts/rag_query.py  –  Step 5: RAG Query Interface (CLI)
===========================================================
Retrieves semantically relevant chunks from rag/index.pkl and answers plant
questions strictly from that context via a local Ollama model (Llama 3).

The system will ONLY answer questions that can be resolved from:
  • The OWL2 Plant Management Ontology (schema, properties, individuals)
  • The ontology README (competency questions, column mappings, ODP descriptions)
  • The shop inventory CSV (products, prices, stock, care level, shelf dates)

Usage:
  # Interactive session
  python3 scripts/rag_query.py

  # Single query
  python3 scripts/rag_query.py --query "Which plants cost under €20?"

  # Show retrieved chunks (useful for debugging / assignment report)
  python3 scripts/rag_query.py --verbose --query "What is the Componency ODP?"

  # Run all competency questions from the README automatically
  python3 scripts/rag_query.py --demo

Environment variables:
  RAG_MODEL          — override the Ollama model (default: llama3)
"""

from __future__ import annotations

import argparse
import os
import pickle
import sys
import textwrap
from pathlib import Path

import numpy as np

ROOT       = Path(__file__).resolve().parent.parent
INDEX_PATH = ROOT / "rag" / "index.pkl"

EMBEDDING_MODEL = "all-MiniLM-L6-v2"
DEFAULT_MODEL   = os.getenv("RAG_MODEL", "llama3")
DEFAULT_TOP_K   = 8   # number of context chunks retrieved per query
MAX_CONTEXT_CHARS = 12_000   # cap for context window

SYSTEM_PROMPT = """\
You are a plant knowledge assistant for a Vienna plant shop.
Your knowledge is LIMITED to the context passages provided in each user message.
Do NOT use any plant knowledge from outside the provided context.

Rules:
1. Answer ONLY from the given context. If the answer is absent, say:
   "I cannot find that information in the current knowledge base."
2. Be concise and factual. Do not speculate.
3. When quoting specific values (prices, stock counts, heights, dates, scores on
   the 0–10 scale), reproduce them exactly as they appear in the context.
4. If a question can be partially answered, give the partial answer and clearly
   state what information is missing.
5. For ontology / schema questions, use the correct ontology terms
   (e.g. property names, class names, ODP names).
"""

# Competency questions from the README – used by --demo mode
DEMO_QUERIES = [
    "Which plants bloom in January?",
    "Which plants belong to family Pinaceae?",
    "Which plants have blue flowers?",
    "Which plants grow in poor soil (soil nutriments low)?",
    "Which plants are edible and have edible leaves?",
    "What is the maximum height of Pinaceae plants?",
    "Which shop products require warm temperature and have been on the shelf for a long time?",
    "What is the total stock of all Araceae plants in the shop?",
    "What easy-care climbing plants cost under €30?",
    "What is the Componency ODP and how is it used in this ontology?",
    "Explain the N-ary Distribution ODP.",
    "What OWL2 features are used in this ontology?",
]


# ─── Index loading ────────────────────────────────────────────────────────────
def load_index(index_path: Path) -> list[dict]:
    if not index_path.exists():
        print(
            f"ERROR: Index not found at {index_path}.\n"
            "Run:  python3 scripts/rag_index.py",
            file=sys.stderr,
        )
        sys.exit(1)
    with open(index_path, "rb") as f:
        chunks = pickle.load(f)
    return chunks


# ─── Embedding ────────────────────────────────────────────────────────────────
def load_embedder(model_name: str = EMBEDDING_MODEL):
    """Load the sentence-transformers model once; reuse for every query."""
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        print(
            "ERROR: sentence-transformers not installed.\n"
            "Run:  pip install sentence-transformers",
            file=sys.stderr,
        )
        sys.exit(1)
    return SentenceTransformer(model_name)


def embed_query(query: str, model) -> np.ndarray:
    return model.encode(
        [query], convert_to_numpy=True, normalize_embeddings=True
    )[0]


# ─── Retrieval ────────────────────────────────────────────────────────────────
def retrieve(
    query_emb: np.ndarray,
    chunks: list[dict],
    top_k: int = DEFAULT_TOP_K,
) -> list[tuple[float, dict]]:
    """
    Return the top-k chunks ranked by cosine similarity.
    Embeddings are already unit-normalised (done during indexing),
    so dot product == cosine similarity.
    """
    scored: list[tuple[float, dict]] = []
    for c in chunks:
        score = float(np.dot(query_emb, c["embedding"]))
        scored.append((score, c))
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[:top_k]


def build_context(scored: list[tuple[float, dict]], max_chars: int = MAX_CONTEXT_CHARS) -> str:
    """
    Assemble the retrieved chunks into a numbered context block.
    Truncates at max_chars to stay within the context window.
    """
    parts: list[str] = []
    total = 0
    for i, (score, c) in enumerate(scored, 1):
        block = (
            f"[{i}] Source: {c['source']}  |  {c['title']}\n"
            f"{c['text']}"
        )
        if total + len(block) > max_chars:
            break
        parts.append(block)
        total += len(block)
    return "\n\n---\n\n".join(parts)


# ─── Generation ───────────────────────────────────────────────────────────────
def ask_ollama(query: str, context: str, model: str) -> str:
    try:
        from langchain_community.llms import Ollama
    except ImportError:
        print(
            "ERROR: langchain-community package not installed.\n"
            "Run:  pip install langchain-community",
            file=sys.stderr,
        )
        sys.exit(1)

    # Initialize the local model
    llm = Ollama(model=model)
    
    # Combine the system prompt, context, and query
    full_prompt = (
        f"{SYSTEM_PROMPT}\n\n"
        f"Context passages from the Plant Management knowledge base:\n\n"
        f"{context}\n\n"
        f"---\n\n"
        f"Question: {query}"
    )
    
    # Generate the response
    return llm.invoke(full_prompt)


# ─── Pipeline ─────────────────────────────────────────────────────────────────
def run_query(
    query: str,
    chunks: list[dict],
    embedder,
    model: str,
    top_k: int = DEFAULT_TOP_K,
    verbose: bool = False,
) -> str:
    # 1. Embed query
    query_emb = embed_query(query, embedder)

    # 2. Retrieve
    scored = retrieve(query_emb, chunks, top_k=top_k)

    # 3. Optionally show which chunks were retrieved
    if verbose:
        print("\n  ── Retrieved chunks ──────────────────────────────")
        for i, (score, c) in enumerate(scored, 1):
            print(f"  [{i}] {score:.3f}  ({c['source']}) {c['title']}")
        print("  ─────────────────────────────────────────────────")

    # 4. Build context and call Ollama
    context = build_context(scored)
    answer  = ask_ollama(query, context, model)
    return answer


# ─── Interactive loop ─────────────────────────────────────────────────────────
def interactive_loop(
    chunks: list[dict],
    embedder,
    model: str,
    top_k: int,
    verbose: bool,
) -> None:
    print("═" * 60)
    print("  Plant Management RAG – Interactive Query Mode")
    print(f"  Model: Local {model} (Ollama) |  Top-K: {top_k}  |  Verbose: {verbose}")
    print("  Type 'help' for example questions, 'quit' to exit.")
    print("═" * 60)

    while True:
        try:
            raw = input("\n❯ ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye.")
            break

        if not raw:
            continue

        if raw.lower() in ("quit", "exit", "q"):
            print("Bye.")
            break

        if raw.lower() == "help":
            print("\nExample questions:")
            for q in DEMO_QUERIES[:6]:
                print(f"  • {q}")
            continue

        print("  Retrieving & Generating …", end="\r", flush=True)
        answer = run_query(
            raw, chunks, embedder, model, top_k=top_k, verbose=verbose
        )
        print(" " * 30)  # clear the "Retrieving…" line
        print("\nAnswer:")
        # Wrap long lines for readability in terminal
        for line in answer.splitlines():
            if len(line) > 100:
                print(textwrap.fill(line, width=100, subsequent_indent="  "))
            else:
                print(line)


# ─── Demo mode ────────────────────────────────────────────────────────────────
def demo_mode(
    chunks: list[dict],
    embedder,
    model: str,
    top_k: int,
    verbose: bool,
) -> None:
    """Run all competency questions and print results."""
    print("═" * 60)
    print(f"  Plant Management RAG – Demo Mode ({model})")
    print("═" * 60)
    for i, q in enumerate(DEMO_QUERIES, 1):
        print(f"\n[CQ{i}] {q}")
        print("-" * 60)
        answer = run_query(
            q, chunks, embedder, model, top_k=top_k, verbose=verbose
        )
        print(answer)
        print()


# ─── Entry point ──────────────────────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Plant Management RAG – query interface (Step 5)"
    )
    parser.add_argument(
        "--query", "-q", default=None,
        help="Single query string. Omit for interactive mode."
    )
    parser.add_argument(
        "--demo", action="store_true",
        help="Run all competency questions from the README and exit."
    )
    parser.add_argument(
        "--index", default=str(INDEX_PATH),
        help="Path to rag/index.pkl (default: rag/index.pkl)"
    )
    parser.add_argument(
        "--model", default=DEFAULT_MODEL,
        help=f"Ollama model name (default: {DEFAULT_MODEL})"
    )
    parser.add_argument(
        "--top-k", type=int, default=DEFAULT_TOP_K,
        help=f"Number of chunks to retrieve per query (default: {DEFAULT_TOP_K})"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Print the titles of retrieved chunks before each answer."
    )
    parser.add_argument(
        "--embedding-model", default=EMBEDDING_MODEL,
        help=f"sentence-transformers model for query embedding (default: {EMBEDDING_MODEL})"
    )
    args = parser.parse_args()

    # ── Load index ───────────────────────────────────────────────────────────
    index_path = Path(args.index)
    print(f"Loading index from {index_path} …", end=" ", flush=True)
    chunks = load_index(index_path)
    print(f"done. ({len(chunks)} chunks)")

    # ── Load embedder (once, reused for every query) ─────────────────────────
    print(f"Loading embedding model '{args.embedding_model}' …", end=" ", flush=True)
    embedder = load_embedder(args.embedding_model)
    print("done.")

    # ── Dispatch ─────────────────────────────────────────────────────────────
    top_k   = args.top_k
    verbose = args.verbose
    model   = args.model

    if args.demo:
        demo_mode(chunks, embedder, model, top_k=top_k, verbose=verbose)

    elif args.query:
        print()
        answer = run_query(
            args.query, chunks, embedder, model,
            top_k=top_k, verbose=verbose,
        )
        print("Answer:")
        print(answer)

    else:
        interactive_loop(
            chunks, embedder, model, top_k=top_k, verbose=verbose
        )


if __name__ == "__main__":
    main()