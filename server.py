import os
import shutil
from typing import Optional
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from router import main_chat_interface
from knowledge_service import (
    index_document,
    delete_document as delete_knowledge_document,
    list_documents as list_knowledge_documents,
    search_documents as search_knowledge_documents,
    get_document as get_knowledge_document
)
from dataset_service import (
    save_uploaded_dataset,
    list_all_datasets,
    get_dataset_profile_by_id,
    get_dataset_preview,
    delete_dataset_by_id,
    SUPPORTED_EXTENSIONS
)
from data_brain import (
    DataBrainError,
    get_dataset_summary,
    get_numeric_statistics,
    aggregate_by_category,
    get_top_categories,
    get_bottom_categories,
    get_time_trend,
    get_kpis,
    detect_anomalies,
    forecast_metric
)

app = FastAPI(title="InsightOS Core API", version="0.3.0")

# Allow local frontend development servers and production Vercel frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://insight-os-taupe.vercel.app"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

class ChatRequest(BaseModel):
    query: str
    api_key: str = ""
    dataset_id: Optional[str] = None
    document_id: Optional[str] = None

class SyncRequest(BaseModel):
    url: str

class AggregateRequest(BaseModel):
    category_column: str
    metric_column: str
    aggregation: str = "sum"

class CategoryRankRequest(BaseModel):
    category_column: str
    metric_column: str
    aggregation: str = "sum"
    limit: int = Field(default=10, ge=1, le=100)

class TrendRequest(BaseModel):
    date_column: str
    metric_column: str
    aggregation: str = "sum"
    frequency: str = "auto"

class DocumentSearchRequest(BaseModel):
    query: str
    top_k: int = Field(default=5, ge=1, le=50)
    document_id: Optional[str] = None

class AnomalyRequest(BaseModel):
    metric_column: str
    date_column: Optional[str] = None
    dimension_column: Optional[str] = None
    limit: int = Field(default=20, ge=1, le=1000)

class ForecastRequest(BaseModel):
    metric_column: str
    date_column: str
    periods: int = Field(default=3, ge=1, le=24)
    frequency: Optional[str] = None

@app.get("/api/health")
async def health_check():
    return {
        "status": "ok",
        "service": "InsightOS Core API",
        "supported_datasets": sorted(list(SUPPORTED_EXTENSIONS))
    }

# ==========================================
# Chat & Hybrid Orchestration Endpoints
# ==========================================

@app.post("/api/chat")
async def chat(request: ChatRequest):
    """
    Chat endpoint routing queries through InsightOS Reasoning Brain.
    API key is passed explicitly down the stack; no process-wide environment mutation.
    """
    try:
        response = main_chat_interface(
            request.query,
            api_key=request.api_key,
            dataset_id=request.dataset_id,
            document_id=request.document_id
        )
        return {"status": "success", "response": response}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ==========================================
# Document / Knowledge Brain Endpoints (InsightOS Knowledge Brain)
# ==========================================

