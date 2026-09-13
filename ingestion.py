import os
import glob
import shutil
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

# Configuration paths
PROJECT_ROOT = os.path.dirname(__file__)
UPLOAD_DIR = os.path.join(PROJECT_ROOT, "uploads")
CHROMA_DB_DIR = os.path.join(PROJECT_ROOT, "chroma_db")

def ensure_directories():
    """Creates necessary directories and seeds initial sample documents if empty."""
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    os.makedirs(CHROMA_DB_DIR, exist_ok=True)

    # If uploads directory is empty, seed with sample PDFs from root if available
    existing_pdfs = glob.glob(os.path.join(UPLOAD_DIR, "*.pdf"))
    if not existing_pdfs:
        sample_pdfs = ["hr_employee_handbook.pdf", "it_security_policy.pdf", "sop_incident_response.pdf"]
        for sample in sample_pdfs:
            src = os.path.join(PROJECT_ROOT, sample)
            dst = os.path.join(UPLOAD_DIR, sample)
            if os.path.exists(src) and not os.path.exists(dst):
                shutil.copy2(src, dst)

def ingest_all_documents():
    """
    Finds all PDFs in the uploads directory, chunks them, and stores them in Chroma DB.
    Clears existing vector collection to ensure complete synchronization.
    """
    ensure_directories()
    embedding_model = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

    # Clear existing collection if present
    if os.path.exists(CHROMA_DB_DIR):
        try:
            old_store = Chroma(persist_directory=CHROMA_DB_DIR, embedding_function=embedding_model)
            old_store.delete_collection()
            old_store = None
        except Exception as e:
            pass

    pdf_files = glob.glob(os.path.join(UPLOAD_DIR, "*.pdf"))
    if not pdf_files:
        return None

    text_splitter = RecursiveCharacterTextSplitter(
        separators=["\n\n", "\n", " "],
        chunk_size=1000,
        chunk_overlap=200
    )

    all_chunks = []
    for file_path in pdf_files:
        try:
            loader = PyMuPDFLoader(file_path)
            documents = loader.load()
            chunks = text_splitter.split_documents(documents)
            all_chunks.extend(chunks)
        except Exception as e:
            print(f"Warning: Failed to load {file_path}: {e}")

    if all_chunks:
        vector_store = Chroma.from_documents(
            documents=all_chunks,
            embedding=embedding_model,
            persist_directory=CHROMA_DB_DIR
        )
        return vector_store
    return None

if __name__ == '__main__':
    ingest_all_documents()
