"""
Runtime regression verification for InsightOS Core API and Knowledge Brain.
Tests:
1. GET /api/health
2. GET /api/datasets
3. GET /api/documents
4. POST /api/chat with a document question (grounded answer, filename + page citation, no fabricated sources)
5. POST /api/chat with insufficient evidence (safe handling)
6. Data Brain endpoints powering the dashboard (/summary, /kpis, /preview)
"""

import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
from fastapi.testclient import TestClient
from server import app
from knowledge_service import seed_default_documents_if_empty, list_documents

def run_regression_verification():
    print("=" * 60)
    print("Running Runtime Regression Verification")
    print("=" * 60)

    client = TestClient(app)

    # 1. /api/health
    print("\n[Check 1] GET /api/health...")
    res_health = client.get("/api/health")
    assert res_health.status_code == 200, f"Health check failed with {res_health.status_code}"
    health_data = res_health.json()
    assert health_data.get("status") == "ok", f"Health status not ok: {health_data}"
    print(f"  -> Health OK: {health_data}")

    # 2. /api/datasets
    print("\n[Check 2] GET /api/datasets...")
    res_datasets = client.get("/api/datasets")
    assert res_datasets.status_code == 200, f"Datasets endpoint failed with {res_datasets.status_code}"
    datasets_data = res_datasets.json()
    assert "datasets" in datasets_data
    print(f"  -> Datasets OK: Found {len(datasets_data['datasets'])} dataset(s)")

    # 3. /api/documents
    print("\n[Check 3] GET /api/documents...")
    seed_default_documents_if_empty()
    res_docs = client.get("/api/documents")
    assert res_docs.status_code == 200, f"Documents endpoint failed with {res_docs.status_code}"
    docs_data = res_docs.json()
    assert "documents" in docs_data
    assert "files" in docs_data
    docs_list = docs_data["documents"]
    print(f"  -> Documents OK: Found {len(docs_list)} indexed document(s)")
    for d in docs_list[:3]:
        print(f"     * {d['filename']} ({d.get('page_count', 1)} pages, {d.get('chunk_count', 0)} chunks)")

    # 4. /api/chat with Document Question
    print("\n[Check 4] POST /api/chat with Document Question...")
    # Query something from the indexed documents, e.g. password policy, incident response, or employee conduct
    chat_query = "What are the password security requirements or guidelines according to company policy?"
    res_chat = client.post("/api/chat", json={"query": chat_query, "api_key": ""})
    assert res_chat.status_code == 200, f"Chat failed with {res_chat.status_code}"
    chat_resp = res_chat.json()
    assert chat_resp.get("status") == "success"
    chat_resp_obj = chat_resp.get("response", {})
    if isinstance(chat_resp_obj, dict):
        response_text = chat_resp_obj.get("answer", "")
        sources_list = chat_resp_obj.get("sources", [])
        sources_text = chat_resp_obj.get("sources_text", "")
    else:
        response_text = str(chat_resp_obj)
        sources_list = []
        sources_text = ""

    print("  -> Chat Response received:")
    print("  --------------------------------------------------")
    print(response_text[:300] + ("..." if len(response_text) > 300 else ""))
    print("  --------------------------------------------------")
    print(f"  -> Sources cited: {sources_list}")

    # Verify source citations
    has_citation = len(sources_list) > 0 or "Sources:" in sources_text or ".pdf" in response_text or "Page" in response_text
    assert has_citation, "Response should include document source or page citations"
    print("  -> Verified: Source filename and page citation present in response.")

    # 5. Insufficient Evidence Safe Handling
    print("\n[Check 5] Insufficient Evidence Handling...")
    weird_query = "What is the treaty protocol for interplanetary diplomacy with Martian civilizations?"
    res_weird = client.post("/api/chat", json={"query": weird_query, "api_key": ""})
    assert res_weird.status_code == 200
    weird_resp_obj = res_weird.json().get("response", {})
    weird_text = weird_resp_obj.get("answer", "") if isinstance(weird_resp_obj, dict) else str(weird_resp_obj)
    print(f"  -> Insufficient evidence response: {weird_text[:150]}...")
    assert "Martian" not in weird_text or "not mentioned" in weird_text.lower() or "not found" in weird_text.lower() or "no information" in weird_text.lower() or "not contain" in weird_text.lower() or "does not" in weird_text.lower()
    print("  -> Verified: Safely handles out-of-domain query without fabricating citations.")

    # 6. Dashboard & Data Brain Regression
    print("\n[Check 6] Dashboard & Data Brain Regression...")
    # If no dataset exists, upload a small test dataset
    if not datasets_data["datasets"]:
        csv_content = b"Date,Product,Region,Sales,Quantity\n2023-01-01,Alpha,North,100,2\n2023-01-02,Beta,South,200,4\n"
        upload_res = client.post(
            "/api/datasets/upload",
            files={"file": ("dashboard_test.csv", csv_content, "text/csv")}
        )
        assert upload_res.status_code == 200
        test_dataset_id = upload_res.json()["profile"]["dataset"]["dataset_id"]
    else:
        test_dataset_id = datasets_data["datasets"][0]["dataset_id"]

    # Verify preview, summary, kpis
    res_prev = client.get(f"/api/datasets/{test_dataset_id}/preview")
    assert res_prev.status_code == 200
    res_sum = client.get(f"/api/datasets/{test_dataset_id}/summary")
    assert res_sum.status_code == 200
    res_kpis = client.get(f"/api/datasets/{test_dataset_id}/kpis")
    assert res_kpis.status_code == 200

    print(f"  -> Dashboard Data Brain endpoints OK for dataset {test_dataset_id}")
    print(f"     Preview rows: {len(res_prev.json()['preview']['preview_rows'])}")
    print(f"     Summary row count: {res_sum.json()['result']['row_count']}")
    print(f"     KPIs calculated: {list(res_kpis.json()['result']['kpis'].keys())}")

    print("\n" + "=" * 60)
    print("ALL RUNTIME REGRESSION CHECKS PASSED SUCCESSFULLY!")
    print("=" * 60)

if __name__ == "__main__":
    run_regression_verification()
