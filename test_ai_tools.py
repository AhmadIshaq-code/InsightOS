"""
Unit tests for InsightOS Safe AI Tools (ai_tools.py).
Tests:
1. Every registered tool executes successfully with valid input.
2. Unknown tool is rejected.
3. Invalid arguments are rejected via Pydantic validation.
4. Missing dataset_id is rejected for DATA tools.
5. Missing document context is handled safely.
6. Zero eval/exec/shell/PandasAgent presence in code.
7. Top_k parameter validation and clamping.
"""

import inspect
import unittest
from unittest.mock import patch, MagicMock

import ai_tools
from ai_tools import (
    TOOL_REGISTRY,
    execute_tool,
    analyze_dataset_tool,
    get_kpis_tool,
    get_data_quality_tool,
    search_documents_tool,
    AnalyzeDatasetInput,
    GetKpisInput,
    GetDataQualityInput,
    SearchDocumentsInput
)


class TestAiTools(unittest.TestCase):

    def test_01_registry_completeness(self):
        """Verify all approved tools exist in TOOL_REGISTRY."""
        expected_tools = {"analyze_dataset", "get_kpis", "get_data_quality", "detect_anomalies", "forecast_metric", "search_documents"}
        self.assertEqual(set(TOOL_REGISTRY.keys()), expected_tools)
        for name, tool_def in TOOL_REGISTRY.items():
            self.assertEqual(tool_def.name, name)
            self.assertTrue(callable(tool_def.func))
            self.assertIsNotNone(tool_def.input_model)

    def test_02_unknown_tool_rejection(self):
        """Verify execution engine rejects unregistered tools."""
        res = execute_tool("arbitrary_python_tool", {"code": "print(1)"})
        self.assertFalse(res["success"])
        self.assertIn("not recognized", res["error"])

    def test_03_invalid_argument_rejection(self):
        """Verify malformed arguments are caught by Pydantic validation."""
        # search_documents with invalid top_k (exceeds le=50)
        res = execute_tool("search_documents", {"query": "test", "top_k": 999})
        self.assertFalse(res["success"])
        self.assertIn("Invalid arguments", res["error"])

        # get_kpis missing required dataset_id
        res2 = execute_tool("get_kpis", {})
        self.assertFalse(res2["success"])
        self.assertIn("Invalid arguments", res2["error"])

    def test_04_missing_dataset_id_rejected(self):
        """Verify DATA tools reject execution when dataset_id is missing or empty."""
        # analyze_dataset
        res_ad = analyze_dataset_tool("What is average salary?", dataset_id=None)
        self.assertFalse(res_ad["success"])
        self.assertIn("Missing dataset_id", res_ad["error"])

        # get_kpis
        res_kpi = get_kpis_tool(dataset_id="")
        self.assertFalse(res_kpi["success"])
        self.assertIn("Missing dataset_id", res_kpi["error"])

        # get_data_quality
        res_dq = get_data_quality_tool(dataset_id="")
        self.assertFalse(res_dq["success"])
        self.assertIn("Missing dataset_id", res_dq["error"])

        # detect_anomalies
        res_anom = execute_tool("detect_anomalies", {"dataset_id": "", "metric_column": "Sales"})
        self.assertFalse(res_anom["success"])

        # forecast_metric
        res_fc = execute_tool("forecast_metric", {"dataset_id": "", "metric_column": "Sales", "date_column": "Date"})
        self.assertFalse(res_fc["success"])

    def test_05_valid_execution_with_mocks(self):
        """Verify successful execution of all registered tools with valid inputs."""
        # 1. analyze_dataset
        mock_summary = {"row_count": 25, "column_count": 5, "quality_score": 95.0, "missing_cells": 0, "missing_percentage": 0.0}
        mock_kpis = {"kpis": {"Sales": {"total": 1000, "average": 40, "minimum": 10, "maximum": 100}}}
        mock_profile = {"dataset": {"original_filename": "sales.csv"}}

        with patch("ai_tools.get_dataset_summary", return_value=mock_summary), \
             patch("ai_tools.db_get_kpis", return_value=mock_kpis), \
             patch("ai_tools.get_dataset_profile_by_id", return_value=mock_profile):
            res = execute_tool("analyze_dataset", {"question": "What is the sales total?", "dataset_id": "ds-123"})
            self.assertTrue(res["success"])
            self.assertIn("facts", res)
            self.assertTrue(len(res["facts"]) > 0)

        # 2. get_kpis
        with patch("ai_tools.db_get_kpis", return_value=mock_kpis), \
             patch("ai_tools.get_dataset_profile_by_id", return_value=mock_profile):
            res_kpi = execute_tool("get_kpis", {"dataset_id": "ds-123"})
            self.assertTrue(res_kpi["success"])
            self.assertIn("kpis", res_kpi)

        # 3. get_data_quality
        mock_quality = {"quality": {"score": 92.0, "missing_cells": 2, "missing_percentage": 1.5, "duplicate_rows": 0, "duplicate_percentage": 0.0}, "summary": mock_summary, "dataset": {"original_filename": "data.csv"}}
        with patch("ai_tools.get_dataset_profile_by_id", return_value=mock_quality):
            res_dq = execute_tool("get_data_quality", {"dataset_id": "ds-123"})
            self.assertTrue(res_dq["success"])
            self.assertIn("quality", res_dq)

        # 4. search_documents
        mock_chunks = [{"filename": "policy.pdf", "page": 2, "text": "Security guidelines", "relevance_score": 0.88}]
        with patch("ai_tools.kb_search_documents", return_value=mock_chunks):
            res_doc = execute_tool("search_documents", {"query": "security guidelines", "top_k": 3})
            self.assertTrue(res_doc["success"])
            self.assertEqual(res_doc["count"], 1)
            self.assertEqual(res_doc["citations"], ["policy.pdf (Page 2)"])

        # 5. detect_anomalies
        mock_anomalies = {
            "column": "Sales", "method": "IQR", "q1": 100, "q3": 200, "iqr": 100,
            "lower_bound": -50, "upper_bound": 350, "anomaly_count": 1,
            "anomaly_percentage": 5.0, "normal_count": 19,
            "anomalies": [{"row_index": 0, "value": 500, "direction": "high"}]
        }
        with patch("ai_tools.db_detect_anomalies", return_value=mock_anomalies):
            res_anom = execute_tool("detect_anomalies", {"dataset_id": "ds-123", "metric_column": "Sales"})
            self.assertTrue(res_anom["success"])
            self.assertIn("anomalies", res_anom)

        # 6. forecast_metric
        mock_forecast = {
            "metric_column": "Sales", "date_column": "Date", "frequency": "monthly",
            "method": "linear_trend", "historical_count": 10, "forecast_periods": 3,
            "trend_slope": 25.0, "trend_direction": "up",
            "historical": [{"period": "2023-01", "value": 100}],
            "forecast": [{"period": "2023-11", "date": "2023-11", "predicted_value": 350.0}]
        }
        with patch("ai_tools.db_forecast_metric", return_value=mock_forecast):
            res_fc = execute_tool("forecast_metric", {"dataset_id": "ds-123", "metric_column": "Sales", "date_column": "Date", "periods": 3})
            self.assertTrue(res_fc["success"])
            self.assertIn("forecast", res_fc)

    def test_06_missing_document_context_safe(self):
        """Verify empty document search returns clean empty results without error."""
        with patch("ai_tools.kb_search_documents", return_value=[]):
            res = execute_tool("search_documents", {"query": "non-existent query", "top_k": 5})
            self.assertTrue(res["success"])
            self.assertEqual(res["chunks"], [])
            self.assertEqual(res["citations"], [])

    def test_07_no_arbitrary_code_execution(self):
        """Verify complete absence of eval, exec, subprocess, or PandasAgent in ai_tools."""
        src = inspect.getsource(ai_tools)
        self.assertNotIn("eval(", src)
        self.assertNotIn("exec(", src)
        self.assertNotIn("subprocess", src)
        self.assertNotIn("create_pandas_dataframe_agent", src)
        self.assertNotIn("allow_dangerous_code", src)


if __name__ == "__main__":
    unittest.main(verbosity=2)
