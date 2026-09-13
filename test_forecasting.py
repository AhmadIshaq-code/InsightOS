"""
Unit and integration tests for InsightOS Deterministic Forecasting (Step 9).
18 Required Deterministic Tests:
1. test_01_basic_linear_forecast: Known historical series with verified manual linear regression values.
2. test_02_upward_trend: Positive slope correctly identified (trend_direction="up").
3. test_03_downward_trend: Negative slope correctly identified (trend_direction="down").
4. test_04_flat_trend: Zero/near-zero slope correctly identified (trend_direction="flat").
5. test_05_future_dates_generation: Chronologically successive future period labels.
6. test_06_monthly_frequency: Aggregation and projection at monthly cadence (%Y-%m).
7. test_07_daily_frequency: Aggregation and projection at daily cadence (%Y-%m-%d).
8. test_08_weekly_frequency: Aggregation and projection at weekly cadence (%Y-W%V).
9. test_09_quarterly_frequency: Aggregation and projection at quarterly cadence (%Y-Q%q).
10. test_10_yearly_frequency: Aggregation and projection at yearly cadence (%Y).
11. test_11_invalid_metric_column: Missing or non-numeric metric raises appropriate error.
12. test_12_invalid_date_column: Missing or unparseable date column raises appropriate error.
13. test_13_insufficient_observations: Dataset with < 3 periods safely raises INSUFFICIENT_DATA.
14. test_14_invalid_periods: periods < 1 or periods > 24 raises INVALID_PERIODS.
15. test_15_nan_infinite_handling: Null and infinite values safely handled without crashing.
16. test_16_api_get_post: FastAPI TestClient verification for GET and POST /api/datasets/{dataset_id}/forecast.
17. test_17_ai_tool_validation_and_execution: execute_tool("forecast_metric", ...) validation and execution.
18. test_18_natural_language_routing_and_no_arbitrary_code: End-to-end forecast routing, regression check for normal trends, and zero arbitrary code execution.
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
from data_brain import forecast_metric, DataBrainError
from dataset_service import save_uploaded_dataset, delete_dataset_by_id
from ai_tools import execute_tool, TOOL_REGISTRY
from reasoning_brain import ReasoningBrain
from server import app


class TestForecasting(unittest.TestCase):

    def setUp(self):
        self.brain = ReasoningBrain()

    def test_01_basic_linear_forecast(self):
        """Verify exact manual linear trend regression on known deterministic data."""
        # Dates: Jan, Feb, Mar, Apr, May 2023
        # Metric: 100, 110, 120, 130, 140
        # x = [0, 1, 2, 3, 4], y = [100, 110, 120, 130, 140]
        # Slope = 10.0, Intercept = 100.0
        # Future 3 periods (Jun, Jul, Aug): x=5 -> 150.0, x=6 -> 160.0, x=7 -> 170.0
        df = pd.DataFrame({
            "Date": ["2023-01-15", "2023-02-15", "2023-03-15", "2023-04-15", "2023-05-15"],
            "Revenue": [100.0, 110.0, 120.0, 130.0, 140.0]
        })
        res = forecast_metric(df, "Revenue", "Date", periods=3, frequency="monthly")

        self.assertEqual(res["metric_column"], "Revenue")
        self.assertEqual(res["date_column"], "Date")
        self.assertEqual(res["frequency"], "month")
        self.assertEqual(res["method"], "linear_trend")
        self.assertEqual(res["historical_count"], 5)
        self.assertEqual(res["forecast_periods"], 3)
        self.assertEqual(res["trend_slope"], 10.0)
        self.assertEqual(res["trend_direction"], "up")
        self.assertEqual(len(res["historical"]), 5)
        self.assertEqual(len(res["forecast"]), 3)

        expected_forecast = [
            {"period": "2023-06", "predicted_value": 150.0},
            {"period": "2023-07", "predicted_value": 160.0},
            {"period": "2023-08", "predicted_value": 170.0}
        ]
        for actual, exp in zip(res["forecast"], expected_forecast):
            self.assertEqual(actual["period"], exp["period"])
            self.assertEqual(actual["predicted_value"], exp["predicted_value"])

    def test_02_upward_trend(self):
        """Verify positive slope correctly sets trend_direction='up'."""
        df = pd.DataFrame({
            "Date": ["2023-01-01", "2023-02-01", "2023-03-01", "2023-04-01"],
            "Sales": [10.0, 25.0, 40.0, 60.0]
        })
        res = forecast_metric(df, "Sales", "Date", periods=2, frequency="monthly")
        self.assertEqual(res["trend_direction"], "up")
        self.assertTrue(res["trend_slope"] > 0)
        self.assertTrue(res["forecast"][0]["predicted_value"] > 60.0)

    def test_03_downward_trend(self):
        """Verify negative slope correctly sets trend_direction='down'."""
        df = pd.DataFrame({
            "Date": ["2023-01-01", "2023-02-01", "2023-03-01", "2023-04-01"],
            "Sales": [100.0, 80.0, 60.0, 40.0]
        })
        res = forecast_metric(df, "Sales", "Date", periods=2, frequency="monthly")
        self.assertEqual(res["trend_direction"], "down")
        self.assertTrue(res["trend_slope"] < 0)
        self.assertTrue(res["forecast"][0]["predicted_value"] < 40.0)

    def test_04_flat_trend(self):
        """Verify zero/near-zero slope correctly sets trend_direction='flat'."""
        df = pd.DataFrame({
            "Date": ["2023-01-01", "2023-02-01", "2023-03-01", "2023-04-01"],
            "Sales": [50.0, 50.0, 50.0, 50.0]
        })
        res = forecast_metric(df, "Sales", "Date", periods=2, frequency="monthly")
        self.assertEqual(res["trend_direction"], "flat")
        self.assertEqual(res["trend_slope"], 0.0)
        self.assertEqual(res["forecast"][0]["predicted_value"], 50.0)

    def test_05_future_dates_generation(self):
        """Verify successive future period labels generate correctly across month boundaries."""
        df = pd.DataFrame({
            "Date": ["2023-10-01", "2023-11-01", "2023-12-01"],
            "Sales": [100.0, 110.0, 120.0]
        })
        res = forecast_metric(df, "Sales", "Date", periods=3, frequency="monthly")
        periods = [p["period"] for p in res["forecast"]]
        self.assertEqual(periods, ["2024-01", "2024-02", "2024-03"])

    def test_06_monthly_frequency(self):
        """Verify explicit monthly frequency aggregation."""
        df = pd.DataFrame({
            "Date": ["2023-01-05", "2023-01-20", "2023-02-10", "2023-03-15"],
            "Val": [50.0, 50.0, 120.0, 140.0]
        })
        res = forecast_metric(df, "Val", "Date", periods=2, frequency="monthly")
        self.assertEqual(res["frequency"], "month")
        self.assertEqual(res["historical_count"], 3)
        self.assertEqual(res["historical"][0]["period"], "2023-01")
        self.assertEqual(res["historical"][0]["value"], 100.0)

    def test_07_daily_frequency(self):
        """Verify daily frequency aggregation and day-by-day projection."""
        df = pd.DataFrame({
            "Date": ["2023-05-01", "2023-05-02", "2023-05-03", "2023-05-04"],
            "Val": [10.0, 20.0, 30.0, 40.0]
        })
        res = forecast_metric(df, "Val", "Date", periods=2, frequency="daily")
        self.assertEqual(res["frequency"], "day")
        self.assertEqual(res["forecast"][0]["period"], "2023-05-05")
        self.assertEqual(res["forecast"][1]["period"], "2023-05-06")

    def test_08_weekly_frequency(self):
        """Verify weekly frequency aggregation."""
        df = pd.DataFrame({
            "Date": ["2023-01-02", "2023-01-09", "2023-01-16", "2023-01-23"],
            "Val": [10.0, 20.0, 30.0, 40.0]
        })
        res = forecast_metric(df, "Val", "Date", periods=2, frequency="weekly")
        self.assertEqual(res["frequency"], "week")
        self.assertEqual(len(res["forecast"]), 2)
        self.assertIn("W", res["forecast"][0]["period"])

    def test_09_quarterly_frequency(self):
        """Verify quarterly frequency aggregation."""
        df = pd.DataFrame({
            "Date": ["2023-01-15", "2023-04-15", "2023-07-15", "2023-10-15"],
            "Val": [100.0, 110.0, 120.0, 130.0]
        })
        res = forecast_metric(df, "Val", "Date", periods=2, frequency="quarterly")
        self.assertEqual(res["frequency"], "quarter")
        self.assertEqual(res["forecast"][0]["period"], "2024-Q1")
        self.assertEqual(res["forecast"][1]["period"], "2024-Q2")

    def test_10_yearly_frequency(self):
        """Verify yearly frequency aggregation."""
        df = pd.DataFrame({
            "Date": ["2021-06-01", "2022-06-01", "2023-06-01"],
            "Val": [1000.0, 1200.0, 1400.0]
        })
        res = forecast_metric(df, "Val", "Date", periods=2, frequency="yearly")
        self.assertEqual(res["frequency"], "year")
        self.assertEqual(res["forecast"][0]["period"], "2024")
        self.assertEqual(res["forecast"][1]["period"], "2025")

    def test_11_invalid_metric_column(self):
        """Verify missing or non-numeric metric raises appropriate DataBrainError."""
        df = pd.DataFrame({
            "Date": ["2023-01-01", "2023-02-01", "2023-03-01"],
            "Category": ["A", "B", "C"]
        })
        # Missing column
        with self.assertRaises(DataBrainError) as ctx1:
            forecast_metric(df, "NonExistent", "Date")
        self.assertEqual(ctx1.exception.code, "INVALID_COLUMN")

        # Non-numeric column
        with self.assertRaises(DataBrainError) as ctx2:
            forecast_metric(df, "Category", "Date")
        self.assertEqual(ctx2.exception.code, "NON_NUMERIC_COLUMN")

    def test_12_invalid_date_column(self):
        """Verify missing or invalid datetime column raises appropriate DataBrainError."""
        df = pd.DataFrame({
            "Revenue": [100, 200, 300],
            "Text": ["one", "two", "three"]
        })
        # Missing date column
        with self.assertRaises(DataBrainError) as ctx1:
            forecast_metric(df, "Revenue", "MissingDate")
        self.assertEqual(ctx1.exception.code, "INVALID_COLUMN")

        # Non-datetime column
        with self.assertRaises(DataBrainError) as ctx2:
            forecast_metric(df, "Revenue", "Text")
        self.assertEqual(ctx2.exception.code, "INVALID_DATETIME_COLUMN")

    def test_13_insufficient_observations(self):
        """Verify fewer than 3 historical periods safely raises INSUFFICIENT_DATA."""
        df = pd.DataFrame({
            "Date": ["2023-01-01", "2023-02-01"],
            "Revenue": [100.0, 200.0]
        })
        with self.assertRaises(DataBrainError) as ctx:
            forecast_metric(df, "Revenue", "Date", periods=3, frequency="monthly")
        self.assertEqual(ctx.exception.code, "INSUFFICIENT_DATA")

    def test_14_invalid_periods(self):
        """Verify periods < 1 or periods > 24 raises INVALID_PERIODS."""
        df = pd.DataFrame({
            "Date": ["2023-01-01", "2023-02-01", "2023-03-01"],
            "Revenue": [100.0, 200.0, 300.0]
        })
        with self.assertRaises(DataBrainError) as ctx1:
            forecast_metric(df, "Revenue", "Date", periods=0)
        self.assertEqual(ctx1.exception.code, "INVALID_PERIODS")

        with self.assertRaises(DataBrainError) as ctx2:
            forecast_metric(df, "Revenue", "Date", periods=25)
        self.assertEqual(ctx2.exception.code, "INVALID_PERIODS")

    def test_15_nan_infinite_handling(self):
        """Verify NaNs, nulls, and infinite values are filtered without causing crashes."""
        df = pd.DataFrame({
            "Date": ["2023-01-01", "2023-02-01", None, "2023-03-01", "2023-04-01"],
            "Revenue": [100.0, np.nan, 300.0, np.inf, 400.0]
        })
        # Valid rows are (2023-01-01, 100) and (2023-04-01, 400) -> 2 rows -> insufficient data
        with self.assertRaises(DataBrainError) as ctx:
            forecast_metric(df, "Revenue", "Date", periods=2, frequency="monthly")
        self.assertEqual(ctx.exception.code, "INSUFFICIENT_DATA")

    def test_16_api_get_post(self):
        """Verify GET and POST /api/datasets/{dataset_id}/forecast via TestClient."""
        client = TestClient(app)

        csv_content = (
            "Date,Revenue\n"
            "2023-01-01,100\n"
            "2023-02-01,110\n"
            "2023-03-01,120\n"
            "2023-04-01,130\n"
            "2023-05-01,140\n"
        ).encode("utf-8")

        profile = save_uploaded_dataset(io.BytesIO(csv_content), "test_api_forecast.csv")
        ds_id = profile["dataset"]["dataset_id"]

        try:
            # 1. POST request
            post_res = client.post(
                f"/api/datasets/{ds_id}/forecast",
                json={
                    "metric_column": "Revenue",
                    "date_column": "Date",
                    "periods": 3,
                    "frequency": "monthly"
                }
            )
            self.assertEqual(post_res.status_code, 200)
            post_data = post_res.json()
            self.assertEqual(post_data["status"], "success")
            self.assertEqual(post_data["dataset_id"], ds_id)
            self.assertEqual(post_data["result"]["forecast_periods"], 3)
            self.assertEqual(len(post_data["result"]["forecast"]), 3)

            # 2. GET request
            get_res = client.get(
                f"/api/datasets/{ds_id}/forecast?metric_column=Revenue&date_column=Date&periods=2&frequency=monthly"
            )
            self.assertEqual(get_res.status_code, 200)
            get_data = get_res.json()
            self.assertEqual(get_data["status"], "success")
            self.assertEqual(get_data["result"]["forecast_periods"], 2)

            # 3. Invalid column returns error response with status 400
            err_res = client.post(
                f"/api/datasets/{ds_id}/forecast",
                json={"metric_column": "NonExistent", "date_column": "Date"}
            )
            self.assertEqual(err_res.status_code, 400)
            err_data = err_res.json()
            self.assertEqual(err_data["status"], "error")
            self.assertEqual(err_data["error"]["code"], "INVALID_COLUMN")
        finally:
            delete_dataset_by_id(ds_id)

    def test_17_ai_tool_validation_and_execution(self):
        """Verify forecast_metric tool in TOOL_REGISTRY validates arguments and executes safely."""
        self.assertIn("forecast_metric", TOOL_REGISTRY)

        csv_content = (
            "Date,Sales\n"
            "2023-01-01,500\n"
            "2023-02-01,550\n"
            "2023-03-01,600\n"
            "2023-04-01,650\n"
        ).encode("utf-8")
        profile = save_uploaded_dataset(io.BytesIO(csv_content), "test_tool_forecast.csv")
        ds_id = profile["dataset"]["dataset_id"]

        try:
            # Valid execution
            res = execute_tool("forecast_metric", {
                "dataset_id": ds_id,
                "metric_column": "Sales",
                "date_column": "Date",
                "periods": 3
            })
            self.assertTrue(res["success"])
            self.assertIn("facts", res)
            self.assertIn("text", res)
            self.assertEqual(len(res["forecast"]), 3)

            # Missing required date_column fails Pydantic validation
            res_missing_dt = execute_tool("forecast_metric", {
                "dataset_id": ds_id,
                "metric_column": "Sales"
            })
            self.assertFalse(res_missing_dt["success"])
            self.assertIn("Invalid arguments", res_missing_dt["error"])

            # Out of bounds periods fails Pydantic validation
            res_invalid_per = execute_tool("forecast_metric", {
                "dataset_id": ds_id,
                "metric_column": "Sales",
                "date_column": "Date",
                "periods": 999
            })
            self.assertFalse(res_invalid_per["success"])

            # Empty dataset_id rejected
            res_empty_ds = execute_tool("forecast_metric", {
                "dataset_id": "",
                "metric_column": "Sales",
                "date_column": "Date"
            })
            self.assertFalse(res_empty_ds["success"])
        finally:
            delete_dataset_by_id(ds_id)

    def test_18_natural_language_routing_and_no_arbitrary_code(self):
        """Verify natural language routing selects forecast_metric for forecast questions,
        while normal historical trend questions continue using analyze_dataset(trend),
        and verify zero arbitrary code execution in core modules."""
        csv_content = (
            "Date,Revenue\n"
            "2023-01-01,100\n"
            "2023-02-01,110\n"
            "2023-03-01,120\n"
            "2023-04-01,130\n"
        ).encode("utf-8")
        profile = save_uploaded_dataset(io.BytesIO(csv_content), "test_nl_forecast.csv")
        ds_id = profile["dataset"]["dataset_id"]

        try:
            # 1. Forecast query plans forecast_metric
            plan_fc = self.brain.plan_tools("DATA", "Forecast the next 3 months of revenue.", dataset_id=ds_id)
            self.assertEqual(len(plan_fc), 1)
            self.assertEqual(plan_fc[0]["tool"], "forecast_metric")
            self.assertEqual(plan_fc[0]["arguments"]["periods"], 3)
            self.assertEqual(plan_fc[0]["arguments"]["metric_column"], "Revenue")

            # 2. End-to-end question execution for forecast
            res_fc = self.brain.process_question("Forecast the next 3 months of revenue.", dataset_id=ds_id)
            self.assertEqual(res_fc["intent"], "DATA")
            self.assertIn("FORECAST", res_fc["answer"])
            self.assertTrue(len(res_fc["data_facts"]) > 0)

            # 3. Regression test: Normal trend question MUST NOT route to forecast_metric
            plan_trend = self.brain.plan_tools("DATA", "Show me the revenue trend over time.", dataset_id=ds_id)
            self.assertEqual(len(plan_trend), 1)
            self.assertEqual(plan_trend[0]["tool"], "analyze_dataset")
            self.assertNotEqual(plan_trend[0]["tool"], "forecast_metric")
            self.assertEqual(plan_trend[0]["arguments"].get("operation"), "trend")
        finally:
            delete_dataset_by_id(ds_id)

        # 4. Security check: zero arbitrary code execution
        for module in [data_brain, ai_tools, reasoning_brain]:
            src = inspect.getsource(module)
            self.assertNotIn("eval(", src)
            self.assertNotIn("exec(", src)
            self.assertNotIn("subprocess", src)
            self.assertNotIn("create_pandas_dataframe_agent", src)
            self.assertNotIn("allow_dangerous_code", src)


if __name__ == "__main__":
    unittest.main(verbosity=2)
