import requests
import json

BASE_URL = "http://127.0.0.1:8000"

def test_api():
    print("==================================================")
    print("Testing InsightOS Live Data Brain API Endpoints")
    print("==================================================")

    # 1. Health check
    res = requests.get(f"{BASE_URL}/api/health")
    assert res.status_code == 200
    print("[1] /api/health -> 200 OK")

    # 2. Upload test dataset
    csv_content = (
        "Date,Product,Region,Revenue,Units\n"
        "2024-01-15,Widget A,North,1000,10\n"
        "2024-01-20,Widget B,South,2000,20\n"
        "2024-02-10,Widget A,North,1500,15\n"
        "2024-02-25,Widget C,East,500,5\n"
        "2024-03-05,Widget B,South,2500,25\n"
        "2024-03-18,Widget A,West,3000,30\n"
        "2024-04-12,Widget C,East,800,8\n"
        "2024-04-28,Widget A,West,1200,12\n"
    )
    files = {"file": ("api_test_sales.csv", csv_content, "text/csv")}
    upload_res = requests.post(f"{BASE_URL}/api/datasets/upload", files=files)
    assert upload_res.status_code == 200
    data = upload_res.json()
    dataset_id = data["dataset"]["dataset_id"]
    print(f"[2] /api/datasets/upload -> 200 OK (Dataset ID: {dataset_id})")

    try:
        # 3. GET summary
        sum_res = requests.get(f"{BASE_URL}/api/datasets/{dataset_id}/summary")
        assert sum_res.status_code == 200
        sum_json = sum_res.json()
        assert sum_json["status"] == "success"
        assert sum_json["result"]["row_count"] == 8
        assert sum_json["result"]["column_count"] == 5
        print("[3] GET /api/datasets/{id}/summary -> 200 OK")

        # 4. GET statistics
        stat_res = requests.get(f"{BASE_URL}/api/datasets/{dataset_id}/statistics/Revenue")
        assert stat_res.status_code == 200
        stat_json = stat_res.json()
        assert stat_json["result"]["sum"] == 12500
        assert stat_json["result"]["mean"] == 1562.5
        assert stat_json["result"]["max"] == 3000
        print("[4] GET /api/datasets/{id}/statistics/Revenue -> 200 OK (exact sum=12500, mean=1562.5)")

        # 5. POST aggregate
        agg_res = requests.post(
            f"{BASE_URL}/api/datasets/{dataset_id}/aggregate",
            json={"category_column": "Product", "metric_column": "Revenue", "aggregation": "sum"}
        )
        assert agg_res.status_code == 200
        agg_json = agg_res.json()
        prod_map = {item["category"]: item["value"] for item in agg_json["result"]}
        assert prod_map["Widget A"] == 6700
        assert prod_map["Widget B"] == 4500
        assert prod_map["Widget C"] == 1300
        print("[5] POST /api/datasets/{id}/aggregate -> 200 OK (Widget A: 6700, B: 4500, C: 1300)")

        # 6. POST top
        top_res = requests.post(
            f"{BASE_URL}/api/datasets/{dataset_id}/top",
            json={"category_column": "Product", "metric_column": "Revenue", "limit": 2}
        )
        assert top_res.status_code == 200
        top_json = top_res.json()
        assert top_json["result"]["items"][0]["category"] == "Widget A"
        assert top_json["result"]["items"][0]["value"] == 6700
        print("[6] POST /api/datasets/{id}/top -> 200 OK (Top 1: Widget A @ 6700)")

        # 7. POST bottom
        bot_res = requests.post(
            f"{BASE_URL}/api/datasets/{dataset_id}/bottom",
            json={"category_column": "Product", "metric_column": "Revenue", "limit": 1}
        )
        assert bot_res.status_code == 200
        bot_json = bot_res.json()
        assert bot_json["result"]["items"][0]["category"] == "Widget C"
        assert bot_json["result"]["items"][0]["value"] == 1300
        print("[7] POST /api/datasets/{id}/bottom -> 200 OK (Bottom 1: Widget C @ 1300)")

        # 8. POST trend
        trend_res = requests.post(
            f"{BASE_URL}/api/datasets/{dataset_id}/trend",
            json={"date_column": "Date", "metric_column": "Revenue", "aggregation": "sum", "frequency": "month"}
        )
        assert trend_res.status_code == 200
        trend_json = trend_res.json()
        trend_map = {item["period"]: item["value"] for item in trend_json["result"]["data"]}
        assert trend_map["2024-01"] == 3000
        assert trend_map["2024-03"] == 5500
        print("[8] POST /api/datasets/{id}/trend -> 200 OK (2024-01: 3000, 2024-03: 5500)")

        # 9. GET kpis
        kpi_res = requests.get(f"{BASE_URL}/api/datasets/{dataset_id}/kpis")
        assert kpi_res.status_code == 200
        kpi_json = kpi_res.json()
        assert kpi_json["result"]["kpis"]["Revenue"]["total"] == 12500
        assert kpi_json["result"]["kpis"]["Units"]["total"] == 125
        print("[9] GET /api/datasets/{id}/kpis -> 200 OK (Revenue: 12500, Units: 125)")

        # 10. Negative tests: invalid column error handling
        bad_col_res = requests.post(
            f"{BASE_URL}/api/datasets/{dataset_id}/aggregate",
            json={"category_column": "NonExistent", "metric_column": "Revenue"}
        )
        assert bad_col_res.status_code == 400
        bad_json = bad_col_res.json()
        assert bad_json["status"] == "error"
        assert bad_json["error"]["code"] == "INVALID_COLUMN"
        print(f"[10] Negative validation test -> 400 with code '{bad_json['error']['code']}'")

    finally:
        # Delete test dataset
        del_res = requests.delete(f"{BASE_URL}/api/datasets/{dataset_id}")
        assert del_res.status_code == 200
        print("[11] DELETE /api/datasets/{id} -> 200 OK (Cleaned up)")

    print("\n==================================================")
    print("  [SUCCESS] ALL LIVE DATA BRAIN API TESTS PASSED!")
    print("==================================================")

if __name__ == "__main__":
    test_api()
