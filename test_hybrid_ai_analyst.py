"""
test_hybrid_ai_analyst.py
Comprehensive verification test suite for Step 7: Hybrid AI Analyst Backend.

Tests:
1. Hybrid intent classification
2. Hybrid planning selects both analyze_dataset and search_documents
3. Data-only question never calls document search
4. Docs-only question never calls dataset analysis
5. Response contract schema preservation
6. Answer separates the four required sections:
   - 📊 DATA FINDINGS
   - 📄 DOCUMENT EVIDENCE
   - ⚡ AI INTERPRETATION
   - 🔗 CITATIONS
7. Citations and page numbers derive strictly from retrieved metadata
8. Missing dataset context is handled safely without guessing
9. Missing document evidence is handled safely without guessing
10. Numbers in answer strictly match Data Brain facts (no invented numbers)
11. Causation safety rule enforced (no unsupported causal assertions)
12. Full hybrid question example:
    "How did revenue perform and what does the company policy say about incident reporting?"
13. Zero arbitrary code execution (no eval, exec, subprocess, PandasAgent)
"""

import os
import re
import unittest
from unittest.mock import patch, MagicMock

import pandas as pd

from reasoning_brain import ReasoningBrain
from dataset_service import save_uploaded_dataset, delete_dataset_by_id


