"""
Unit and integration tests for InsightOS Deterministic Anomaly Detection (Step 8).
15 Required Deterministic Tests:
1. test_01_basic_iqr_calculation: Verified manual IQR calculations on known array.
2. test_02_high_outlier: Flagging values above upper bound (direction="high").
3. test_03_low_outlier: Flagging values below lower bound (direction="low").
4. test_04_no_anomalies: Uniform/normal data returns 0 anomalies.
5. test_05_constant_column: Identical values produce 0 anomalies without error.
6. test_06_missing_column: Non-existent column raises DataBrainError("INVALID_COLUMN").
7. test_07_non_numeric_column: Categorical column raises DataBrainError("NON_NUMERIC_COLUMN").
8. test_08_nan_values: Dataset with nulls handles calculation safely without error.
9. test_09_datetime_metadata: Inclusion of date column in anomaly objects.
10. test_10_category_metadata: Inclusion of category column in anomaly objects.
11. test_11_limit_handling: Enforcement of limit and validation of invalid limits.
12. test_12_api_endpoint: Verification of GET and POST /api/datasets/{dataset_id}/anomalies.
13. test_13_ai_tool_validation: Pydantic validation and execution of detect_anomalies tool.
14. test_14_natural_language_routing: Full pipeline routing for "Which months had unusual revenue?".
15. test_15_no_arbitrary_code_execution: Security check verifying zero presence of eval, exec, subprocess, PandasAgent.
"""

import io
import inspect
import unittest
import numpy as np
import pandas as pd
from fastapi.testclient import TestClient

import data_brain
import ai_tools
import reasoning_brain
from data_brain import detect_anomalies, DataBrainError
from dataset_service import save_uploaded_dataset, delete_dataset_by_id
from ai_tools import execute_tool, TOOL_REGISTRY
from reasoning_brain import ReasoningBrain
from server import app


