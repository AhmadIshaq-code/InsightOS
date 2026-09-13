"""
Integration tests for Knowledge Brain REST API endpoints (server.py).
Tests:
- POST /api/documents/upload & /api/upload
- GET /api/documents
- POST /api/documents/search (global and filtered)
- DELETE /api/documents/{doc_id_or_name}
- Duplicate upload behavior
- Input validation (non-PDF, empty PDF)
- Multiple-document coexistence & deletion isolation
"""

import io
import uuid
import unittest
import pymupdf
from fastapi.testclient import TestClient

from server import app
from knowledge_service import delete_document


def make_test_pdf(text: str) -> bytes:
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((50, 72), text, fontsize=12)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


class TestKnowledgeAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_01_invalid_inputs(self):
        """Verify non-PDF and empty files are rejected."""
        # Non-PDF
        res = self.client.post(
            "/api/documents/upload",
            files={"file": ("notes.txt", b"plain text content", "text/plain")}
        )
        self.assertEqual(res.status_code, 400)

        # Empty PDF
        res = self.client.post(
            "/api/documents/upload",
            files={"file": ("empty.pdf", b"", "application/pdf")}
        )
        self.assertEqual(res.status_code, 400)

    def test_02_upload_and_listing(self):
        """Test document upload, metadata persistence, and document listing."""
        run_id = uuid.uuid4().hex[:8]
        content_a = f"Global Incident Escalation Matrix {run_id}: Tier 3 outages must alert On-Call Lead within 5 minutes."
        pdf_bytes_a = make_test_pdf(content_a)

        # Upload doc A
        upload_res = self.client.post(
            "/api/documents/upload",
            files={"file": (f"incident_matrix_{run_id}.pdf", pdf_bytes_a, "application/pdf")}
        )
        self.assertEqual(upload_res.status_code, 200)
        data = upload_res.json()
        self.assertEqual(data["status"], "success")
        doc_a_id = data["document"]["document_id"]
        self.assertEqual(data["document"]["filename"], f"incident_matrix_{run_id}.pdf")
        self.assertEqual(data["document"]["page_count"], 1)

        try:
            # Check listing
            list_res = self.client.get("/api/documents")
            self.assertEqual(list_res.status_code, 200)
            list_data = list_res.json()
            self.assertIn("documents", list_data)
            self.assertIn("files", list_data)
            doc_ids = [d["document_id"] for d in list_data["documents"]]
            self.assertIn(doc_a_id, doc_ids)

            # Test duplicate upload
            dupe_res = self.client.post(
                "/api/documents/upload",
                files={"file": (f"incident_copy_{run_id}.pdf", pdf_bytes_a, "application/pdf")}
            )
            self.assertEqual(dupe_res.status_code, 200)
            dupe_data = dupe_res.json()
            self.assertEqual(dupe_data["document"]["document_id"], doc_a_id)
            self.assertTrue(dupe_data["document"].get("is_duplicate", False))

        finally:
            self.client.delete(f"/api/documents/{doc_a_id}")

    def test_03_search_global_and_filtered(self):
        """Test global semantic search and document_id filtered search."""
        run_id = uuid.uuid4().hex[:8]
        text_eng = f"Engineering Standards {run_id}: All microservices must use TLS 1.3 mutual authentication."
        text_hr = f"HR Benefits Guide {run_id}: Dental coverage includes annual preventive care without deductible."

        pdf_eng = make_test_pdf(text_eng)
        pdf_hr = make_test_pdf(text_hr)

        res_eng = self.client.post(
            "/api/documents/upload",
            files={"file": (f"eng_standards_{run_id}.pdf", pdf_eng, "application/pdf")}
        )
        doc_eng_id = res_eng.json()["document"]["document_id"]

        res_hr = self.client.post(
            "/api/documents/upload",
            files={"file": (f"hr_benefits_{run_id}.pdf", pdf_hr, "application/pdf")}
        )
        doc_hr_id = res_hr.json()["document"]["document_id"]

        try:
            # Global Search for TLS 1.3
            search_res = self.client.post("/api/documents/search", json={
                "query": f"mutual authentication TLS {run_id}",
                "top_k": 5
            })
            self.assertEqual(search_res.status_code, 200)
            results = search_res.json()["results"]
            self.assertGreater(len(results), 0)
            self.assertEqual(results[0]["document_id"], doc_eng_id)
            self.assertEqual(results[0]["page"], 1)
            self.assertIn("relevance_score", results[0])

            # Filtered Search: query for TLS scoped to HR document should return 0 matches
            filtered_res = self.client.post("/api/documents/search", json={
                "query": f"mutual authentication TLS {run_id}",
                "top_k": 5,
                "document_id": doc_hr_id
            })
            self.assertEqual(filtered_res.status_code, 200)
            filtered_results = filtered_res.json()["results"]
            self.assertEqual(len(filtered_results), 0)

            # Filtered Search: query for dental coverage scoped to HR document
            hr_search_res = self.client.post("/api/documents/search", json={
                "query": f"dental coverage preventive care {run_id}",
                "top_k": 5,
                "document_id": doc_hr_id
            })
            self.assertEqual(hr_search_res.status_code, 200)
            hr_results = hr_search_res.json()["results"]
            self.assertGreater(len(hr_results), 0)
            self.assertEqual(hr_results[0]["document_id"], doc_hr_id)

        finally:
            self.client.delete(f"/api/documents/{doc_eng_id}")
            self.client.delete(f"/api/documents/{doc_hr_id}")

    def test_04_deletion_and_isolation(self):
        """Test document deletion removes target document while preserving other documents."""
        run_id = uuid.uuid4().hex[:8]
        text_1 = f"Document Alpha {run_id}: Confidential financial forecast protocols."
        text_2 = f"Document Beta {run_id}: Production deployment release checklist."

        res_1 = self.client.post(
            "/api/documents/upload",
            files={"file": (f"doc_alpha_{run_id}.pdf", make_test_pdf(text_1), "application/pdf")}
        )
        id_1 = res_1.json()["document"]["document_id"]

        res_2 = self.client.post(
            "/api/documents/upload",
            files={"file": (f"doc_beta_{run_id}.pdf", make_test_pdf(text_2), "application/pdf")}
        )
        id_2 = res_2.json()["document"]["document_id"]

        try:
            # Delete Document Alpha
            del_res = self.client.delete(f"/api/documents/{id_1}")
            self.assertEqual(del_res.status_code, 200)

            # Check listing: doc 1 gone, doc 2 still present
            list_res = self.client.get("/api/documents")
            doc_ids = [d["document_id"] for d in list_res.json()["documents"]]
            self.assertNotIn(id_1, doc_ids)
            self.assertIn(id_2, doc_ids)

            # Check search: doc 1 gone, doc 2 still searchable
            search_del = self.client.post("/api/documents/search", json={
                "query": f"financial forecast protocols {run_id}",
                "top_k": 3
            })
            id_1_matches = [r for r in search_del.json()["results"] if r["document_id"] == id_1]
            self.assertEqual(len(id_1_matches), 0)

            search_remain = self.client.post("/api/documents/search", json={
                "query": f"deployment release checklist {run_id}",
                "top_k": 3
            })
            self.assertGreater(len(search_remain.json()["results"]), 0)
            self.assertEqual(search_remain.json()["results"][0]["document_id"], id_2)

            # Deleting non-existent document returns 404
            del_404 = self.client.delete(f"/api/documents/non_existent_id_99999")
            self.assertEqual(del_404.status_code, 404)

        finally:
            self.client.delete(f"/api/documents/{id_2}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