@app.post("/api/documents/upload")
@app.post("/api/upload")
async def upload_document(file: UploadFile = File(...)):
    """
    Handles PDF document uploads.
    Validates file format and size, stores in uploads/documents/,
    extracts pages, chunks deterministically, and indexes incrementally into Chroma.
    Supports duplicate detection via SHA-256 hash.
    """
    try:
        doc_metadata = index_document(file.file, file.filename)
        return {
            "status": "success",
            "message": f"Successfully processed and indexed {file.filename}",
            "document": doc_metadata,
            "id": doc_metadata["document_id"],
            "name": doc_metadata["filename"]
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Document processing failed: {str(e)}")


@app.get("/api/documents")
async def get_documents():
    """
    Returns a list of all indexed documents in the Knowledge Brain.
    Preserves both modern and legacy frontend keys ('documents' and 'files').
    """
    try:
        docs = list_knowledge_documents()
        formatted_files = []
        for d in docs:
            file_size = d.get("size", d.get("file_size_bytes", 0))
            formatted_files.append({
                **d,
                "id": d.get("document_id", ""),
                "name": d.get("filename", ""),
                "size": file_size,
                "file_size_bytes": file_size,
                "type": "application/pdf"
            })
        return {
            "status": "success",
            "documents": formatted_files,
            "files": formatted_files
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list documents: {str(e)}")


@app.delete("/api/documents/{doc_id_or_name}")
async def delete_document(doc_id_or_name: str):
    """
    Deletes a document from the Knowledge Brain.
    Removes vectors incrementally from Chroma without wiping other documents,
    and removes file from disk and metadata index.
    Accepts document_id (UUID) or original filename.
    """
    success = delete_knowledge_document(doc_id_or_name)
    if not success:
        raise HTTPException(status_code=404, detail=f"Document '{doc_id_or_name}' not found")
    return {
        "status": "success",
        "message": f"Successfully removed document '{doc_id_or_name}'"
    }


@app.post("/api/documents/search")
async def search_documents_endpoint(request: DocumentSearchRequest):
    """
    Performs semantic search across the Knowledge Brain vector store.
    Returns ranked chunks with relevance scores, page numbers, and source metadata.
    Supports optional document_id filtering.
    """
    try:
        results = search_knowledge_documents(
            query=request.query,
            top_k=request.top_k,
            document_id=request.document_id
        )
        return {
            "status": "success",
            "query": request.query,
            "results_count": len(results),
            "results": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Document search failed: {str(e)}")

# ==========================================
# Structured Dataset Endpoints (InsightOS Data Brain)
# ==========================================

@app.post("/api/datasets/upload")
async def upload_dataset(file: UploadFile = File(...)):
    """
    Accepts CSV, XLSX, and XLS structured datasets.
    Saves file to uploads/datasets/ and generates deterministic profile & quality metrics.
    """
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format '{ext}'. Supported formats: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )

    try:
        profile = save_uploaded_dataset(file.file, file.filename)
        return {
            "status": "success",
            "message": f"Successfully ingested and profiled '{file.filename}'",
            "dataset": profile["dataset"],
            "quality": profile["quality"],
            "columns": profile["columns"],
            "numeric_statistics": profile.get("numeric_statistics", {})
        }
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Dataset processing error: {str(e)}")

@app.get("/api/datasets")
async def get_all_datasets():
    """Returns metadata for all uploaded structured datasets."""
    datasets = list_all_datasets()
    return {"status": "success", "datasets": datasets}

@app.get("/api/datasets/{dataset_id}/profile")
async def get_dataset_profile(dataset_id: str):
    """Returns the full deterministic profile and quality metrics for a dataset."""
    try:
        profile = get_dataset_profile_by_id(dataset_id)
        return {"status": "success", "profile": profile}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Dataset '{dataset_id}' not found.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/datasets/{dataset_id}/preview")
async def get_preview(dataset_id: str, limit: int = 20):
    """Returns a safe row preview (first 10-20 rows) for a dataset."""
    try:
        preview = get_dataset_preview(dataset_id, limit=limit)
        return {"status": "success", "preview": preview}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Dataset '{dataset_id}' not found.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/datasets/{dataset_id}")
async def delete_dataset(dataset_id: str):
    """Deletes a dataset and its profile metadata."""
    success = delete_dataset_by_id(dataset_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Dataset '{dataset_id}' not found.")
    return {"status": "success", "message": f"Successfully deleted dataset {dataset_id}"}

# ==========================================
# InsightOS Safe Data Brain Analytics Endpoints
# ==========================================

def _format_error_response(e: Exception):
    if isinstance(e, DataBrainError):
        status_code = 404 if e.code == "DATASET_NOT_FOUND" else 400
        return JSONResponse(
            status_code=status_code,
            content={
                "status": "error",
                "error": {
                    "code": e.code,
                    "message": e.message
                }
            }
        )
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": str(e)
            }
        }
    )

@app.get("/api/datasets/{dataset_id}/summary")
async def get_summary(dataset_id: str):
    """Returns structural and semantic summary of dataset from Data Brain."""
    try:
        summary = get_dataset_summary(dataset_id)
        return {"status": "success", "dataset_id": dataset_id, "result": summary}
    except Exception as e:
        return _format_error_response(e)

@app.get("/api/datasets/{dataset_id}/statistics/{column}")
async def get_statistics(dataset_id: str, column: str):
    """Calculates deterministic descriptive statistics for a numeric column."""
    try:
        stats = get_numeric_statistics(dataset_id, column)
        return {"status": "success", "dataset_id": dataset_id, "result": stats}
    except Exception as e:
        return _format_error_response(e)

@app.post("/api/datasets/{dataset_id}/aggregate")
async def aggregate(dataset_id: str, request: AggregateRequest):
    """Groups dataset by category and aggregates numeric metric."""
    try:
        results = aggregate_by_category(
            dataset_id,
            request.category_column,
            request.metric_column,
            aggregation=request.aggregation
        )
        return {"status": "success", "dataset_id": dataset_id, "result": results}
    except Exception as e:
        return _format_error_response(e)