class TestAnomalyDetection(unittest.TestCase):

    def setUp(self):
        self.brain = ReasoningBrain()

    def test_01_basic_iqr_calculation(self):
        """Verify exact manual IQR percentiles and bounds on a known deterministic array."""
        # Array: 10, 20, 30, 40, 50, 60, 70, 80
        # Q1 (25th): 27.5, Q3 (75th): 62.5, IQR: 35.0
        # Lower: 27.5 - 1.5 * 35.0 = -25.0, Upper: 62.5 + 1.5 * 35.0 = 115.0
        df = pd.DataFrame({"metric": [10, 20, 30, 40, 50, 60, 70, 80]})
        res = detect_anomalies(df, "metric")

        self.assertEqual(res["column"], "metric")
        self.assertEqual(res["method"], "IQR")
        self.assertEqual(res["q1"], 27.5)
        self.assertEqual(res["q3"], 62.5)
        self.assertEqual(res["iqr"], 35.0)
        self.assertEqual(res["lower_bound"], -25.0)
        self.assertEqual(res["upper_bound"], 115.0)
        self.assertEqual(res["anomaly_count"], 0)
        self.assertEqual(res["normal_count"], 8)
        self.assertEqual(res["anomaly_percentage"], 0.0)
        self.assertEqual(res["anomalies"], [])

    def test_02_high_outlier(self):
        """Verify values strictly above upper bound are flagged with direction='high'."""
        # 500 is far above upper bound
        df = pd.DataFrame({"metric": [10, 12, 14, 15, 16, 18, 20, 22, 500]})
        res = detect_anomalies(df, "metric")

        self.assertEqual(res["anomaly_count"], 1)
        self.assertEqual(len(res["anomalies"]), 1)
        anom = res["anomalies"][0]
        self.assertEqual(anom["value"], 500)
        self.assertEqual(anom["direction"], "high")
        self.assertTrue(anom["value"] > res["upper_bound"])

    def test_03_low_outlier(self):
        """Verify values strictly below lower bound are flagged with direction='low'."""
        # -500 is far below lower bound
        df = pd.DataFrame({"metric": [-500, 10, 12, 14, 15, 16, 18, 20, 22]})
        res = detect_anomalies(df, "metric")

        self.assertEqual(res["anomaly_count"], 1)
        self.assertEqual(len(res["anomalies"]), 1)
        anom = res["anomalies"][0]
        self.assertEqual(anom["value"], -500)
        self.assertEqual(anom["direction"], "low")
        self.assertTrue(anom["value"] < res["lower_bound"])

    def test_04_no_anomalies(self):
        """Verify evenly distributed/normal data returns zero anomalies."""
        df = pd.DataFrame({"metric": [10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20]})
        res = detect_anomalies(df, "metric")

        self.assertEqual(res["anomaly_count"], 0)
        self.assertEqual(res["anomalies"], [])
        self.assertEqual(res["normal_count"], 11)
        self.assertEqual(res["anomaly_percentage"], 0.0)

    def test_05_constant_column(self):
        """Verify constant columns produce IQR=0 and zero anomalies without division-by-zero or errors."""
        df = pd.DataFrame({"metric": [42.0, 42.0, 42.0, 42.0, 42.0, 42.0]})
        res = detect_anomalies(df, "metric")

        self.assertEqual(res["anomaly_count"], 0)
        self.assertEqual(res["anomalies"], [])
        self.assertEqual(res["iqr"], 0.0)
        self.assertEqual(res["normal_count"], 6)

    def test_06_missing_column(self):
        """Verify non-existent column raises DataBrainError with code INVALID_COLUMN."""
        df = pd.DataFrame({"metric": [10, 20, 30, 40]})
        with self.assertRaises(DataBrainError) as ctx:
            detect_anomalies(df, "non_existent_column")
        self.assertEqual(ctx.exception.code, "INVALID_COLUMN")

    def test_07_non_numeric_column(self):
        """Verify non-numeric column raises DataBrainError with code NON_NUMERIC_COLUMN."""
        df = pd.DataFrame({"category": ["North", "South", "East", "West", "Central"]})
        with self.assertRaises(DataBrainError) as ctx:
            detect_anomalies(df, "category")
        self.assertEqual(ctx.exception.code, "NON_NUMERIC_COLUMN")

    def test_08_nan_values(self):
        """Verify NaN, None, and infinite values are cleanly filtered before calculation."""
        df = pd.DataFrame({"metric": [10.0, np.nan, 20.0, np.inf, 30.0, 40.0, -np.inf, 50.0, 60.0, 70.0, 80.0]})
        res = detect_anomalies(df, "metric")

        self.assertEqual(res["normal_count"], 8)
        self.assertEqual(res["anomaly_count"], 0)

        # Also verify fewer than 4 valid observations handles gracefully
        df_few = pd.DataFrame({"metric": [10.0, np.nan, 20.0, np.nan]})
        res_few = detect_anomalies(df_few, "metric")
        self.assertEqual(res_few["anomaly_count"], 0)
        self.assertEqual(res_few["normal_count"], 2)

    def test_09_datetime_metadata(self):
        """Verify date values are correctly attached to flagged anomaly records."""
        df = pd.DataFrame({
            "Date": ["2023-01-01", "2023-02-01", "2023-03-01", "2023-04-01", "2023-05-01", "2023-06-01"],
            "Revenue": [100, 110, 105, 115, 9999, 120]
        })
        res = detect_anomalies(df, "Revenue", date_column="Date")

        self.assertEqual(res["anomaly_count"], 1)
        anom = res["anomalies"][0]
        self.assertEqual(anom["value"], 9999)
        self.assertEqual(anom["date"], "2023-05-01")

    def test_10_category_metadata(self):
        """Verify category/dimension values are correctly attached to flagged anomaly records."""
        df = pd.DataFrame({
            "Product": ["Widget A", "Widget B", "Widget C", "Widget D", "Widget Spike"],
            "Sales": [50, 52, 48, 55, 1200]
        })
        res = detect_anomalies(df, "Sales", dimension_column="Product")

        self.assertEqual(res["anomaly_count"], 1)
        anom = res["anomalies"][0]
        self.assertEqual(anom["value"], 1200)
        self.assertEqual(anom["category"], "Widget Spike")
        self.assertEqual(anom["dimension"], "Widget Spike")

    def test_11_limit_handling(self):
        """Verify limit clamps returned anomalies and validates limit parameter bounds."""
        # 40 normal points + 5 high outliers
        normal_points = [10, 11, 12, 11, 10] * 8
        outliers = [5000, 5100, 5200, 5300, 5400]
        df = pd.DataFrame({"val": normal_points + outliers})

        res = detect_anomalies(df, "val", limit=2)
        self.assertEqual(res["anomaly_count"], 5)
        self.assertEqual(len(res["anomalies"]), 2)

        # Invalid limits: limit < 1 or limit > 1000 raises DataBrainError
        with self.assertRaises(DataBrainError) as ctx1:
            detect_anomalies(df, "val", limit=0)
        self.assertEqual(ctx1.exception.code, "INVALID_LIMIT")

        with self.assertRaises(DataBrainError) as ctx2:
            detect_anomalies(df, "val", limit=1001)
        self.assertEqual(ctx2.exception.code, "INVALID_LIMIT")

    def test_12_api_endpoint(self):
        """Verify GET and POST /api/datasets/{dataset_id}/anomalies endpoint."""
        client = TestClient(app)

        csv_content = (
            "Date,Product,Revenue\n"
            "2023-01-01,Alpha,100\n"
            "2023-02-01,Beta,105\n"
            "2023-03-01,Alpha,110\n"
            "2023-04-01,Beta,115\n"
            "2023-05-01,Alpha,9500\n"
            "2023-06-01,Beta,120\n"
        ).encode("utf-8")

        profile = save_uploaded_dataset(io.BytesIO(csv_content), "test_api_anomalies.csv")
        ds_id = profile["dataset"]["dataset_id"]

        try:
            # 1. POST request
            post_res = client.post(
                f"/api/datasets/{ds_id}/anomalies",
                json={
                    "metric_column": "Revenue",
                    "date_column": "Date",
                    "dimension_column": "Product",
                    "limit": 10
                }
            )
            self.assertEqual(post_res.status_code, 200)
            post_data = post_res.json()
            self.assertEqual(post_data["status"], "success")
            self.assertEqual(post_data["dataset_id"], ds_id)
            self.assertEqual(post_data["result"]["anomaly_count"], 1)
            self.assertEqual(post_data["result"]["anomalies"][0]["date"], "2023-05-01")

            # 2. GET request
            get_res = client.get(
                f"/api/datasets/{ds_id}/anomalies?metric_column=Revenue&date_column=Date&limit=5"
            )
            self.assertEqual(get_res.status_code, 200)
            get_data = get_res.json()
            self.assertEqual(get_data["status"], "success")
            self.assertEqual(get_data["result"]["anomaly_count"], 1)

            # 3. Invalid column returns error response
            err_res = client.post(
                f"/api/datasets/{ds_id}/anomalies",
                json={"metric_column": "NonExistentColumn"}
            )
            self.assertEqual(err_res.status_code, 400)
            err_data = err_res.json()
            self.assertEqual(err_data["status"], "error")
            self.assertEqual(err_data["error"]["code"], "INVALID_COLUMN")
        finally:
            delete_dataset_by_id(ds_id)

    def test_13_ai_tool_validation(self):
        """Verify detect_anomalies tool in TOOL_REGISTRY validates arguments and executes safely."""
        self.assertIn("detect_anomalies", TOOL_REGISTRY)

        csv_content = (
            "Month,Sales\n"
            "Jan,50\n"
            "Feb,55\n"
            "Mar,52\n"
            "Apr,48\n"
            "May,51\n"
            "Jun,5000\n"
        ).encode("utf-8")
        profile = save_uploaded_dataset(io.BytesIO(csv_content), "test_tool_anomalies.csv")
        ds_id = profile["dataset"]["dataset_id"]

        try:
            # Valid execution
            res = execute_tool("detect_anomalies", {
                "dataset_id": ds_id,
                "metric_column": "Sales",
                "dimension_column": "Month"
            })
            self.assertTrue(res["success"])
            self.assertIn("facts", res)
            self.assertIn("text", res)
            self.assertEqual(res["anomaly_count"], 1)
            self.assertEqual(len(res["anomalies"]), 1)

            # Missing required metric_column fails Pydantic validation
            res_missing_col = execute_tool("detect_anomalies", {"dataset_id": ds_id})
            self.assertFalse(res_missing_col["success"])
            self.assertIn("Invalid arguments", res_missing_col["error"])

            # Empty dataset_id rejected
            res_empty_ds = execute_tool("detect_anomalies", {"dataset_id": "", "metric_column": "Sales"})
            self.assertFalse(res_empty_ds["success"])
        finally:
            delete_dataset_by_id(ds_id)

    def test_14_natural_language_routing(self):
        """Verify natural language routing for questions asking for unusual values/anomalies/outliers."""
        csv_content = (
            "Date,Revenue\n"
            "2023-01-01,100\n"
            "2023-02-01,110\n"
            "2023-03-01,105\n"
            "2023-04-01,115\n"
            "2023-05-01,9500\n"
            "2023-06-01,120\n"
        ).encode("utf-8")
        profile = save_uploaded_dataset(io.BytesIO(csv_content), "test_nl_anomalies.csv")
        ds_id = profile["dataset"]["dataset_id"]

        try:
            # Plan test
            plan = self.brain.plan_tools("DATA", "Which months had unusual revenue?", dataset_id=ds_id)
            self.assertEqual(len(plan), 1)
            self.assertEqual(plan[0]["tool"], "detect_anomalies")
            self.assertEqual(plan[0]["arguments"]["metric_column"], "Revenue")

            # End-to-end question processing
            res = self.brain.process_question("Which months had unusual revenue?", dataset_id=ds_id)
            self.assertEqual(res["intent"], "DATA")
            self.assertIn("Statistical Anomaly Detection", res["answer"])
            self.assertIn("DATA FINDINGS", res["answer"])
            self.assertTrue(len(res["data_facts"]) > 0)
        finally:
            delete_dataset_by_id(ds_id)

    def test_15_no_arbitrary_code_execution(self):
        """Verify zero presence of eval, exec, subprocess, or PandasAgent in core codebase."""
        for module in [data_brain, ai_tools, reasoning_brain]:
            src = inspect.getsource(module)
            self.assertNotIn("eval(", src)
            self.assertNotIn("exec(", src)
            self.assertNotIn("subprocess", src)
            self.assertNotIn("create_pandas_dataframe_agent", src)
            self.assertNotIn("allow_dangerous_code", src)


if __name__ == "__main__":
    unittest.main(verbosity=2)
