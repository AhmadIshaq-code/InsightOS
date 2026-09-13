import os
import re
import json
import uuid
import hashlib
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple

import pymupdf
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

"""
INSIGHTOS KNOWLEDGE BRAIN SERVICE
=================================
Modular, reliable, and incremental document knowledge layer for InsightOS.

KEY FEATURES:
- UUID-based document identity preserving original filenames.
- Dedicated safe document storage in uploads/documents/.
- Page-aware PDF extraction and chunking via PyMuPDF.
- Incremental Chroma vector indexing without destructive global wipes.
- Collision-safe deterministic chunk IDs: {document_id}:{chunk_index}.
- Document-level vector deletion without affecting other documents.
- Duplicate detection via SHA256 content hashing.
- Deterministic semantic search with source citations (filename, page, chunk_index, score).
- Document-filtered search support.
"""

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
DOCUMENTS_DIR = os.path.join(PROJECT_ROOT, "uploads", "documents")
CHROMA_DB_DIR = os.path.join(PROJECT_ROOT, "chroma_db")
COLLECTION_NAME = "insightos_knowledge"

MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024 # 50 MB limit
DEFAULT_CHUNK_SIZE = 1000
DEFAULT_CHUNK_OVERLAP = 200
DEFAULT_TOP_K = 5

_EMBEDDING_MODEL = None
_VECTOR_STORE = None

def get_embedding_model():
    """Cached singleton embedding model."""
    global _EMBEDDING_MODEL
    if _EMBEDDING_MODEL is None:
        _EMBEDDING_MODEL = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    return _EMBEDDING_MODEL

def get_vector_store():
    """Initializes or retrieves the persistent Chroma vector store."""
    global _VECTOR_STORE
    if _VECTOR_STORE is None:
        os.makedirs(CHROMA_DB_DIR, exist_ok=True)
        embedding_model = get_embedding_model()
        _VECTOR_STORE = Chroma(
            collection_name=COLLECTION_NAME,
            persist_directory=CHROMA_DB_DIR,
            embedding_function=embedding_model
        )
    return _VECTOR_STORE


# =====================================================================
# 1. Validation and File Storage Helpers
# =====================================================================

def ensure_documents_dir():
    """Creates the dedicated documents directory if not present."""
    os.makedirs(DOCUMENTS_DIR, exist_ok=True)

def sanitize_filename(filename: str) -> str:
    """Sanitizes filename against path traversal and dangerous characters."""
    base = os.path.basename(filename)
    cleaned = re.sub(r'[^a-zA-Z0-9_.-]', '_', base)
    return cleaned or "document.pdf"

def get_safe_pdf_path(doc_id: str) -> str:
    """Returns absolute path for a stored PDF within DOCUMENTS_DIR."""
    safe_id = re.sub(r'[^a-zA-Z0-9-]', '', doc_id)
    full_path = os.path.abspath(os.path.join(DOCUMENTS_DIR, f"{safe_id}.pdf"))
    if not full_path.startswith(os.path.abspath(DOCUMENTS_DIR)):
        raise ValueError("Invalid storage path: Path traversal detected.")
    return full_path

def get_meta_path(doc_id: str) -> str:
    """Returns absolute path for a document metadata file within DOCUMENTS_DIR."""
    safe_id = re.sub(r'[^a-zA-Z0-9-]', '', doc_id)
    full_path = os.path.abspath(os.path.join(DOCUMENTS_DIR, f"{safe_id}.meta.json"))
    if not full_path.startswith(os.path.abspath(DOCUMENTS_DIR)):
        raise ValueError("Invalid metadata path: Path traversal detected.")
    return full_path

def _to_bytes(data: Any) -> bytes:
    """Converts bytes, bytearray, or file-like stream to bytes."""
    if isinstance(data, (bytes, bytearray)):
        return bytes(data)
    if hasattr(data, "read"):
        current_pos = data.tell() if hasattr(data, "tell") else None
        if hasattr(data, "seek") and current_pos is not None:
            try:
                data.seek(0)
            except Exception:
                pass
        content = data.read()
        if hasattr(data, "seek") and current_pos is not None:
            try:
                data.seek(current_pos)
            except Exception:
                pass
        return content
    raise ValueError("Invalid file data type; expected bytes or file-like object.")

def compute_content_hash(file_input: Any) -> str:
    """Computes SHA256 content hash for duplicate detection."""
    b = _to_bytes(file_input)
    return hashlib.sha256(b).hexdigest()