@app.post("/api/datasets/{dataset_id}/top")
async def top_categories(dataset_id: str, request: CategoryRankRequest):
    """Returns top performing categories sorted descending."""
    try:
        top_data = get_top_categories(
            dataset_id,
            request.category_column,
            request.metric_column,
            aggregation=request.aggregation,
            limit=request.limit
        )
        return {"status": "success", "dataset_id": dataset_id, "result": top_data}
    except Exception as e:
        return _format_error_response(e)

@app.post("/api/datasets/{dataset_id}/bottom")
async def bottom_categories(dataset_id: str, request: CategoryRankRequest):
    """Returns lowest performing categories sorted ascending."""
    try:
        bottom_data = get_bottom_categories(
            dataset_id,
            request.category_column,
            request.metric_column,
            aggregation=request.aggregation,
            limit=request.limit
        )
        return {"status": "success", "dataset_id": dataset_id, "result": bottom_data}
    except Exception as e:
        return _format_error_response(e)

@app.post("/api/datasets/{dataset_id}/trend")
async def time_trend(dataset_id: str, request: TrendRequest):
    """Calculates deterministic time trend over a date column."""
    try:
        trend = get_time_trend(
            dataset_id,
            request.date_column,
            request.metric_column,
            aggregation=request.aggregation,
            frequency=request.frequency
        )
        return {"status": "success", "dataset_id": dataset_id, "result": trend}
    except Exception as e:
        return _format_error_response(e)

@app.get("/api/datasets/{dataset_id}/kpis")
async def dataset_kpis(dataset_id: str):
    """Computes deterministic business KPIs for suitable numeric columns."""
    try:
        kpis = get_kpis(dataset_id)
        return {"status": "success", "dataset_id": dataset_id, "result": kpis}
    except Exception as e:
        return _format_error_response(e)

@app.post("/api/datasets/{dataset_id}/anomalies")
async def detect_dataset_anomalies_post(dataset_id: str, request: AnomalyRequest):
    """Detects statistical outliers/anomalies in a numeric column via IQR (POST)."""
    try:
        results = detect_anomalies(
            dataset_id,
            metric_column=request.metric_column,
            date_column=request.date_column,
            dimension_column=request.dimension_column,
            limit=request.limit
        )
        return {"status": "success", "dataset_id": dataset_id, "result": results}
    except Exception as e:
        return _format_error_response(e)

@app.get("/api/datasets/{dataset_id}/anomalies")
async def detect_dataset_anomalies_get(
    dataset_id: str,
    metric_column: str,
    date_column: Optional[str] = None,
    dimension_column: Optional[str] = None,
    limit: int = 20
):
    """Detects statistical outliers/anomalies in a numeric column via IQR (GET)."""
    try:
        results = detect_anomalies(
            dataset_id,
            metric_column=metric_column,
            date_column=date_column,
            dimension_column=dimension_column,
            limit=limit
        )
        return {"status": "success", "dataset_id": dataset_id, "result": results}
    except Exception as e:
        return _format_error_response(e)

@app.post("/api/datasets/{dataset_id}/forecast")
async def forecast_dataset_metric_post(dataset_id: str, request: ForecastRequest):
    """Generates deterministic time-series forecast for a numeric column (POST)."""
    try:
        results = forecast_metric(
            dataset_id,
            metric_column=request.metric_column,
            date_column=request.date_column,
            periods=request.periods,
            frequency=request.frequency
        )
        return {"status": "success", "dataset_id": dataset_id, "result": results}
    except Exception as e:
        return _format_error_response(e)

@app.get("/api/datasets/{dataset_id}/forecast")
async def forecast_dataset_metric_get(
    dataset_id: str,
    metric_column: str,
    date_column: str,
    periods: int = 3,
    frequency: Optional[str] = None
):
    """Generates deterministic time-series forecast for a numeric column (GET)."""
    try:
        results = forecast_metric(
            dataset_id,
            metric_column=metric_column,
            date_column=date_column,
            periods=periods,
            frequency=frequency
        )
        return {"status": "success", "dataset_id": dataset_id, "result": results}
    except Exception as e:
        return _format_error_response(e)

# ==========================================
# Legacy Stub
# ==========================================

@app.post("/api/sync")
async def sync_data(request: SyncRequest):
    """Legacy compatibility endpoint."""
    return {"status": "info", "message": "External live syncing archived to legacy for MVP."}
