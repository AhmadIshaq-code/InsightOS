"""
Unit tests for InsightOS Knowledge Brain (knowledge_service.py)
Tests:
- Validation (PDF only, max size, non-empty)
- Deterministic content hashing
- Page-aware extraction with PyMuPDF (1-indexed pages)
- Chunking with metadata preservation
- Incremental Chroma indexing (multiple coexisting documents)
- Duplicate detection via SHA-256
- Filtered semantic search (document_id scoping)
- Document-level deletion without wiping other documents
"""

import os
import sys
import io
import shutil
import unittest
import pymupdf

# Set testing environment paths if needed
import knowledge_service
from knowledge_service import (
    validate_document,
    compute_content_hash,
    extract_pdf_pages,
    chunk_document_pages,
    index_document,
    get_document,
    list_documents,
    delete_document,
    search_documents,
    DOCUMENTS_DIR,
    CHROMA_DB_DIR
)


def create_synthetic_pdf(pages_text: list[str]) -> io.BytesIO:
    """Creates an in-memory PDF using PyMuPDF with specified text per page."""
    doc = pymupdf.open()
    for text in pages_text:
        page = doc.new_page()
        page.insert_text((50, 72), text, fontsize=12)
    pdf_bytes = io.BytesIO(doc.tobytes())
    doc.close()
    return pdf_bytes