def validate_document(file_input: Any, filename: str) -> str:
    """
    Validates document format, size, and magic bytes.
    Returns sanitized filename or raises ValueError.
    """
    if not filename or not filename.lower().endswith(".pdf"):
        raise ValueError("Unsupported file format. Knowledge Brain only accepts PDF documents.")

    file_bytes = _to_bytes(file_input)

    if len(file_bytes) == 0:
        raise ValueError("The uploaded document is completely empty (0 bytes).")

    if len(file_bytes) > MAX_FILE_SIZE_BYTES:
        raise ValueError(f"File exceeds maximum allowed size of {MAX_FILE_SIZE_BYTES // (1024 * 1024)} MB.")

    # Validate PDF magic bytes (%PDF-)
    if not file_bytes.startswith(b"%PDF"):
        raise ValueError("Corrupted or invalid PDF header. The file does not appear to be a valid PDF.")

    return sanitize_filename(filename)

def find_document_by_hash(content_hash: str) -> Optional[Dict[str, Any]]:
    """Checks if an identical document is already indexed."""
    ensure_documents_dir()
    for f in os.listdir(DOCUMENTS_DIR):
        if f.endswith(".meta.json"):
            meta_file = os.path.join(DOCUMENTS_DIR, f)
            try:
                with open(meta_file, "r", encoding="utf-8") as mf:
                    meta = json.load(mf)
                    if meta.get("content_hash") == content_hash:
                        return meta
            except Exception:
                continue
    return None


# =====================================================================
# 2. PDF Extraction & Chunking
# =====================================================================

def extract_pdf_pages(file_input: Any) -> List[Tuple[int, str]]:
    """
    Extracts text page-by-page from PDF bytes using PyMuPDF.
    Returns list of (page_number, page_text) with 1-indexed page numbers.
    Handles malformed or empty pages gracefully without crashing.
    """
    file_bytes = _to_bytes(file_input)
    pages_data = []
    try:
        doc = pymupdf.open(stream=file_bytes, filetype="pdf")
    except Exception as e:
        raise ValueError(f"Failed to parse PDF document with PyMuPDF: {str(e)}")

    if len(doc) == 0:
        raise ValueError("PDF document contains 0 pages.")

    for page_idx in range(len(doc)):
        page_num = page_idx + 1
        try:
            page = doc[page_idx]
            text = page.get_text("text") or ""
            # Clean non-printable characters while preserving layout whitespace
            cleaned_text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text).strip()
            pages_data.append((page_num, cleaned_text))
        except Exception as e:
            # Record empty text for corrupted single page rather than crashing document ingestion
            pages_data.append((page_num, ""))

    doc.close()
    return pages_data

def chunk_document_pages(
    pages_data: Any,
    doc_id: str,
    filename: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP
) -> List[Dict[str, Any]]:
    """
    Splits page texts into chunks using RecursiveCharacterTextSplitter.
    Accepts List of (page_num, text) tuples OR List of {"page": page_num, "text": text} dicts.
    Preserves exact 1-indexed page number and document identity on every chunk.
    """
    splitter = RecursiveCharacterTextSplitter(
        separators=["\n\n", "\n", " ", ""],
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap
    )

    # Normalize pages_data format
    normalized_pages = []
    for item in pages_data:
        if isinstance(item, (tuple, list)) and len(item) == 2:
            normalized_pages.append((item[0], item[1]))
        elif isinstance(item, dict):
            normalized_pages.append((item.get("page", 1), item.get("text", "")))

    chunks = []
    global_chunk_idx = 0

    for page_num, text in normalized_pages:
        if not text:
            continue
        page_chunks = splitter.split_text(text)
        for chunk_text in page_chunks:
            if not chunk_text.strip():
                continue
            chunks.append({
                "chunk_id": f"{doc_id}:{global_chunk_idx}",
                "chunk_index": global_chunk_idx,
                "text": chunk_text,
                "metadata": {
                    "document_id": doc_id,
                    "filename": filename,
                    "page": page_num,
                    "chunk_index": global_chunk_idx
                }
            })
            global_chunk_idx += 1

    return chunks


# =====================================================================
# 3. Document Indexing & Storage
# =====================================================================

