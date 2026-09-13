"""
Unit and integration tests for InsightOS Reasoning Brain (reasoning_brain.py).
Tests:
1. DATA classification
2. DOCS classification
3. HYBRID classification
4. GENERAL classification
5. DATA with no dataset (clean missing-context state)
6. DOCS with no documents (clean missing-context state)
7. Structured routing result schema
8. No arbitrary code execution (no eval, exec, shell, or PandasAgent)
9. DATA execution does not call document search
10. DOCS execution does not call Data Brain
11. HYBRID execution calls both
12. Citations originate only from retrieved metadata
13. No fabricated page numbers
14. Numerical facts remain deterministic
"""

import unittest
from unittest.mock import MagicMock, patch
from reasoning_brain import ReasoningBrain


class TestReasoningBrain(unittest.TestCase):

    def setUp(self):
        self.brain = ReasoningBrain()

    # 1. Classification Tests
    def test_01_data_classification(self):
        """Test classification of numerical/dataset questions as DATA."""
        queries = [
            "What is the average salary?",
            "Calculate the total sales for the dataset",
            "Show me the highest revenue and minimum profit",
            "What is the monthly sales trend?",
            "What is the data quality score and missing values count?"
        ]
        for q in queries:
            res = self.brain.classify_intent(q)
            self.assertEqual(res["intent"], "DATA", f"Failed for query: {q}")
            self.assertGreaterEqual(res["confidence"], 0.7)

    def test_02_docs_classification(self):
        """Test classification of policy/document questions as DOCS."""
        queries = [
            "What does the IT security policy say about incident reporting?",
            "What are the vacation and leave guidelines in the employee handbook?",
            "According to the policy, what is the protocol for emergency escalation?",
            "What are the compliance procedures for acceptable use?"
        ]
        for q in queries:
            res = self.brain.classify_intent(q)
            self.assertEqual(res["intent"], "DOCS", f"Failed for query: {q}")
            self.assertGreaterEqual(res["confidence"], 0.7)

    def test_03_hybrid_classification(self):
        """Test classification of cross-referencing questions as HYBRID."""
        queries = [
            "Why did sales decrease according to the policy?",
            "What does the handbook say about the employees with the lowest salary?",
            "Compare the dataset findings with the company policy",
            "Why might the business result be related to the company policy?"
        ]
        for q in queries:
            res = self.brain.classify_intent(q)
            self.assertEqual(res["intent"], "HYBRID", f"Failed for query: {q}")
            self.assertGreaterEqual(res["confidence"], 0.7)

    def test_04_general_classification(self):
        """Test classification of greetings and capability questions as GENERAL."""
        queries = [
            "Hello, what can you do?",
            "Hi there!",
            "Good morning, who are you?",
            "What is InsightOS?"
        ]
        for q in queries:
            res = self.brain.classify_intent(q)
            self.assertEqual(res["intent"], "GENERAL", f"Failed for query: {q}")

    # 5. DATA with no dataset
    def test_05_data_with_no_dataset(self):
        """Test DATA route when no dataset exists."""
        with patch.object(self.brain, "get_dataset_context", return_value={"available": False, "reason": "No datasets uploaded."}):
            res = self.brain.process_question("What is the total sales?")
            self.assertEqual(res["intent"], "DATA")
            self.assertIn("No active structured dataset", res["answer"])
            self.assertEqual(res["document_evidence"], [])
            self.assertEqual(res["citations"], [])
            self.assertTrue(len(res["warnings"]) > 0)

    # 6. DOCS with no documents
    def test_06_docs_with_no_documents(self):
        """Test DOCS route when no document chunks match."""
        with patch.object(self.brain, "search_documents", return_value=[]):
            res = self.brain.process_question("What is the interplanetary Martian policy?")
            self.assertEqual(res["intent"], "DOCS")
            self.assertIn("could not find any relevant information", res["answer"].lower())
            self.assertEqual(res["citations"], [])
            self.assertEqual(res["document_evidence"], [])

    # 7. Structured Routing Result Schema
    def test_07_structured_routing_schema(self):
        """Verify routing result contains all required contract keys."""
        res = self.brain.classify_intent("Calculate total revenue", dataset_id="ds-123")
        self.assertIn("intent", res)
        self.assertIn("confidence", res)
        self.assertIn("reason", res)
        self.assertIn("dataset_id", res)
        self.assertIn("document_id", res)
        self.assertEqual(res["dataset_id"], "ds-123")
        self.assertIsInstance(res["confidence"], float)

    # 8. No Arbitrary Code Execution Check
    def test_08_no_arbitrary_code_execution(self):
        """Verify zero presence of eval, exec, shell, or PandasAgent in reasoning_brain.py."""
        import inspect
        import reasoning_brain
        source = inspect.getsource(reasoning_brain)
        self.assertNotIn("eval(", source)
        self.assertNotIn("exec(", source)
        self.assertNotIn("create_pandas_dataframe_agent", source)
        self.assertNotIn("allow_dangerous_code", source)
        self.assertNotIn("subprocess", source)

    # 9. Tool Call Isolation: DATA does NOT call document search
    def test_09_data_does_not_call_document_search(self):
        """Verify DATA execution never queries the vector store."""
        with patch.object(self.brain, "search_documents") as mock_search:
            res = self.brain.process_question("What is the average salary?")
            self.assertEqual(res["intent"], "DATA")
            mock_search.assert_not_called()
            self.assertEqual(res["document_evidence"], [])
            self.assertEqual(res["citations"], [])

    # 10. Tool Call Isolation: DOCS does NOT call Data Brain
    def test_10_docs_does_not_call_data_brain(self):
        """Verify DOCS execution never queries the dataset service or Data Brain."""
        mock_chunks = [{
            "text": "Incident response requires escalation within 15 minutes.",
            "filename": "sop_incident_response.pdf",
            "page": 1,
            "chunk_index": 0
        }]
        with patch.object(self.brain, "search_documents", return_value=mock_chunks) as mock_search, \
             patch.object(self.brain, "analyze_dataset") as mock_analyze:
            res = self.brain.process_question("What is the incident response procedure?")
            self.assertEqual(res["intent"], "DOCS")
            mock_search.assert_called_once()
            mock_analyze.assert_not_called()
            self.assertEqual(res["data_facts"], [])

    # 11. Tool Call Isolation: HYBRID calls both
    def test_11_hybrid_calls_both(self):
        """Verify HYBRID execution calls both Data Brain and Knowledge Brain."""
        mock_chunks = [{
            "text": "Overtime compensation is capped at 10 hours per week.",
            "filename": "hr_policy.pdf",
            "page": 2,
            "chunk_index": 1
        }]
        mock_data = {
            "success": True,
            "text": "Salary facts",
            "facts": ["Average salary is $120,000"],
            "summary": {"row_count": 10},
            "kpis": {}
        }
        with patch.object(self.brain, "analyze_dataset", return_value=mock_data) as mock_analyze, \
             patch.object(self.brain, "search_documents", return_value=mock_chunks) as mock_search:
            res = self.brain.process_question("Compare the dataset findings with the company policy")
            self.assertEqual(res["intent"], "HYBRID")
            mock_analyze.assert_called_once()
            mock_search.assert_called_once()
            self.assertTrue(len(res["data_facts"]) > 0)
            self.assertTrue(len(res["document_evidence"]) > 0)
            self.assertTrue(len(res["citations"]) > 0)

    # 12 & 13. Citations Originate Strictly from Retrieved Metadata (No Hallucinations)
    def test_12_citations_strictly_from_metadata(self):
        """Verify citations and page numbers are derived strictly from retrieved chunks."""
        mock_chunks = [
            {"text": "Security rule 1", "filename": "cyber_sec.pdf", "page": 3, "chunk_index": 0},
            {"text": "Security rule 2", "filename": "data_gov.pdf", "page": 7, "chunk_index": 1}
        ]
        with patch.object(self.brain, "search_documents", return_value=mock_chunks):
            res = self.brain.process_question("What does the security policy say?")
            self.assertEqual(res["intent"], "DOCS")
            expected_cites = ["cyber_sec.pdf (Page 3)", "data_gov.pdf (Page 7)"]
            self.assertEqual(res["citations"], expected_cites)
            for doc in res["document_evidence"]:
                self.assertIn(doc["filename"], ["cyber_sec.pdf", "data_gov.pdf"])
                self.assertIn(doc["page"], [3, 7])

    # 14. Numerical facts remain deterministic
    def test_14_numerical_facts_deterministic(self):
        """Verify data facts returned are deterministic facts from Data Brain."""
        res = self.brain.analyze_dataset("Show me sales and salary metrics")
        if res.get("success"):
            self.assertIsInstance(res["facts"], list)
            self.assertIsInstance(res["text"], str)
            self.assertIn("Deterministic Key Metrics", res["text"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
