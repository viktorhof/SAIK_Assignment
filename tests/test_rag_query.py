import unittest
from pathlib import Path

import scripts.rag_query as rag_query


ROOT = Path(__file__).resolve().parent.parent


class RagQueryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ontology = rag_query.load_ontology_graph(
            ROOT / "ontology" / "plant_management_oops_fixed.ttl"
        )

    def test_generated_query_must_be_read_only(self):
        with self.assertRaises(SystemExit):
            rag_query.validate_read_only_sparql("DELETE WHERE { ?s ?p ?o }")

        with self.assertRaises(SystemExit):
            rag_query.validate_read_only_sparql(
                "SELECT * WHERE { SERVICE <http://example.org> { ?s ?p ?o } }"
            )

        query = rag_query.validate_read_only_sparql(
            "SELECT * WHERE { ?s ?p ?o } LIMIT 1000"
        )
        self.assertTrue(query.endswith("LIMIT 100"))

    def test_generated_query_must_use_known_ontology_vocabulary(self):
        with self.assertRaises(SystemExit):
            rag_query.validate_read_only_sparql(
                """PREFIX plant: <http://www.semanticweb.org/plantms/ontology#>
                SELECT ?plant WHERE { ?plant plant:isSafeForCats true . }""",
                self.ontology,
            )

        query = rag_query.validate_read_only_sparql(
            """PREFIX plant: <http://www.semanticweb.org/plantms/ontology#>
            SELECT ?plant WHERE { ?plant a plant:Plant . }""",
            self.ontology,
        )
        self.assertTrue(query.endswith("LIMIT 100"))

    def test_dynamic_route_with_mocked_graphdb_and_llm(self):
        responses = iter([
            """{
              "sparql": "SELECT (SUM(?stock) AS ?totalStock) WHERE { ?product a plant:ShopProduct ; plant:hasStockQuantity ?stock ; plant:isShopProductFor ?plant . ?plant plant:belongsToFamily ?family . ?family rdfs:label \\"Araceae\\" . }",
              "reason": "Link products to plants and filter their family label."
            }""",
            "Total Araceae stock is 88 units.",
        ])
        original_call_llm = rag_query.call_llm
        original_ensure_llm_ready = rag_query.ensure_llm_ready
        original_retrieve_entity_candidates = rag_query.retrieve_entity_candidates
        original_run_sparql = rag_query.run_sparql
        rag_query.call_llm = lambda prompt, provider, ollama_url, openai_api_base, model: next(responses)
        rag_query.ensure_llm_ready = lambda provider, ollama_url: None
        rag_query.retrieve_entity_candidates = lambda endpoint, question: [{
            "entity": "http://www.semanticweb.org/plantms/ontology#Family_Araceae",
            "label": "Araceae",
        }]
        rag_query.run_sparql = lambda endpoint, sparql: [{"totalStock": "88"}]
        try:
            answer = rag_query.answer_with_llm(
                "http://mock-graphdb",
                self.ontology,
                "What is the total stock of all Araceae plants in the shop?",
                "openai",
                "http://mock-ollama",
                "http://mock-openai",
                "mock-model",
            )
        finally:
            rag_query.call_llm = original_call_llm
            rag_query.ensure_llm_ready = original_ensure_llm_ready
            rag_query.retrieve_entity_candidates = original_retrieve_entity_candidates
            rag_query.run_sparql = original_run_sparql

        self.assertEqual(answer, "Total Araceae stock is 88 units.")

    def test_entity_candidate_formatting(self):
        rows = [{"entity": "http://example.org/Family_Araceae", "label": "Araceae"}]
        self.assertEqual(
            rag_query.format_entity_candidates(rows),
            "- <http://example.org/Family_Araceae>; label=Araceae",
        )

    def test_openai_output_text_extraction(self):
        result = {
            "output": [{
                "type": "message",
                "content": [{"type": "output_text", "text": "grounded answer"}],
            }],
        }
        self.assertEqual(
            rag_query.extract_openai_output_text(result),
            "grounded answer",
        )


if __name__ == "__main__":
    unittest.main()