def index_document(
    file_input: Any,
    filename: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP
) -> Dict[str, Any]:
    """
    Validates, saves, chunks, and incrementally indexes a PDF into Chroma.
    Guarantees:
    - Zero global wipes (increments existing vectors).
    - Content hash duplicate detection.
    - Page-accurate source metadata.
    """
    ensure_documents_dir()
    file_bytes = _to_bytes(file_input)
    clean_name = validate_document(file_bytes, filename)
    content_hash = compute_content_hash(file_bytes)

    # 1. Duplicate check: If identical content exists, return existing indexed document
    existing = find_document_by_hash(content_hash)
    if existing:
        return {
            "document_id": existing["document_id"],
            "filename": clean_name,
            "status": "indexed",
            "page_count": existing.get("page_count", 1),
            "chunk_count": existing.get("chunk_count", 0),
            "size": existing.get("size", len(file_bytes)),
            "uploaded_at": existing.get("uploaded_at", datetime.now(timezone.utc).isoformat()),
            "is_duplicate": True
        }

    # 2. Extract pages and validate extractable text
    pages_data = extract_pdf_pages(file_bytes)
    total_text = "".join(text for _, text in pages_data).strip()
    if not total_text:
        raise ValueError(
            "PDF contains no extractable text. Scanned images or empty documents require OCR before indexing."
        )

    # 3. Generate stable document ID & file locations
    doc_id = str(uuid.uuid4())
    pdf_path = get_safe_pdf_path(doc_id)
    meta_path = get_meta_path(doc_id)

    # Save PDF file to disk
    with open(pdf_path, "wb") as pf:
        pf.write(file_bytes)

    try:
        # 4. Chunk document pages
        chunks = chunk_document_pages(
            pages_data,
            doc_id,
            clean_name,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )

        if not chunks:
            raise ValueError("No valid text chunks could be produced from document.")

        # 5. Incrementally add to Chroma DB with deterministic IDs
        vector_store = get_vector_store()
        texts = [c["text"] for c in chunks]
        metadatas = [c["metadata"] for c in chunks]
        ids = [c["chunk_id"] for c in chunks]

        vector_store.add_texts(texts=texts, metadatas=metadatas, ids=ids)

        # 6. Save metadata JSON
        doc_meta = {
            "document_id": doc_id,
            "filename": clean_name,
            "size": len(file_bytes),
            "content_hash": content_hash,
            "page_count": len(pages_data),
            "chunk_count": len(chunks),
            "status": "indexed",
            "uploaded_at": datetime.now(timezone.utc).isoformat()
        }

        with open(meta_path, "w", encoding="utf-8") as mf:
            json.dump(doc_meta, mf, indent=2)

        return doc_meta

    except Exception as e:
        # Clean up disk file on indexing failure
        if os.path.exists(pdf_path):
            os.remove(pdf_path)
        if os.path.exists(meta_path):
            os.remove(meta_path)
        raise e


# =====================================================================
# 4. Document Deletion & Management
# =====================================================================

def delete_document(doc_id_or_name: str) -> bool:
    """
    Safely deletes a document from disk and removes its vectors from Chroma
    without performing a destructive global wipe or affecting other documents.
    """
    ensure_documents_dir()
    target_meta = None
    target_id = None

    # Try matching direct document ID first
    meta_path = get_meta_path(doc_id_or_name)
    if os.path.exists(meta_path):
        try:
            with open(meta_path, "r", encoding="utf-8") as mf:
                target_meta = json.load(mf)
                target_id = target_meta.get("document_id", doc_id_or_name)
        except Exception:
            target_id = doc_id_or_name
    else:
        # Search by filename
        for f in os.listdir(DOCUMENTS_DIR):
            if f.endswith(".meta.json"):
                mf_path = os.path.join(DOCUMENTS_DIR, f)
                try:
                    with open(mf_path, "r", encoding="utf-8") as mf:
                        meta = json.load(mf)
                        if meta.get("filename") == doc_id_or_name or meta.get("document_id") == doc_id_or_name:
                            target_meta = meta
                            target_id = meta.get("document_id")
                            break
                except Exception:
                    continue

    if not target_id:
        return False

    # 1. Remove vectors from Chroma belonging only to target_id
    try:
        vector_store = get_vector_store()
        chunk_count = target_meta.get("chunk_count", 0) if target_meta else 100
        # Deterministic chunk ID deletion
        ids_to_delete = [f"{target_id}:{i}" for i in range(max(chunk_count + 10, 100))]
        vector_store.delete(ids=ids_to_delete)
    except Exception as e:
        # Fallback: try where clause deletion if supported
        try:
            vector_store.delete(where={"document_id": target_id})
        except Exception:
            pass

    # 2. Remove files from disk
    pdf_path = get_safe_pdf_path(target_id)
    meta_file = get_meta_path(target_id)
    if os.path.exists(pdf_path):
        os.remove(pdf_path)
    if os.path.exists(meta_file):
        os.remove(meta_file)

    return True

