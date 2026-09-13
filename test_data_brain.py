import io
import os
import shutil
import pandas as pd
import numpy as np

from dataset_service import save_uploaded_dataset, delete_dataset_by_id
from data_brain import (
    DataBrainError,
    require_dataset,
    require_column,
    require_numeric_column,
    require_datetime_column,
    is_likely_identifier_column,
    get_dataset_summary,
    get_numeric_statistics,
    aggregate_by_category,
    get_top_categories,
    get_bottom_categories,
    get_time_trend,
    get_kpis
)

def test_data_brain_complete_suite():
    print("==================================================")
    print("Running InsightOS Data Brain Deterministic Tests")
    print("==================================================")

    # -------------------------------------------------------------
    # 1. SALES DATASET FIXTURE (Deterministic facts)
    # -------------------------------------------------------------
    print("\n[Test 1] Testing Sales Dataset with Deterministic Assertions...")
    sales_data = {
        "Date": [
            "2024-01-15", "2024-01-20", "2024-02-10", "2024-02-25",
            "2024-03-05", "2024-03-18", "2024-04-12", "2024-04-28"
        ],
        "Product": ["Widget A", "Widget B", "Widget A", "Widget C", "Widget B", "Widget A", "Widget C", "Widget A"],
        "Region": ["North", "South", "North", "East", "South", "West", "East", "West"],
        "Revenue": [1000.0, 2000.0, 1500.0, 500.0, 2500.0, 3000.0, 800.0, 1200.0],
        "Units": [10, 20, 15, 5, 25, 30, 8, 12]
    }
    # Mathematical ground truth:
    # Total Revenue = 1000 + 2000 + 1500 + 500 + 2500 + 3000 + 800 + 1200 = 12500.0
    # Mean Revenue = 12500 / 8 = 1562.5
    # Min Revenue = 500.0
    # Max Revenue = 3000.0
    # Median Revenue = (1200 + 1500) / 2 = 1350.0
    # Total Units = 10 + 20 + 15 + 5 + 25 + 30 + 8 + 12 = 125
    # Product sums:
    #   Widget A: 1000 + 1500 + 3000 + 1200 = 6700.0
    #   Widget B: 2000 + 2500 = 4500.0
    #   Widget C: 500 + 800 = 1300.0
    # Monthly sums:
    #   2024-01: 1000 + 2000 = 3000.0
    #   2024-02: 1500 + 500 = 2000.0
    #   2024-03: 2500 + 3000 = 5500.0
    #   2024-04: 800 + 1200 = 2000.0

    df_sales = pd.DataFrame(sales_data)
    sales_bytes = df_sales.to_csv(index=False).encode('utf-8')
    sales_profile = save_uploaded_dataset(io.BytesIO(sales_bytes), "test_sales_db.csv")
    sales_id = sales_profile["dataset"]["dataset_id"]

    try:
        # A. Summary
        summary = get_dataset_summary(sales_id)
        assert summary["row_count"] == 8
        assert summary["column_count"] == 5
        assert "Revenue" in summary["numeric_columns"]
        assert "Units" in summary["numeric_columns"]
        assert "Product" in summary["categorical_columns"]
        assert "Date" in summary["datetime_columns"]
        print("  -> Summary verified.")

        # B. Numeric Statistics (exact values)
        rev_stats = get_numeric_statistics(sales_id, "Revenue")
        assert rev_stats["count"] == 8
        assert rev_stats["missing"] == 0
        assert rev_stats["sum"] == 12500.0
        assert rev_stats["mean"] == 1562.5
        assert rev_stats["min"] == 500.0
        assert rev_stats["max"] == 3000.0
        assert rev_stats["median"] == 1350.0
        print("  -> Numeric statistics strictly verified.")

        # C. Category Aggregation
        prod_rev = aggregate_by_category(sales_id, "Product", "Revenue", aggregation="sum")
        prod_map = {item["category"]: item["value"] for item in prod_rev}
        assert prod_map["Widget A"] == 6700.0
        assert prod_map["Widget B"] == 4500.0
        assert prod_map["Widget C"] == 1300.0

        # Mean aggregation
        prod_mean = aggregate_by_category(sales_id, "Product", "Revenue", aggregation="mean")
        mean_map = {item["category"]: item["value"] for item in prod_mean}
        assert mean_map["Widget A"] == 1675.0  # 6700 / 4
        assert mean_map["Widget B"] == 2250.0  # 4500 / 2
        assert mean_map["Widget C"] == 650.0   # 1300 / 2
        print("  -> Category aggregation strictly verified.")

        # D. Top / Bottom Categories
        top_res = get_top_categories(sales_id, "Product", "Revenue", aggregation="sum", limit=2)
        assert len(top_res["items"]) == 2
        assert top_res["items"][0]["category"] == "Widget A"
        assert top_res["items"][0]["value"] == 6700.0
        assert top_res["items"][1]["category"] == "Widget B"
        assert top_res["items"][1]["value"] == 4500.0

        bot_res = get_bottom_categories(sales_id, "Product", "Revenue", aggregation="sum", limit=1)
        assert len(bot_res["items"]) == 1
        assert bot_res["items"][0]["category"] == "Widget C"
        assert bot_res["items"][0]["value"] == 1300.0
        print("  -> Top and bottom performers verified.")

        # E. Time Trend Analysis
        trend_res = get_time_trend(sales_id, "Date", "Revenue", aggregation="sum", frequency="month")
        trend_map = {item["period"]: item["value"] for item in trend_res["data"]}
        assert trend_map["2024-01"] == 3000.0
        assert trend_map["2024-02"] == 2000.0
        assert trend_map["2024-03"] == 5500.0
        assert trend_map["2024-04"] == 2000.0
        assert trend_res["metadata"]["number_of_periods"] == 4
        print("  -> Time trend strictly verified.")

        # F. KPIs
        kpis_res = get_kpis(sales_id)
        assert "Revenue" in kpis_res["kpis"]
        assert "Units" in kpis_res["kpis"]
        assert kpis_res["kpis"]["Revenue"]["total"] == 12500.0
        assert kpis_res["kpis"]["Revenue"]["average"] == 1562.5
        assert kpis_res["kpis"]["Units"]["total"] == 125
        print("  -> KPIs verified.")

    finally:
        delete_dataset_by_id(sales_id)

    # -------------------------------------------------------------
    # 2. EMPLOYEE DATASET FIXTURE (ID heuristic & Dept Aggregations)
    # -------------------------------------------------------------
    print("\n[Test 2] Testing Employee Dataset & Identifier Exclusion Heuristic...")
    emp_data = {
        "Employee_ID": [101, 102, 103, 104, 105, 106],
        "Employee": ["Alice", "Bob", "Charlie", "David", "Eve", "Frank"],
        "Department": ["Engineering", "Engineering", "Sales", "Sales", "HR", "Engineering"],
        "Salary": [120000, 110000, 95000, 85000, 75000, 130000],
        "JoinDate": ["2021-03-01", "2021-07-15", "2022-01-10", "2022-06-01", "2023-02-20", "2023-11-15"]
    }
    # Dept Salary Sums:
    #   Engineering: 120000 + 110000 + 130000 = 360000
    #   Sales: 95000 + 85000 = 180000
    #   HR: 75000
    # Total Salary = 615000
    # Mean Salary = 102500.0

    df_emp = pd.DataFrame(emp_data)
    emp_bytes = df_emp.to_csv(index=False).encode('utf-8')
    emp_profile = save_uploaded_dataset(io.BytesIO(emp_bytes), "test_emp_db.csv")
    emp_id = emp_profile["dataset"]["dataset_id"]

    try:
        # Check ID Heuristic
        assert is_likely_identifier_column(df_emp["Employee_ID"], "Employee_ID") == True
        assert is_likely_identifier_column(df_emp["Salary"], "Salary") == False

        # Check KPIs: Employee_ID must be in excluded_id_columns and NOT in kpis
        emp_kpis = get_kpis(emp_id)
        assert "Employee_ID" in emp_kpis["excluded_id_columns"]
        assert "Employee_ID" not in emp_kpis["kpis"]
        assert "Salary" in emp_kpis["kpis"]
        assert emp_kpis["kpis"]["Salary"]["total"] == 615000
        assert emp_kpis["kpis"]["Salary"]["average"] == 102500.0
        print("  -> Identifier exclusion heuristic verified (Employee_ID excluded, Salary computed).")

        # Department aggregation
        dept_sal = aggregate_by_category(emp_id, "Department", "Salary", aggregation="sum")
        dept_map = {item["category"]: item["value"] for item in dept_sal}
        assert dept_map["Engineering"] == 360000
        assert dept_map["Sales"] == 180000
        assert dept_map["HR"] == 75000
        print("  -> Department salary aggregation verified.")

        # JoinDate trend
        emp_trend = get_time_trend(emp_id, "JoinDate", "Salary", aggregation="count", frequency="year")
        trend_map = {item["period"]: item["value"] for item in emp_trend["data"]}
        assert trend_map["2021"] == 2
        assert trend_map["2022"] == 2
        assert trend_map["2023"] == 2
        print("  -> Yearly hiring trend verified.")

    finally:
        delete_dataset_by_id(emp_id)

    # -------------------------------------------------------------
    # 3. EDGE CASES & SAFETY VALIDATION
    # -------------------------------------------------------------
    print("\n[Test 3] Testing Edge Cases and Safe Error Handling...")

    # A. Non-existent dataset ID
    try:
        get_dataset_summary("non_existent_dataset_id_12345")
        assert False, "Should have raised DataBrainError"
    except DataBrainError as e:
        assert e.code == "DATASET_NOT_FOUND"
        print("  -> Non-existent dataset ID caught cleanly.")

    # Create small fixture for column/metric error tests
    small_df = pd.DataFrame({"Alpha": ["x", "y", "z"], "Beta": [10, 20, 30]})
    small_bytes = small_df.to_csv(index=False).encode('utf-8')
    small_profile = save_uploaded_dataset(io.BytesIO(small_bytes), "test_small_db.csv")
    small_id = small_profile["dataset"]["dataset_id"]

    try:
        # B. Non-existent column
        try:
            get_numeric_statistics(small_id, "NonExistentColumn")
            assert False, "Should have raised DataBrainError"
        except DataBrainError as e:
            assert e.code == "INVALID_COLUMN"
            print("  -> Invalid column error caught cleanly.")

        # C. Non-numeric metric for sum
        try:
            aggregate_by_category(small_id, "Alpha", "Alpha", aggregation="sum")
            assert False, "Should have raised DataBrainError"
        except DataBrainError as e:
            assert e.code == "NON_NUMERIC_COLUMN"
            print("  -> Non-numeric metric error caught cleanly.")

        # D. Invalid aggregation
        try:
            aggregate_by_category(small_id, "Alpha", "Beta", aggregation="unsupported_op")
            assert False, "Should have raised DataBrainError"
        except DataBrainError as e:
            assert e.code == "INVALID_AGGREGATION"
            print("  -> Invalid aggregation error caught cleanly.")

        # E. Invalid limit
        try:
            get_top_categories(small_id, "Alpha", "Beta", limit=999)
            assert False, "Should have raised DataBrainError"
        except DataBrainError as e:
            assert e.code == "INVALID_LIMIT"
            print("  -> Invalid limit error caught cleanly.")

        # F. Invalid date column
        try:
            get_time_trend(small_id, "Alpha", "Beta")
            assert False, "Should have raised DataBrainError"
        except DataBrainError as e:
            assert e.code == "INVALID_DATETIME_COLUMN"
            print("  -> Invalid datetime column caught cleanly.")

        # G. Invalid frequency
        try:
            get_time_trend(small_id, "Beta", "Beta", frequency="decade")
            assert False, "Should have raised DataBrainError"
        except DataBrainError as e:
            # First it checks if Beta is datetime or frequency
            assert e.code in ["INVALID_DATETIME_COLUMN", "INVALID_FREQUENCY"]
            print("  -> Invalid frequency/datetime caught cleanly.")

    finally:
        delete_dataset_by_id(small_id)

    print("\n==================================================")
    print("  [SUCCESS] ALL DATA BRAIN TESTS PASSED!")
    print("==================================================")

if __name__ == "__main__":
    test_data_brain_complete_suite()
