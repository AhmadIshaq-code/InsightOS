import io
import os
import pandas as pd
import numpy as np

from dataset_service import save_uploaded_dataset, delete_dataset_by_id, list_all_datasets
from data_brain import (
    get_dataset_summary,
    get_numeric_statistics,
    aggregate_by_category,
    get_top_categories,
    get_bottom_categories,
    get_time_trend,
    get_kpis,
    DataBrainError
)

def test_dashboard_backend_scenarios():
    print("==================================================")
    print("Running Dashboard Backend Scenarios & Edge Cases")
    print("==================================================")

    # -------------------------------------------------------------
    # Scenario 1: Dataset with 10+ Numeric Columns (Anti-Explosion)
    # -------------------------------------------------------------
    print("\n[Scenario 1] Dataset with 12 Numeric Columns...")
    num_cols_data = {"ID_Code": [1001, 1002, 1003, 1004, 1005]}
    for i in range(1, 12):
        num_cols_data[f"Metric_{i}"] = [i * 10.0, i * 20.0, i * 15.0, i * 30.0, i * 25.0]

    df_many = pd.DataFrame(num_cols_data)
    many_bytes = df_many.to_csv(index=False).encode('utf-8')
    profile_many = save_uploaded_dataset(io.BytesIO(many_bytes), "test_many_cols.csv")
    id_many = profile_many["dataset"]["dataset_id"]

    try:
        summary_many = get_dataset_summary(id_many)
        kpis_many = get_kpis(id_many)

        assert summary_many["column_count"] == 12
        assert len(summary_many["numeric_columns"]) == 12
        # ID_Code should be identified and excluded from business KPIs
        assert "ID_Code" in kpis_many["excluded_id_columns"]
        assert "ID_Code" not in kpis_many["kpis"]
        # All 11 other business metrics should be present in kpis payload
        for i in range(1, 12):
            metric_name = f"Metric_{i}"
            assert metric_name in kpis_many["kpis"]
            assert kpis_many["kpis"][metric_name]["total"] == sum([i * 10.0, i * 20.0, i * 15.0, i * 30.0, i * 25.0])
        print("  -> 12-column dataset handled successfully with ID_Code excluded and 11 metrics computed.")
    finally:
        delete_dataset_by_id(id_many)

    # -------------------------------------------------------------
    # Scenario 2: Limited Dataset — Only Categorical / No Date / No Numeric
    # -------------------------------------------------------------
    print("\n[Scenario 2] Limited Dataset (Only Categorical Columns)...")
    cat_only_data = {
        "Department": ["HR", "Engineering", "Marketing", "Sales", "Legal"],
        "Office": ["NYC", "SF", "NYC", "London", "London"]
    }
    df_cat = pd.DataFrame(cat_only_data)
    cat_bytes = df_cat.to_csv(index=False).encode('utf-8')
    profile_cat = save_uploaded_dataset(io.BytesIO(cat_bytes), "test_cat_only.csv")
    id_cat = profile_cat["dataset"]["dataset_id"]

    try:
        summary_cat = get_dataset_summary(id_cat)
        assert len(summary_cat["numeric_columns"]) == 0
        assert len(summary_cat["datetime_columns"]) == 0
        assert len(summary_cat["categorical_columns"]) == 2

        kpis_cat = get_kpis(id_cat)
        assert len(kpis_cat["kpis"]) == 0
        print("  -> Categorical-only dataset handled cleanly (0 numeric KPIs, 0 datetime columns).")

        # Trend call should fail with clean DataBrainError
        try:
            get_time_trend(id_cat, "Department", "Office")
            assert False, "Should have failed"
        except DataBrainError as e:
            assert e.code == "INVALID_DATETIME_COLUMN"
            print("  -> Trend on non-datetime column caught cleanly with INVALID_DATETIME_COLUMN.")
    finally:
        delete_dataset_by_id(id_cat)

    # -------------------------------------------------------------
    # Scenario 3: Limited Dataset — Only Datetime and Numeric (No Categorical)
    # -------------------------------------------------------------
    print("\n[Scenario 3] Limited Dataset (No Categorical Columns)...")
    ts_only_data = {
        "Timestamp": ["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04"],
        "Sensor_Reading": [98.6, 99.1, 98.4, 100.2]
    }
    df_ts = pd.DataFrame(ts_only_data)
    ts_bytes = df_ts.to_csv(index=False).encode('utf-8')
    profile_ts = save_uploaded_dataset(io.BytesIO(ts_bytes), "test_ts_only.csv")
    id_ts = profile_ts["dataset"]["dataset_id"]

    try:
        summary_ts = get_dataset_summary(id_ts)
        assert len(summary_ts["categorical_columns"]) == 0
        assert len(summary_ts["datetime_columns"]) == 1
        assert len(summary_ts["numeric_columns"]) == 1

        # Trend should succeed
        trend_ts = get_time_trend(id_ts, "Timestamp", "Sensor_Reading", frequency="day")
        assert len(trend_ts["data"]) == 4
        print("  -> Time-series only dataset trend computed successfully.")
    finally:
        delete_dataset_by_id(id_ts)

    # -------------------------------------------------------------
    # Scenario 4: Non-existent Dataset ID
    # -------------------------------------------------------------
    print("\n[Scenario 4] Invalid Dataset ID Error Handling...")
    try:
        get_dataset_summary("completely_nonexistent_dataset_guid")
        assert False, "Should have failed"
    except DataBrainError as e:
        assert e.code == "DATASET_NOT_FOUND"
        print("  -> Invalid dataset ID handled cleanly with DATASET_NOT_FOUND.")

    print("\n==================================================")
    print("  [SUCCESS] ALL DASHBOARD SCENARIO TESTS PASSED!")
    print("==================================================")

if __name__ == "__main__":
    test_dashboard_backend_scenarios()
