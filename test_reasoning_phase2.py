"""
Unit and integration tests for InsightOS Reasoning Brain Phase 2: Safe AI Tool Orchestration.
Tests:
1. Tool plan generation for DATA (minimal tool execution)
2. Tool plan generation for DOCS
3. Tool plan generation for HYBRID
4. Tool plan generation for GENERAL
5. DATA question cannot invoke document tool
6. DOCS question cannot invoke Data Brain
7. HYBRID question invokes both
8. GENERAL question invokes neither
9. Missing dataset_id is rejected for DATA tools
10. Missing document context is handled safely
11. Tool calls structure is deterministic and valid in response
12. Backward-compatible answer/sources/sources_text remain present
13. Numerical facts originate from Data Brain output
14. Citations originate only from Knowledge Brain metadata
15. Insufficient evidence produces safe response
"""

import unittest
from unittest.mock import patch, MagicMock
from reasoning_brain import ReasoningBrain


class TestReasoningPhase2(unittest.TestCase):

    def setUp(self):
        self.brain = ReasoningBrain()

    def test_01_plan_minimal_data_tools(self):
        """Verify DATA planning selects only the specific tool needed."""
        # 1. KPI query -> get_kpis
        plan_kpi = self.brain.plan_tools("DATA", "Show me the KPIs", dataset_id="ds-1")
        self.assertEqual(len(plan_kpi), 1)
        self.assertEqual(plan_kpi[0]["tool"], "get_kpis")

        # 2. Quality query -> get_data_quality
        plan_dq = self.brain.plan_tools("DATA", "What is the data quality health score?", dataset_id="ds-1")
        self.assertEqual(len(plan_dq), 1)
        self.assertEqual(plan_dq[0]["tool"], "get_data_quality")

        # 3. General analytics query -> analyze_dataset
        plan_ad = self.brain.plan_tools("DATA", "What is the average salary?", dataset_id="ds-1")
        self.assertEqual(len(plan_ad), 1)
        self.assertEqual(plan_ad[0]["tool"], "analyze_dataset")

    def test_02_plan_docs_tool(self):
        """Verify DOCS planning selects only search_documents."""
        plan = self.brain.plan_tools("DOCS", "What is the security policy?", document_id="doc-1")
        self.assertEqual(len(plan), 1)
        self.assertEqual(plan[0]["tool"], "search_documents")
        self.assertEqual(plan[0]["arguments"]["document_id"], "doc-1")

    def test_03_plan_hybrid_tools(self):
        """Verify HYBRID planning selects both data and document tools."""
        plan = self.brain.plan_tools("HYBRID", "Why did revenue drop according to the policy?", dataset_id="ds-1", document_id="doc-1")
        self.assertEqual(len(plan), 2)
        tool_names = [p["tool"] for p in plan]
        self.assertIn("analyze_dataset", tool_names)
        self.assertIn("search_documents", tool_names)

    def test_04_plan_general_no_tools(self):
        """Verify GENERAL planning selects 0 tools."""
        plan = self.brain.plan_tools("GENERAL", "Hello!")
        self.assertEqual(plan, [])

    def test_05_data_cannot_invoke_docs(self):
        """Verify DATA query execution never invokes search_documents."""
        with patch("reasoning_brain.execute_tool") as mock_exec:
            mock_exec.return_value = {"success": True, "facts": ["Fact 1"], "text": "Data Text"}
            res = self.brain.process_question("What is the total sales?", dataset_id="ds-1")
            self.assertEqual(res["intent"], "DATA")
            # Verify search_documents was never executed
            called_tools = [call[0][0] for call in mock_exec.call_args_list]
            self.assertNotIn("search_documents", called_tools)
            self.assertEqual(res["document_evidence"], [])
            self.assertEqual(res["citations"], [])

    def test_06_docs_cannot_invoke_data(self):
        """Verify DOCS query execution never invokes data tools."""
        with patch("reasoning_brain.execute_tool") as mock_exec:
            mock_exec.return_value = {"success": True, "chunks": [{"filename": "p.pdf", "page": 1, "text": "txt"}], "citations": ["p.pdf (Page 1)"]}
            res = self.brain.process_question("What does the employee handbook say?", document_id="doc-1")
            self.assertEqual(res["intent"], "DOCS")
            called_tools = [call[0][0] for call in mock_exec.call_args_list]
            self.assertNotIn("analyze_dataset", called_tools)
            self.assertNotIn("get_kpis", called_tools)
            self.assertNotIn("get_data_quality", called_tools)
            self.assertEqual(res["data_facts"], [])

    def test_07_hybrid_invokes_both(self):
        """Verify HYBRID query execution invokes both data and document tools."""
        def mock_tool_impl(name, args):
            if name == "analyze_dataset":
                return {"success": True, "facts": ["Revenue dropped 10%"], "text": "Sales Text"}
            if name == "search_documents":
                return {"success": True, "chunks": [{"filename": "sop.pdf", "page": 2, "text": "SOP text"}], "citations": ["sop.pdf (Page 2)"]}
            return {"success": False}

        with patch("reasoning_brain.execute_tool", side_effect=mock_tool_impl):
            res = self.brain.process_question("Why did sales decrease according to the policy?", dataset_id="ds-1")
            self.assertEqual(res["intent"], "HYBRID")
            self.assertEqual(len(res["tool_calls"]), 2)
            tool_names = [tc["tool"] for tc in res["tool_calls"]]
            self.assertIn("analyze_dataset", tool_names)
            self.assertIn("search_documents", tool_names)
            self.assertTrue(len(res["data_facts"]) > 0)
            self.assertTrue(len(res["document_evidence"]) > 0)
            self.assertTrue(len(res["citations"]) > 0)

    def test_08_general_invokes_neither(self):
        """Verify GENERAL query execution invokes no tools."""
        with patch("reasoning_brain.execute_tool") as mock_exec:
            res = self.brain.process_question("Hello, what can you do?")
            self.assertEqual(res["intent"], "GENERAL")
            mock_exec.assert_not_called()
            self.assertEqual(res["tool_calls"], [])

    def test_09_missing_dataset_id_handling(self):
        """Verify missing dataset_id results in a safe clarification/warning state."""
        with patch.object(self.brain, "resolve_dataset_id", return_value=None):
            res = self.brain.process_question("What is the average salary?")
            self.assertEqual(res["intent"], "DATA")
            self.assertIn("No active structured dataset", res["answer"])
            self.assertTrue(len(res["warnings"]) > 0)

    def test_10_missing_document_context_safe(self):
        """Verify missing document evidence returns a safe no-information response."""
        def mock_tool_impl(name, args):
            if name == "search_documents":
                return {"success": True, "chunks": [], "citations": []}
            return {"success": False}

        with patch("reasoning_brain.execute_tool", side_effect=mock_tool_impl):
            res = self.brain.process_question("What is the Martian diplomacy handbook?")
            self.assertEqual(res["intent"], "DOCS")
            self.assertIn("could not find any relevant information", res["answer"].lower())
            self.assertEqual(res["citations"], [])

    @classmethod
    def setUpClass(cls):
        import io
        from dataset_service import save_uploaded_dataset
        csv_bytes = (
            "Date,Product,Category,Units,Revenue\n"
            "2026-01-05,Laptop,Electronics,10,12000\n"
            "2026-01-12,Phone,Electronics,20,16000\n"
            "2026-02-03,Laptop,Electronics,8,9600\n"
            "2026-02-15,Headphones,Accessories,30,4500\n"
            "2026-03-04,Phone,Electronics,15,12000\n"
            "2026-03-20,Headphones,Accessories,25,3750\n"
        ).encode("utf-8")
        profile = save_uploaded_dataset(io.BytesIO(csv_bytes), "test_sales_demo.csv")
        cls.demo_dataset_id = profile["dataset"]["dataset_id"]

    @classmethod
    def tearDownClass(cls):
        from dataset_service import delete_dataset_by_id
        if hasattr(cls, "demo_dataset_id") and cls.demo_dataset_id:
            try:
                delete_dataset_by_id(cls.demo_dataset_id)
            except Exception:
                pass

    def test_11_backward_compatibility_fields(self):
        """Verify all required response fields are present across intents."""
        res_gen = self.brain.process_question("Hi!")
        for key in ["intent", "tool_calls", "answer", "data_facts", "document_evidence", "citations", "confidence", "warnings", "sources", "sources_text"]:
            self.assertIn(key, res_gen)

    def test_12_product_most_revenue(self):
        """1. 'Which product generated the most revenue?'"""
        res = self.brain.process_question("Which product generated the most revenue?", dataset_id=self.demo_dataset_id)
        self.assertEqual(res["intent"], "DATA")
        self.assertIn("Phone", res["answer"])
        self.assertIn("28,000", res["answer"])
        self.assertIn("Laptop", res["answer"])
        self.assertIn("21,600", res["answer"])
        self.assertIn("Headphones", res["answer"])
        self.assertIn("8,250", res["answer"])
        self.assertEqual(res["tool_calls"][0]["tool"], "analyze_dataset")

    def test_13_category_highest_revenue(self):
        """2. 'Which category has the highest revenue?'"""
        res = self.brain.process_question("Which category has the highest revenue?", dataset_id=self.demo_dataset_id)
        self.assertEqual(res["intent"], "DATA")
        self.assertIn("Electronics", res["answer"])
        self.assertIn("49,600", res["answer"])
        self.assertIn("Accessories", res["answer"])

    def test_14_show_revenue_by_product(self):
        """3. 'Show revenue by product.'"""
        res = self.brain.process_question("Show revenue by product.", dataset_id=self.demo_dataset_id)
        self.assertEqual(res["intent"], "DATA")
        self.assertIn("Revenue by Product", res["answer"])
        self.assertIn("Phone", res["answer"])
        self.assertIn("Laptop", res["answer"])

    def test_15_revenue_trend_over_time(self):
        """4. 'Show me the revenue trend over time.'"""
        res = self.brain.process_question("Show me the revenue trend over time.", dataset_id=self.demo_dataset_id)
        self.assertEqual(res["intent"], "DATA")
        self.assertIn("28,000", res["answer"])
        self.assertIn("14,100", res["answer"])
        self.assertIn("15,750", res["answer"])
        self.assertEqual(res["tool_calls"][0]["tool"], "analyze_dataset")

    def test_16_show_monthly_revenue(self):
        """5. 'Show monthly revenue.'"""
        res = self.brain.process_question("Show monthly revenue.", dataset_id=self.demo_dataset_id)
        self.assertEqual(res["intent"], "DATA")
        self.assertIn("28,000", res["answer"])
        self.assertIn("14,100", res["answer"])
        self.assertIn("15,750", res["answer"])

    def test_17_ambiguous_question_no_guessing(self):
        """6. Ambiguous question should NOT guess a column."""
        res = self.brain.process_question("Which one generated the most?", dataset_id=self.demo_dataset_id)
        self.assertEqual(res["intent"], "DATA")
        self.assertIn("Ambiguous Query", res["answer"])
        self.assertIn("Product", res["answer"])
        self.assertIn("Category", res["answer"])

    def test_18_generic_kpi_questions_continue_working(self):
        """8. Existing generic KPI questions must continue working."""
        res = self.brain.process_question("Show me the KPIs", dataset_id=self.demo_dataset_id)
        self.assertEqual(res["intent"], "DATA")
        self.assertEqual(res["tool_calls"][0]["tool"], "get_kpis")
        self.assertIn("Key Performance Indicators", res["answer"])

    def test_19_no_arbitrary_code_execution(self):
        """10. Verify zero eval/exec/arbitrary code in reasoning_brain and ai_tools."""
        import inspect
        import ai_tools
        import reasoning_brain
        for mod in [ai_tools, reasoning_brain]:
            src = inspect.getsource(mod)
            self.assertNotIn("eval(", src)
            self.assertNotIn("exec(", src)
            self.assertNotIn("subprocess", src)
            self.assertNotIn("create_pandas_dataframe_agent", src)
            self.assertNotIn("allow_dangerous_code", src)


if __name__ == "__main__":
    unittest.main(verbosity=2)
