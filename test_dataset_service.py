import io
import os
import json
import pandas as pd
import numpy as np
from dataset_service import (
    calculate_dataset_profile,
    save_uploaded_dataset,
    list_all_datasets,
    get_dataset_profile_by_id,
    get_dataset_preview,
    delete_dataset_by_id,
    sanitize_filename
)

def run_tests():
    print("==================================================")
    print("Running InsightOS Dataset Service Automated Tests")
    print("==================================================")

    # 1. Test Sanitize Filename
    print("\n[Test 1] Filename sanitization...")
    assert sanitize_filename("../../../etc/passwd.csv") == "passwd.csv"
    assert sanitize_filename("..\\..\\windows\\system32\\calc.xlsx") == "calc.xlsx"
    print("  -> Passed safe filename sanitation.")

    # 2. Test Dataset A: CSV (Sales data with >= 20 rows)
    print("\n[Test 2] Test Dataset A: Sales CSV (25 rows)...")
    sales_data = {
        "Date": [f"2026-01-{i:02d}" for i in range(1, 26)],
        "Product": ["Alpha", "Beta", "Gamma", "Delta", "Epsilon"] * 5,
        "Region": ["North", "South", "East", "West", "Central"] * 5,
        "Sales": [120.5 + (i * 15.2) for i in range(25)],
        "Quantity": [1 + (i % 8) for i in range(25)]
    }
    df_sales = pd.DataFrame(sales_data)
    csv_bytes = df_sales.to_csv(index=False).encode('utf-8')
    file_obj_a = io.BytesIO(csv_bytes)

    profile_a = save_uploaded_dataset(file_obj_a, "sales_q1.csv")
    id_a = profile_a["dataset"]["dataset_id"]
    print(f"  -> Uploaded and profiled dataset ID: {id_a}")
    assert profile_a["dataset"]["row_count"] == 25
    assert profile_a["dataset"]["column_count"] == 5
    assert profile_a["quality"]["missing_cells"] == 0
    assert profile_a["quality"]["score"] == 100.0

    # Verify column semantic types
    col_types_a = {col["name"]: col["semantic_type"] for col in profile_a["columns"]}
    print(f"  -> Detected column semantic types: {col_types_a}")
    assert col_types_a["Date"] == "datetime"
    assert col_types_a["Sales"] == "numeric"
    assert col_types_a["Quantity"] == "numeric"
    assert col_types_a["Product"] == "categorical"
    assert col_types_a["Region"] == "categorical"

    # Verify numeric stats
    sales_stats = profile_a["numeric_statistics"]["Sales"]
    assert sales_stats["min"] == round(float(df_sales["Sales"].min()), 4)
    assert sales_stats["max"] == round(float(df_sales["Sales"].max()), 4)
    print(f"  -> Numeric stats verified: min={sales_stats['min']}, max={sales_stats['max']}, mean={sales_stats['mean']}")

    # 3. Test Dataset B: XLSX (Employee dataset)
    print("\n[Test 3] Test Dataset B: Employee Excel XLSX...")
    emp_data = {
        "Employee": ["Alice Smith", "Bob Jones", "Charlie Brown", "Diana Prince", "Evan Wright"],
        "Department": ["Engineering", "Marketing", "Engineering", "Finance", "HR"],
        "Salary": [95000, 72000, 105000, 88000, 65000],
        "JoiningDate": pd.date_range("2021-01-01", periods=5, freq="180D")
    }
    df_emp = pd.DataFrame(emp_data)
    excel_buffer = io.BytesIO()
    with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
        df_emp.to_excel(writer, index=False)
    excel_bytes = excel_buffer.getvalue()
    file_obj_b = io.BytesIO(excel_bytes)

    profile_b = save_uploaded_dataset(file_obj_b, "employees.xlsx")
    id_b = profile_b["dataset"]["dataset_id"]
    print(f"  -> Uploaded and profiled XLSX ID: {id_b}")
    assert profile_b["dataset"]["file_type"] == "xlsx"
    assert profile_b["dataset"]["row_count"] == 5
    assert profile_b["dataset"]["column_count"] == 4
    col_types_b = {col["name"]: col["semantic_type"] for col in profile_b["columns"]}
    assert col_types_b["Salary"] == "numeric"
    assert col_types_b["Department"] == "categorical"
    print("  -> Excel column types verified.")

    # 4. Test Dataset C: Messy Dataset
    print("\n[Test 4] Test Dataset C: Messy Data (nulls, duplicates, empty column, constant column)...")
    messy_data = {
        "ID": [1, 2, 2, 4, 5, 5],                       # Contains duplicate row (indices 1 & 2, 4 & 5)
        "Category": ["A", "B", "B", None, "E", "E"],    # Contains 1 missing value
        "Constant": ["FIXED", "FIXED", "FIXED", "FIXED", "FIXED", "FIXED"], # 1 Constant column
        "EmptyCol": [None, None, None, None, None, None] # 1 Completely empty column (6 missing values)
    }
    df_messy = pd.DataFrame(messy_data)
    # Save as canonical reference file for live API verification
    df_messy.to_csv("canonical_test_messy.csv", index=False)
    
    messy_bytes = df_messy.to_csv(index=False).encode('utf-8')
    file_obj_c = io.BytesIO(messy_bytes)

    profile_c = save_uploaded_dataset(file_obj_c, "canonical_test_messy.csv")
    id_c = profile_c["dataset"]["dataset_id"]
    print(f"  -> Uploaded and profiled Messy dataset ID: {id_c}")
    quality_c = profile_c["quality"]
    print(f"  -> Quality metrics computed: {quality_c}")
    assert quality_c["missing_cells"] == 7 # 1 in Category, 6 in EmptyCol
    assert quality_c["missing_percentage"] == 29.17
    assert quality_c["duplicate_rows"] == 2
    assert quality_c["duplicate_percentage"] == 33.33
    assert quality_c["empty_columns"] == 1
    assert quality_c["constant_columns"] == 1 # Excludes EmptyCol
    assert "Category" in quality_c["columns_with_missing"]
    assert "EmptyCol" in quality_c["columns_with_missing"]
    assert quality_c["score"] == 68.0 # 100 - (11.6667 + 13.3333 + 5.0 + 2.0)
    print("  -> Data quality calculation strictly verified: score = 68.0%")

    # 5. Test Dataset Preview
    print("\n[Test 5] Dataset Preview...")
    preview_a = get_dataset_preview(id_a, limit=10)
    assert len(preview_a["preview_rows"]) == 10
    assert preview_a["total_rows"] == 25
    assert preview_a["total_columns"] == 5
    print("  -> Preview successfully verified.")

    # 6. Test Listing & Retrieval
    print("\n[Test 6] List and fetch datasets...")
    all_datasets = list_all_datasets()
    assert len(all_datasets) >= 3
    dataset_ids = [d["dataset_id"] for d in all_datasets]
    assert id_a in dataset_ids
    assert id_b in dataset_ids
    assert id_c in dataset_ids

    fetched_profile = get_dataset_profile_by_id(id_a)
    assert fetched_profile["dataset"]["original_filename"] == "sales_q1.csv"
    print("  -> Listing and retrieval verified.")

    # 7. Cleanup test datasets
    print("\n[Test 7] Cleanup test datasets...")
    delete_dataset_by_id(id_a)
    delete_dataset_by_id(id_b)
    delete_dataset_by_id(id_c)
    print("  -> Deleted test artifacts.")

    print("\n==================================================")
    print("  [SUCCESS] ALL DATASET SERVICE UNIT TESTS PASSED!")
    print("==================================================")

if __name__ == "__main__":
    run_tests()