class TestHybridAiAnalyst(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.brain = ReasoningBrain()
        
        # Create small test dataset for integration checks
        cls.test_csv_path = os.path.join(os.path.dirname(__file__), "test_hybrid_sales_demo.csv")
        df = pd.DataFrame({
            "Date": ["2026-01-15", "2026-01-20", "2026-02-10", "2026-02-18", "2026-03-05"],
            "Product": ["Phone", "Laptop", "Phone", "Headphones", "Phone"],
            "Category": ["Electronics", "Electronics", "Electronics", "Accessories", "Electronics"],
            "Revenue": [10000, 15000, 8000, 5000, 12000]
        })
        df.to_csv(cls.test_csv_path, index=False)
        
        with open(cls.test_csv_path, "rb") as f:
            profile = save_uploaded_dataset(f, "test_hybrid_sales_demo.csv")
            cls.test_dataset_id = profile["dataset"]["dataset_id"]

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, "test_dataset_id") and cls.test_dataset_id:
            try:
                delete_dataset_by_id(cls.test_dataset_id)
            except Exception:
                pass
        if os.path.exists(cls.test_csv_path):
            try:
                os.remove(cls.test_csv_path)
            except Exception:
                pass

    # -------------------------------------------------------------------------
    # Test 1: Hybrid Intent Detection
    # -------------------------------------------------------------------------
    def test_01_hybrid_intent_detection(self):
        """Verify hybrid questions combining metrics and policy/guidelines classify as HYBRID."""
        questions = [
            "How did revenue perform and what does the company policy say about incident reporting?",
            "Why did sales drop according to the policy?",
            "Compare the revenue findings with the employee handbook.",
            "What does the incident response SOP say about our sales decline?"
        ]
        for q in questions:
            res = self.brain.classify_intent(q)
            self.assertEqual(res["intent"], "HYBRID", f"Expected HYBRID for question: {q}")
            self.assertGreaterEqual(res["confidence"], 0.80)

    # -------------------------------------------------------------------------
    # Test 2: Hybrid Planning Selects Both Tools
    # -------------------------------------------------------------------------
    def test_02_hybrid_calls_both_tools(self):
        """Verify HYBRID planning selects both analyze_dataset and search_documents."""
        q = "How did revenue perform and what does the company policy say about incident reporting?"
        plan = self.brain.plan_tools("HYBRID", q, dataset_id=self.test_dataset_id)
        self.assertEqual(len(plan), 2)
        tool_names = [p["tool"] for p in plan]
        self.assertIn("analyze_dataset", tool_names)
        self.assertIn("search_documents", tool_names)

        # Check search_documents arguments
        search_plan = next(p for p in plan if p["tool"] == "search_documents")
        self.assertEqual(search_plan["arguments"]["top_k"], 5)
        self.assertEqual(search_plan["arguments"]["query"], q)

    # -------------------------------------------------------------------------
    # Test 3: Data-Only Question Does Not Call Document Search
    # -------------------------------------------------------------------------
    def test_03_data_only_no_docs(self):
        """Verify purely numerical/data queries never invoke search_documents."""
        with patch("reasoning_brain.execute_tool") as mock_exec:
            mock_exec.return_value = {
                "success": True,
                "facts": ["Total revenue: $50,000"],
                "text": "Total revenue: $50,000"
            }
            res = self.brain.process_question("Which product generated the most revenue?", dataset_id=self.test_dataset_id)
            self.assertEqual(res["intent"], "DATA")
            executed_tools = [c[0][0] for c in mock_exec.call_args_list]
            self.assertNotIn("search_documents", executed_tools)
            self.assertEqual(res["document_evidence"], [])
            self.assertEqual(res["citations"], [])

    # -------------------------------------------------------------------------
    # Test 4: Docs-Only Question Does Not Call Dataset Analysis
    # -------------------------------------------------------------------------
    def test_04_docs_only_no_data(self):
        """Verify document/policy queries never invoke data brain tools."""
        with patch("reasoning_brain.execute_tool") as mock_exec:
            mock_exec.return_value = {
                "success": True,
                "chunks": [{"filename": "it_security_policy.pdf", "page": 1, "text": "SSO required"}],
                "citations": ["it_security_policy.pdf (Page 1)"]
            }
            res = self.brain.process_question("What does the company policy say about passwords?", document_id="doc-1")
            self.assertEqual(res["intent"], "DOCS")
            executed_tools = [c[0][0] for c in mock_exec.call_args_list]
            self.assertNotIn("analyze_dataset", executed_tools)
            self.assertNotIn("get_kpis", executed_tools)
            self.assertNotIn("get_data_quality", executed_tools)
            self.assertEqual(res["data_facts"], [])

    # -------------------------------------------------------------------------
    # Test 5: Response Contract Schema Preservation
    # -------------------------------------------------------------------------
    def test_05_response_structure_contract(self):
        """Verify all contract keys are present in HYBRID response."""
        data_res = {
            "success": True,
            "facts": ["Phone generated 30,000", "Laptop generated 15,000"],
            "text": "Phone: 30,000\nLaptop: 15,000"
        }
        docs_res = {
            "success": True,
            "chunks": [
                {"filename": "sop_incident_response.pdf", "page": 2, "text": "Sev-1 incidents require immediate SRE paging."}
            ],
            "citations": ["sop_incident_response.pdf (Page 2)"]
        }

        res = self.brain.synthesize_hybrid(
            question="How did revenue perform and what does the policy say?",
            data_result=data_res,
            docs_result=docs_res,
            tool_calls=[{"tool": "analyze_dataset", "status": "success"}, {"tool": "search_documents", "status": "success"}]
        )

        required_keys = [
            "intent", "tool_calls", "answer", "data_facts", "document_evidence",
            "citations", "confidence", "warnings", "sources", "sources_text"
        ]
        for key in required_keys:
            self.assertIn(key, res, f"Missing required contract key: {key}")
        
        self.assertEqual(res["intent"], "HYBRID")
        self.assertIsInstance(res["tool_calls"], list)
        self.assertIsInstance(res["data_facts"], list)
        self.assertIsInstance(res["document_evidence"], list)
        self.assertIsInstance(res["citations"], list)
        self.assertIsInstance(res["warnings"], list)

    # -------------------------------------------------------------------------
    # Test 6: Answer Clearly Separates the Four Sections
    # -------------------------------------------------------------------------
    def test_06_answer_sections_separated(self):
        """Verify the final answer clearly separates the four required sections."""
        data_res = {
            "success": True,
            "facts": ["Revenue: $45,000"],
            "text": "Total revenue is $45,000."
        }
        docs_res = {
            "success": True,
            "chunks": [
                {"filename": "sop_incident_response.pdf", "page": 1, "text": "Incident triage protocol"}
            ],
            "citations": ["sop_incident_response.pdf (Page 1)"]
        }

        res = self.brain.synthesize_hybrid(
            question="How did revenue perform and what does the policy say about incidents?",
            data_result=data_res,
            docs_result=docs_res
        )
        answer = res["answer"]

        self.assertIn("📊 DATA FINDINGS", answer)
        self.assertIn("📄 DOCUMENT EVIDENCE", answer)
        self.assertIn("⚡ AI INTERPRETATION", answer)
        self.assertIn("🔗 CITATIONS", answer)

    # -------------------------------------------------------------------------
    # Test 7: Citations Strictly from Retrieved Metadata
    # -------------------------------------------------------------------------
    def test_07_citations_only_from_metadata(self):
        """Verify citations and page numbers derive strictly from retrieved metadata."""
        docs_res = {
            "success": True,
            "chunks": [
                {"filename": "it_security_policy.pdf", "page": 3, "text": "MFA requirements"}
            ]
        }
        res = self.brain.synthesize_hybrid(
            question="Test query",
            data_result={"success": True, "facts": ["Fact 1"], "text": "Fact 1"},
            docs_result=docs_res
        )
        self.assertEqual(res["citations"], ["it_security_policy.pdf (Page 3)"])
        self.assertIn("it_security_policy.pdf (Page 3)", res["sources_text"])
        self.assertIn("it_security_policy.pdf (Page 3)", res["answer"])

    # -------------------------------------------------------------------------
    # Test 8: Missing Dataset Context Handled Safely
    # -------------------------------------------------------------------------
    def test_08_missing_dataset_safe(self):
        """Verify missing dataset context returns a safe warning and does not invent numbers."""
        data_res = {"success": False, "error": "No dataset found."}
        docs_res = {
            "success": True,
            "chunks": [{"filename": "handbook.pdf", "page": 1, "text": "Company guidelines."}],
            "citations": ["handbook.pdf (Page 1)"]
        }
        res = self.brain.synthesize_hybrid(
            question="What are the sales numbers and handbook rules?",
            data_result=data_res,
            docs_result=docs_res
        )
        self.assertEqual(res["data_facts"], [])
        self.assertIn("No active structured dataset", res["answer"])
        self.assertTrue(any("dataset" in w.lower() for w in res["warnings"]))

    # -------------------------------------------------------------------------
    # Test 9: Missing Document Evidence Handled Safely
    # -------------------------------------------------------------------------
    def test_09_missing_document_evidence_safe(self):
        """Verify missing document evidence returns a safe notice and does not invent citations."""
        data_res = {"success": True, "facts": ["Revenue: $10,000"], "text": "Revenue: $10,000"}
        docs_res = {"success": True, "chunks": [], "citations": []}
        res = self.brain.synthesize_hybrid(
            question="Revenue and unknown policy?",
            data_result=data_res,
            docs_result=docs_res
        )
        self.assertEqual(res["document_evidence"], [])
        self.assertEqual(res["citations"], [])
        self.assertIn("No matching document evidence found", res["answer"])
        self.assertTrue(any("document" in w.lower() for w in res["warnings"]))

    # -------------------------------------------------------------------------
    # Test 10: Numbers in Answer Strictly Match Data Brain Facts
    # -------------------------------------------------------------------------
    def test_10_no_invented_numbers(self):
        """Verify numerical facts in answer strictly come from Data Brain without invention."""
        data_res = {
            "success": True,
            "facts": ["Phone: 28,000", "Laptop: 21,600", "Headphones: 8,250"],
            "text": "Phone: 28,000\nLaptop: 21,600\nHeadphones: 8,250"
        }
        docs_res = {
            "success": True,
            "chunks": [{"filename": "sop.pdf", "page": 1, "text": "Incident response protocol."}],
            "citations": ["sop.pdf (Page 1)"]
        }
        res = self.brain.synthesize_hybrid(
            question="Revenue performance and incident policy",
            data_result=data_res,
            docs_result=docs_res
        )
        data_section = res["answer"].split("### 📄 DOCUMENT EVIDENCE")[0]
        self.assertIn("28,000", data_section)
        self.assertIn("21,600", data_section)
        self.assertIn("8,250", data_section)
        # Verify no fabricated external numbers like 99,999
        self.assertNotIn("99,999", res["answer"])

    # -------------------------------------------------------------------------
    # Test 11: Causation Safety Rule Enforced
    # -------------------------------------------------------------------------
    def test_11_no_causation_assumption(self):
        """Verify the synthesis prompt and fallback prevent unwarranted causal claims."""
        data_res = {"success": True, "facts": ["Revenue dropped 10%"], "text": "Revenue dropped 10%"}
        docs_res = {
            "success": True,
            "chunks": [{"filename": "sop.pdf", "page": 1, "text": "Server maintenance window on Sunday."}],
            "citations": ["sop.pdf (Page 1)"]
        }
        res = self.brain.synthesize_hybrid(
            question="Why did revenue drop according to server maintenance policy?",
            data_result=data_res,
            docs_result=docs_res
        )
        # Interpretation must contain a cautionary statement about causation
        self.assertIn("No causal link", res["answer"])

    # -------------------------------------------------------------------------
    # Test 12: Full Hybrid Question Example
    # -------------------------------------------------------------------------
    def test_12_full_hybrid_question_example(self):
        """
        Full end-to-end question test:
        'How did revenue perform and what does the company policy say about incident reporting?'
        """
        question = "How did revenue perform and what does the company policy say about incident reporting?"
        
        # Mocking tool execution to inspect end-to-end integration through process_question
        def mock_tool_dispatcher(tool_name, args):
            if tool_name == "analyze_dataset":
                return {
                    "success": True,
                    "facts": ["Phone: 30,000", "Laptop: 15,000", "Headphones: 5,000"],
                    "text": "• Phone: 30,000\n• Laptop: 15,000\n• Headphones: 5,000\n\nTop product: Phone with revenue of 30,000."
                }
            elif tool_name == "search_documents":
                return {
                    "success": True,
                    "chunks": [
                        {
                            "filename": "sop_incident_response.pdf",
                            "page": 1,
                            "text": "Sev-1: Complete outage of a production service. All-hands response is mandatory."
                        }
                    ],
                    "citations": ["sop_incident_response.pdf (Page 1)"]
                }
            return {"success": False}

        with patch("reasoning_brain.execute_tool", side_effect=mock_tool_dispatcher):
            res = self.brain.process_question(question, dataset_id=self.test_dataset_id)
            
            self.assertEqual(res["intent"], "HYBRID")
            self.assertEqual(len(res["tool_calls"]), 2)
            self.assertIn("Phone: 30,000", res["data_facts"][0])
            self.assertEqual(res["document_evidence"][0]["filename"], "sop_incident_response.pdf")
            self.assertIn("sop_incident_response.pdf (Page 1)", res["citations"])
            
            # Answer sections
            self.assertIn("📊 DATA FINDINGS", res["answer"])
            self.assertIn("📄 DOCUMENT EVIDENCE", res["answer"])
            self.assertIn("⚡ AI INTERPRETATION", res["answer"])
            self.assertIn("🔗 CITATIONS", res["answer"])
            self.assertIn("30,000", res["answer"])
            self.assertIn("sop_incident_response.pdf (Page 1)", res["answer"])

    # -------------------------------------------------------------------------
    # Test 13: Zero Arbitrary Code Execution
    # -------------------------------------------------------------------------
    def test_13_no_arbitrary_code_execution(self):
        """Verify zero presence of eval, exec, subprocess, or PandasAgent in reasoning_brain.py."""
        target_path = os.path.join(os.path.dirname(__file__), "reasoning_brain.py")
        with open(target_path, "r", encoding="utf-8") as f:
            code = f.read()

        forbidden_patterns = [
            r"\beval\s*\(",
            r"\bexec\s*\(",
            r"\bsubprocess\b",
            r"\bcreate_pandas_dataframe_agent\b",
            r"\ballow_dangerous_code\s*=\s*True\b",
            r"\bos\.system\s*\("
        ]
        for pattern in forbidden_patterns:
            matches = re.findall(pattern, code)
            self.assertEqual(len(matches), 0, f"Forbidden execution pattern '{pattern}' detected in reasoning_brain.py!")


if __name__ == "__main__":
    unittest.main()