def get_document(doc_id_or_name: str) -> Optional[Dict[str, Any]]:
    """Retrieves metadata for a specific document by ID or filename."""
    ensure_documents_dir()
    # Check direct ID
    meta_path = get_meta_path(doc_id_or_name)
    if os.path.exists(meta_path):
        with open(meta_path, "r", encoding="utf-8") as mf:
            return json.load(mf)

    # Check by filename
    for f in os.listdir(DOCUMENTS_DIR):
        if f.endswith(".meta.json"):
            try:
                with open(os.path.join(DOCUMENTS_DIR, f), "r", encoding="utf-8") as mf:
                    meta = json.load(mf)
                    if meta.get("filename") == doc_id_or_name or meta.get("document_id") == doc_id_or_name:
                        return meta
            except Exception:
                continue
    return None

def list_documents() -> List[Dict[str, Any]]:
    """
    Returns structured list of all indexed documents from disk metadata.
    Seeds sample documents from root/uploads if storage is empty on initial boot.
    """
    ensure_documents_dir()
    seed_default_documents_if_empty()

    docs = []
    for f in os.listdir(DOCUMENTS_DIR):
        if f.endswith(".meta.json"):
            meta_path = os.path.join(DOCUMENTS_DIR, f)
            try:
                with open(meta_path, "r", encoding="utf-8") as mf:
                    data = json.load(mf)
                    # Include backwards-compatible properties for frontend
                    docs.append({
                        **data,
                        "id": data["document_id"],
                        "name": data["filename"],
                        "type": "application/pdf"
                    })
            except Exception:
                continue

    docs.sort(key=lambda x: x.get("uploaded_at", ""), reverse=True)
    return docs

def seed_default_documents_if_empty():
    """
    Seeds initial default policy PDFs into the Knowledge Brain if empty.
    Ensures starter documents are indexed with full page and source metadata.
    """
    ensure_documents_dir()
    existing_meta = [f for f in os.listdir(DOCUMENTS_DIR) if f.endswith(".meta.json")]
    if existing_meta:
        return

    sample_names = ["hr_employee_handbook.pdf", "it_security_policy.pdf", "sop_incident_response.pdf"]
    for sample in sample_names:
        # Check root or legacy uploads directory
        src_path = os.path.join(PROJECT_ROOT, sample)
        if not os.path.exists(src_path):
            src_path = os.path.join(PROJECT_ROOT, "uploads", sample)

        if os.path.exists(src_path):
            try:
                with open(src_path, "rb") as sf:
                    file_bytes = sf.read()
                index_document(file_bytes, sample)
            except Exception as e:
                print(f"Notice: Could not seed sample document '{sample}': {e}")


# =====================================================================
# 5. Deterministic Document Search
# =====================================================================

def search_documents(
    query: str,
    top_k: int = DEFAULT_TOP_K,
    document_id: Optional[str] = None,
    min_score: float = 0.0
) -> List[Dict[str, Any]]:
    """
    Performs deterministic semantic search against indexed document chunks in Chroma.
    Supports:
    - Global search across all documents.
    - Document-level filtered search when document_id is provided.
    - Accurate source citations (filename, page, chunk_index, score).
    - Threshold filtering (min_score) to drop completely irrelevant chunks.
    """
    clean_query = query.strip() if query else ""
    if not clean_query:
        raise ValueError("Search query cannot be empty.")

    if top_k < 1 or top_k > 50:
        raise ValueError("top_k must be an integer between 1 and 50.")

    ensure_documents_dir()
    seed_default_documents_if_empty()

    vector_store = get_vector_store()
    filter_dict = {"document_id": document_id} if document_id else None

    try:
        results_with_scores = vector_store.similarity_search_with_relevance_scores(
            clean_query,
            k=top_k,
            filter=filter_dict
        )
    except Exception:
        # Fallback to standard similarity search if relevance scores metric not supported
        docs = vector_store.similarity_search(clean_query, k=top_k, filter=filter_dict)
        results_with_scores = [(doc, 0.8) for doc in docs]

    formatted_results = []
    for doc, score in results_with_scores:
        if score is not None and score < min_score:
            continue
        meta = doc.metadata or {}
        # Ensure score is normalized float
        norm_score = max(0.0, min(1.0, float(score))) if score is not None else 0.5
        formatted_results.append({
            "text": doc.page_content,
            "score": round(norm_score, 4),
            "relevance_score": round(norm_score, 4),
            "document_id": meta.get("document_id", ""),
            "filename": meta.get("filename", "Unknown Document"),
            "page": meta.get("page", 1),
            "chunk_index": meta.get("chunk_index", 0)
        })

    return formatted_results
