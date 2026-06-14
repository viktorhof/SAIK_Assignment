"""Streamlit UI for querying the Plant Management knowledge graph."""

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))

import rag_query as rq  # noqa: E402


@st.cache_resource(show_spinner="Loading ontology graph…")
def get_ontology_graph():
    return rq.load_ontology_graph(rq.DEFAULT_ONTOLOGY)


def run_query(question, provider, model, endpoint):
    ontology_graph = get_ontology_graph()

    rq.ensure_llm_ready(provider, rq.DEFAULT_OLLAMA_URL)

    schema_terms = rq.retrieve_schema_terms(ontology_graph, question)
    entity_candidates = rq.retrieve_entity_candidates(endpoint, question)

    planner_response = rq.call_llm(
        rq.planner_prompt(question, schema_terms, entity_candidates),
        provider,
        rq.DEFAULT_OLLAMA_URL,
        rq.DEFAULT_OPENAI_API_BASE,
        model,
    )
    sparql, _reason = rq.parse_planner_response(planner_response, ontology_graph)

    rows = rq.run_sparql(endpoint, rq.PREFIXES + sparql)
    answer = rq.call_llm(
        rq.answer_prompt(question, sparql, rows),
        provider,
        rq.DEFAULT_OLLAMA_URL,
        rq.DEFAULT_OPENAI_API_BASE,
        model,
    )
    return answer, sparql


def _init_state():
    for key in ("last_answer", "last_sparql", "last_error"):
        if key not in st.session_state:
            st.session_state[key] = None


def _submit(question, provider, model, endpoint, show_sparql):
    if not question.strip():
        return

    st.session_state.last_answer = None
    st.session_state.last_sparql = None
    st.session_state.last_error = None

    try:
        with st.spinner("Querying knowledge graph…"):
            answer, sparql = run_query(question, provider, model, endpoint)
        st.session_state.last_answer = answer
        st.session_state.last_sparql = sparql if show_sparql else None
    except SystemExit as exc:
        st.session_state.last_error = str(exc)


def main():
    st.set_page_config(
        page_title="Plant Management KG",
        page_icon="🌿",
        layout="wide",
    )

    _init_state()

    with st.sidebar:
        st.header("Settings")

        provider = "openai"

        model = st.text_input("Model", value=rq.DEFAULT_OPENAI_MODEL)

        endpoint = st.text_input("GraphDB endpoint", value=rq.DEFAULT_ENDPOINT)

        show_sparql = st.checkbox("Show generated SPARQL", value=True)

    st.title("Plant Management KG")
    st.caption(
        "Natural-language query interface — KG-based RAG with SPARQL generation"
    )

    with st.form(key="query_form", border=False):
        col_input, col_btn = st.columns([9, 1])
        with col_input:
            question = st.text_input(
                "question",
                placeholder="Ask a question about the plant knowledge graph…",
                label_visibility="collapsed",
            )
        with col_btn:
            submitted = st.form_submit_button("→", use_container_width=True)

    if submitted:
        _submit(question, provider, model, endpoint, show_sparql)

    st.markdown("**Example questions:**")
    demo_cols = st.columns(2)
    for i, demo in enumerate(rq.DEMO_QUERIES):
        if demo_cols[i % 2].button(demo, key=f"demo_{i}"):
            _submit(demo, provider, model, endpoint, show_sparql)

    if st.session_state.last_error:
        st.error(st.session_state.last_error)

    elif st.session_state.last_answer:
        st.divider()
        st.subheader("Answer")
        st.markdown(st.session_state.last_answer)

        if st.session_state.last_sparql:
            with st.expander("Generated SPARQL"):
                st.code(st.session_state.last_sparql, language="sql")


if __name__ == "__main__":
    main()
