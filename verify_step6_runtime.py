"""
Synchronous Live Verification for Step 6 Phase 1 Reasoning Brain.
Verifies:
- GET /api/health
- GET /api/datasets
- GET /api/documents
- POST /api/chat:
  1. "What is the average salary?" -> DATA
  2. "What does the IT security policy say about incident reporting?" -> DOCS (real citation with filename + page)
  3. "Why might the business result be related to the company policy?" -> HYBRID (structured data + document evidence)
  4. "Hello, what can you do?" -> GENERAL
- Backward compatibility:
  - 'answer' string
  - 'sources' list
  - 'sources_text' string
  - 'intent', 'data_facts', 'document_evidence', 'citations'
"""

import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from fastapi.testclient import TestClient
from server import app
from knowledge_service import seed_default_documents_if_empty

def verify_step6():
    print("=" * 60)
    print("STEP 6 PHASE 1: RUNTIME REASONING BRAIN VERIFICATION")
    print("=" * 60)

    client = TestClient(app)

    # 1. /api/health
    print("\n[Check 1] GET /api/health...")
    res_health = client.get("/api/health")
    assert res_health.status_code == 200, f"Health check failed: {res_health.status_code}"
    print(f"  -> Health OK (200): {res_health.json()}")

    # 2. /api/datasets
    print("\n[Check 2] GET /api/datasets...")
    res_datasets = client.get("/api/datasets")
    assert res_datasets.status_code == 200, f"Datasets check failed: {res_datasets.status_code}"
    datasets = res_datasets.json().get("datasets", [])
    print(f"  -> Datasets OK (200): {len(datasets)} dataset(s) loaded")

    # 3. /api/documents
    print("\n[Check 3] GET /api/documents...")
    seed_default_documents_if_empty()
    res_docs = client.get("/api/documents")
    assert res_docs.status_code == 200, f"Documents check failed: {res_docs.status_code}"
    docs = res_docs.json().get("documents", [])
    print(f"  -> Documents OK (200): {len(docs)} document(s) indexed")

    # Helper to check backward compatibility
    def assert_backward_compat(res_obj, label):
        assert "answer" in res_obj, f"Missing 'answer' in {label}"
        assert isinstance(res_obj["answer"], str) and len(res_obj["answer"]) > 0, f"Empty 'answer' in {label}"
        assert "sources" in res_obj and isinstance(res_obj["sources"], list), f"Missing or invalid 'sources' in {label}"
        assert "sources_text" in res_obj and isinstance(res_obj["sources_text"], str), f"Missing or invalid 'sources_text' in {label}"
        assert "intent" in res_obj, f"Missing 'intent' in {label}"
        assert "data_facts" in res_obj and isinstance(res_obj["data_facts"], list), f"Missing 'data_facts' in {label}"
        assert "document_evidence" in res_obj and isinstance(res_obj["document_evidence"], list), f"Missing 'document_evidence' in {label}"
        assert "citations" in res_obj and isinstance(res_obj["citations"], list), f"Missing 'citations' in {label}"
        print(f"  -> Backward compatibility verified for {label}")

    # 4. Question 1: DATA
    print("\n[Check 4] Question 1: 'What is the average salary?'")
    res1 = client.post("/api/chat", json={"query": "What is the average salary?"})
    assert res1.status_code == 200, f"Chat failed: {res1.status_code}"
    obj1 = res1.json()["response"]
    assert_backward_compat(obj1, "Q1 DATA")
    assert obj1["intent"] == "DATA", f"Expected DATA, got {obj1['intent']}"
    assert len(obj1["document_evidence"]) == 0, "DATA route should have empty document_evidence"
    assert len(obj1["citations"]) == 0, "DATA route should have empty citations"
    assert len(obj1["data_facts"]) > 0, "DATA route should have data_facts"
    print(f"  -> Intent: {obj1['intent']} (CONFIRMED)")
    print(f"  -> Data Facts: {obj1['data_facts'][:2]}")

    # 5. Question 2: DOCS
    print("\n[Check 5] Question 2: 'What does the IT security policy say about incident reporting?'")
    res2 = client.post("/api/chat", json={"query": "What does the IT security policy say about incident reporting?"})
    assert res2.status_code == 200, f"Chat failed: {res2.status_code}"
    obj2 = res2.json()["response"]
    assert_backward_compat(obj2, "Q2 DOCS")
    assert obj2["intent"] == "DOCS", f"Expected DOCS, got {obj2['intent']}"
    assert len(obj2["data_facts"]) == 0, "DOCS route should have empty data_facts"
    assert len(obj2["citations"]) > 0, "DOCS route should have real citations"
    assert any("it_security_policy.pdf" in c or ".pdf" in c for c in obj2["citations"]), f"Expected policy citation, got {obj2['citations']}"
    assert any("Page" in c for c in obj2["citations"]), f"Expected Page number in citations, got {obj2['citations']}"
    print(f"  -> Intent: {obj2['intent']} (CONFIRMED)")
    print(f"  -> Citations: {obj2['citations']}")

    # 6. Question 3: HYBRID
    print("\n[Check 6] Question 3: 'Why might the business result be related to the company policy?'")
    res3 = client.post("/api/chat", json={"query": "Why might the business result be related to the company policy?"})
    assert res3.status_code == 200, f"Chat failed: {res3.status_code}"
    obj3 = res3.json()["response"]
    assert_backward_compat(obj3, "Q3 HYBRID")
    assert obj3["intent"] == "HYBRID", f"Expected HYBRID, got {obj3['intent']}"
    assert len(obj3["data_facts"]) > 0, "HYBRID route should contain structured data facts"
    assert len(obj3["document_evidence"]) > 0, "HYBRID route should contain document evidence"
    print(f"  -> Intent: {obj3['intent']} (CONFIRMED)")
    print(f"  -> Structured Data Facts count: {len(obj3['data_facts'])}")
    print(f"  -> Document Evidence count: {len(obj3['document_evidence'])}")
    print(f"  -> Citations: {obj3['citations']}")

    # 7. Question 4: GENERAL
    print("\n[Check 7] Question 4: 'Hello, what can you do?'")
    res4 = client.post("/api/chat", json={"query": "Hello, what can you do?"})
    assert res4.status_code == 200, f"Chat failed: {res4.status_code}"
    obj4 = res4.json()["response"]
    assert_backward_compat(obj4, "Q4 GENERAL")
    assert obj4["intent"] == "GENERAL", f"Expected GENERAL, got {obj4['intent']}"
    assert len(obj4["data_facts"]) == 0, "GENERAL route should have no data_facts"
    assert len(obj4["document_evidence"]) == 0, "GENERAL route should have no document_evidence"
    assert len(obj4["citations"]) == 0, "GENERAL route should have no citations"
    print(f"  -> Intent: {obj4['intent']} (CONFIRMED)")
    print(f"  -> Answer snippet: {obj4['answer'][:120]}...")

    print("\n" + "=" * 60)
    print("ALL STEP 6 PHASE 1 RUNTIME CHECKS PASSED SUCCESSFULLY!")
    print("=" * 60)

if __name__ == "__main__":
    verify_step6()