class TestKnowledgeBrain(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        pass

    def test_01_validation(self):
        """Test document validation rules."""
        # Non-PDF
        with self.assertRaises(ValueError):
            validate_document(io.BytesIO(b"hello world"), "notes.txt")

        # Empty PDF
        with self.assertRaises(ValueError):
            validate_document(io.BytesIO(b""), "empty.pdf")

        # Valid PDF
        pdf_stream = create_synthetic_pdf(["This is a test document."])
        clean_name = validate_document(pdf_stream, "test.pdf")
        self.assertEqual(clean_name, "test.pdf")

    def test_02_content_hash(self):
        """Test SHA-256 content hash determinism."""
        stream1 = io.BytesIO(b"%PDF-1.4 test document content A")
        stream2 = io.BytesIO(b"%PDF-1.4 test document content A")
        stream3 = io.BytesIO(b"%PDF-1.4 test document content B")

        hash1 = compute_content_hash(stream1)
        hash2 = compute_content_hash(stream2)
        hash3 = compute_content_hash(stream3)

        self.assertEqual(hash1, hash2)
        self.assertNotEqual(hash1, hash3)
        self.assertEqual(len(hash1), 64)

    def test_03_page_extraction(self):
        """Test page extraction preserves 1-indexed page numbers."""
        pages = [
            "Page 1: Policy Overview and Governance protocols for InsightOS.",
            "Page 2: Incident Response procedure and emergency notification escalation tree.",
            "Page 3: Remote work guidelines, VPN authentication, and data classification."
        ]
        pdf_stream = create_synthetic_pdf(pages)
        extracted = extract_pdf_pages(pdf_stream)

        self.assertEqual(len(extracted), 3)
        self.assertEqual(extracted[0][0], 1)
        self.assertEqual(extracted[1][0], 2)
        self.assertEqual(extracted[2][0], 3)
        self.assertIn("Governance protocols", extracted[0][1])
        self.assertIn("emergency notification", extracted[1][1])
        self.assertIn("Remote work guidelines", extracted[2][1])

    def test_04_chunking(self):
        """Test text chunking with metadata preservation."""
        pages = [
            {"page": 1, "text": "Paragraph A " * 50},
            {"page": 2, "text": "Paragraph B " * 50}
        ]
        chunks = chunk_document_pages(
            pages_data=pages,
            doc_id="doc-test-uuid-123",
            filename="test_manual.pdf",
            chunk_size=300,
            chunk_overlap=50
        )
        self.assertGreater(len(chunks), 2)
        for chunk in chunks:
            self.assertEqual(chunk["metadata"]["document_id"], "doc-test-uuid-123")
            self.assertEqual(chunk["metadata"]["filename"], "test_manual.pdf")
            self.assertIn(chunk["metadata"]["page"], [1, 2])
            self.assertIn("chunk_index", chunk["metadata"])

    def test_05_incremental_indexing_and_coexistence(self):
        """Test indexing two distinct documents without wiping each other."""
        import uuid
        run_token = uuid.uuid4().hex[:8]

        text_a = f"Alpha Corporation Cybersecurity Policy {run_token}: All employees must enable YubiKey hardware 2FA."
        pdf_bytes_a = create_synthetic_pdf([text_a]).getvalue()
        pdf_a = io.BytesIO(pdf_bytes_a)
        doc_a = index_document(pdf_a, f"alpha_policy_{run_token}.pdf")
        self.assertIn("document_id", doc_a)
        self.assertEqual(doc_a["filename"], f"alpha_policy_{run_token}.pdf")
        self.assertEqual(doc_a["page_count"], 1)
        self.assertGreater(doc_a["chunk_count"], 0)

        text_b = f"Beta Medical Leave Guidelines {run_token}: Maternity and paternity leave eligibility requires 180 days service."
        pdf_b = create_synthetic_pdf([text_b])
        doc_b = index_document(pdf_b, f"beta_guidelines_{run_token}.pdf")
        self.assertIn("document_id", doc_b)
        self.assertEqual(doc_b["filename"], f"beta_guidelines_{run_token}.pdf")

        try:
            # Verify both coexist in document listing
            all_docs = list_documents()
            doc_ids = [d["document_id"] for d in all_docs]
            self.assertIn(doc_a["document_id"], doc_ids)
            self.assertIn(doc_b["document_id"], doc_ids)

            # Global search: both should be retrievable
            results_a = search_documents(f"YubiKey hardware 2FA {run_token}", top_k=3)
            self.assertGreater(len(results_a), 0)
            self.assertEqual(results_a[0]["document_id"], doc_a["document_id"])
            self.assertEqual(results_a[0]["filename"], f"alpha_policy_{run_token}.pdf")
            self.assertEqual(results_a[0]["page"], 1)
            self.assertIsNotNone(results_a[0]["relevance_score"])

            results_b = search_documents(f"maternity leave 180 days {run_token}", top_k=3)
            self.assertGreater(len(results_b), 0)
            self.assertEqual(results_b[0]["document_id"], doc_b["document_id"])
            self.assertEqual(results_b[0]["filename"], f"beta_guidelines_{run_token}.pdf")

            # Filtered search: query for YubiKey scoped only to doc_b should return 0 results
            scoped_results = search_documents(f"YubiKey hardware 2FA {run_token}", top_k=3, document_id=doc_b["document_id"])
            self.assertEqual(len(scoped_results), 0)

            # Filtered search scoped to doc_a should return it
            scoped_results_a = search_documents(f"YubiKey hardware 2FA {run_token}", top_k=3, document_id=doc_a["document_id"])
            self.assertGreater(len(scoped_results_a), 0)
            self.assertEqual(scoped_results_a[0]["document_id"], doc_a["document_id"])

            # Test duplicate prevention: re-uploading doc_a content should detect duplicate
            pdf_a_dupe = io.BytesIO(pdf_bytes_a)
            dupe_result = index_document(pdf_a_dupe, f"alpha_copy_{run_token}.pdf")
            self.assertEqual(dupe_result["document_id"], doc_a["document_id"])
            self.assertTrue(dupe_result.get("is_duplicate", False))

            # Test Document-level deletion: delete doc_a, verify doc_b remains intact
            del_success = delete_document(doc_a["document_id"])
            self.assertTrue(del_success)

            # doc_a should no longer be in list
            updated_docs = list_documents()
            updated_ids = [d["document_id"] for d in updated_docs]
            self.assertNotIn(doc_a["document_id"], updated_ids)
            self.assertIn(doc_b["document_id"], updated_ids)

            # doc_a vectors should be deleted from Chroma
            res_after_del = search_documents(f"YubiKey hardware 2FA {run_token}", top_k=3)
            doc_a_matches = [r for r in res_after_del if r["document_id"] == doc_a["document_id"]]
            self.assertEqual(len(doc_a_matches), 0)

            # doc_b should still be searchable
            res_b_after = search_documents(f"maternity leave 180 days {run_token}", top_k=3)
            self.assertGreater(len(res_b_after), 0)
            self.assertEqual(res_b_after[0]["document_id"], doc_b["document_id"])

        finally:
            # Ensure cleanup
            delete_document(doc_a["document_id"])
            delete_document(doc_b["document_id"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
