import os
import re
import json
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd

# Safe storage directory for uploaded structured datasets
DATASETS_DIR = os.path.join(os.path.dirname(__file__), "uploads", "datasets")
os.makedirs(DATASETS_DIR, exist_ok=True)

# Maximum allowed file size for upload (50 MB)
MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024
SUPPORTED_EXTENSIONS = {".csv", ".xlsx", ".xls"}

def sanitize_filename(filename: str) -> str:
    """Removes path traversal components and unsafe characters from a filename."""
    base = os.path.basename(filename)
    # Remove any dangerous characters except alphanumeric, dots, underscores, dashes
    cleaned = re.sub(r'[^a-zA-Z0-9_.-]', '_', base)
    return cleaned or "dataset"

def get_safe_dataset_path(dataset_id: str, ext: str) -> str:
    """Constructs an absolute path within the datasets directory preventing traversal."""
    safe_id = re.sub(r'[^a-zA-Z0-9-]', '', dataset_id)
    safe_ext = ext if ext.startswith('.') else f".{ext}"
    filename = f"{safe_id}{safe_ext}"
    full_path = os.path.abspath(os.path.join(DATASETS_DIR, filename))
    if not full_path.startswith(os.path.abspath(DATASETS_DIR)):
        raise ValueError("Invalid storage path: Path traversal detected.")
    return full_path

def get_meta_path(dataset_id: str) -> str:
    """Returns the metadata JSON path for a dataset ID."""
    safe_id = re.sub(r'[^a-zA-Z0-9-]', '', dataset_id)
    full_path = os.path.abspath(os.path.join(DATASETS_DIR, f"{safe_id}.meta.json"))
    if not full_path.startswith(os.path.abspath(DATASETS_DIR)):
        raise ValueError("Invalid metadata path: Path traversal detected.")
    return full_path

def to_json_serializable(val: Any) -> Any:
    """Recursively converts NumPy / Pandas data types into JSON-serializable Python types."""
    if val is None or pd.isna(val):
        return None
    if isinstance(val, (np.integer, int)):
        return int(val)
    if isinstance(val, (np.floating, float)):
        if np.isnan(val) or np.isinf(val):
            return None
        return float(val)
    if isinstance(val, (np.bool_, bool)):
        return bool(val)
    if isinstance(val, (pd.Timestamp, datetime)):
        return val.isoformat()
    if isinstance(val, (list, tuple)):
        return [to_json_serializable(x) for x in val]
    if isinstance(val, dict):
        return {str(k): to_json_serializable(v) for k, v in val.items()}
    return str(val)

def load_dataframe_from_file(filepath: str, ext: str) -> pd.DataFrame:
    """
    Loads a dataset from disk using Pandas.
    Supports CSV (with encoding fallbacks), XLSX (openpyxl), and XLS (xlrd).
    """
    ext = ext.lower()
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Dataset file not found at: {filepath}")

    if ext == ".csv":
        try:
            df = pd.read_csv(filepath, encoding="utf-8")
        except UnicodeDecodeError:
            df = pd.read_csv(filepath, encoding="latin1")
        except Exception as e:
            raise ValueError(f"Failed to parse CSV file: {str(e)}")
    elif ext == ".xlsx":
        try:
            df = pd.read_excel(filepath, engine="openpyxl")
        except Exception as e:
            raise ValueError(f"Failed to parse Excel (.xlsx) file: {str(e)}")
    elif ext == ".xls":
        try:
            df = pd.read_excel(filepath, engine="xlrd")
        except ImportError:
            raise ValueError("Reading legacy .xls files requires the 'xlrd' engine.")
        except Exception as e:
            raise ValueError(f"Failed to parse Excel (.xls) file: {str(e)}")
    else:
        raise ValueError(f"Unsupported file format: {ext}. Supported formats: {', '.join(SUPPORTED_EXTENSIONS)}")

    if df.empty and len(df.columns) == 0:
        raise ValueError("The uploaded dataset is completely empty (0 rows, 0 columns).")

    return df

def normalize_columns_for_analysis(df: pd.DataFrame) -> pd.DataFrame:
    """
    Returns an in-memory normalized copy of the DataFrame with trimmed and deduplicated headers.
    Original file on disk is NOT modified.
    """
    clean_df = df.copy()
    seen = {}
    new_cols = []
    for i, col in enumerate(clean_df.columns):
        c_str = str(col).strip()
        if not c_str or c_str.lower().startswith("unnamed"):
            c_str = f"column_{i+1}"
        if c_str in seen:
            seen[c_str] += 1
            c_str = f"{c_str}_{seen[c_str]}"
        else:
            seen[c_str] = 0
        new_cols.append(c_str)
    clean_df.columns = new_cols
    return clean_df

def detect_semantic_type(series: pd.Series) -> str:
    """
    Deterministically determines the semantic type of a Pandas series:
    'numeric', 'categorical', 'datetime', 'boolean', 'text', or 'unknown'.
    """
    if pd.api.types.is_bool_dtype(series):
        return "boolean"

    if pd.api.types.is_numeric_dtype(series):
        # Check if it behaves as a binary flag (0/1)
        non_null = series.dropna()
        if len(non_null) > 0 and set(non_null.unique()).issubset({0, 1}):
            return "boolean"
        return "numeric"

    if pd.api.types.is_datetime64_any_dtype(series):
        return "datetime"

    # For object/string columns, test for datetime if column name hints or values match
    col_name_lower = str(series.name).lower() if series.name else ""
    date_hints = ["date", "time", "timestamp", "year", "month", "day", "created", "updated"]
    non_null_samples = series.dropna().astype(str).head(15).tolist()

    if non_null_samples and (any(hint in col_name_lower for hint in date_hints)):
        try:
            # Test parsing a sample
            parsed = pd.to_datetime(non_null_samples, errors="coerce")
            if parsed.notna().sum() >= len(non_null_samples) * 0.8:
                return "datetime"
        except Exception:
            pass

    # Categorical vs Free Text
    total_non_null = series.dropna().shape[0]
    if total_non_null == 0:
        return "unknown"

    unique_count = series.nunique(dropna=True)
    uniqueness_ratio = unique_count / total_non_null

    # If few distinct values or low ratio, it's categorical
    if unique_count <= 50 or uniqueness_ratio < 0.25:
        return "categorical"

    return "text"

def calculate_data_quality_score(
    missing_percentage: float,
    duplicate_percentage: float,
    empty_columns: int,
    empty_rows: int,
    constant_columns: int
) -> float:
    """
    Authoritative InsightOS Deterministic Data Quality Health Score (0.0 to 100.0).

    Exact Mathematical Formula:
    Base Score: 100.0
    Deductions:
      1. Missing Data Penalty:
         - 0.4 points deducted per 1% of total cells missing
      2. Duplicate Rows Penalty:
         - 0.4 points deducted per 1% of duplicate rows
      3. Structural Defect Penalties:
         - Empty Columns: 5.0 points deducted per completely empty column
         - Empty Rows: 5.0 points deducted per completely empty row
         - Constant Columns: 2.0 points deducted per non-empty constant column

    Score is clamped between 0.0 and 100.0 and rounded to 1 decimal place.
    """
    deductions = (
        (missing_percentage * 0.4) +
        (duplicate_percentage * 0.4) +
        (empty_columns * 5.0) +
        (empty_rows * 5.0) +
        (constant_columns * 2.0)
    )
    return max(0.0, min(100.0, round(100.0 - deductions, 1)))

def calculate_dataset_profile(
    df: pd.DataFrame,
    dataset_id: str,
    original_filename: str,
    stored_filename: str,
    file_type: str,
    file_size: int
) -> Dict[str, Any]:
    """
    Generates a comprehensive, 100% deterministic dataset profile using Pandas.
    NO LLM hallucinations — all statistics and quality metrics are computed mathematically.
    """
    clean_df = normalize_columns_for_analysis(df)
    total_rows = int(len(clean_df))
    total_columns = int(len(clean_df.columns))

    # 1. Dataset Metadata
    metadata = {
        "dataset_id": dataset_id,
        "original_filename": original_filename,
        "stored_filename": stored_filename,
        "file_type": file_type,
        "file_size": file_size,
        "row_count": total_rows,
        "column_count": total_columns,
        "upload_timestamp": datetime.utcnow().isoformat() + "Z"
    }

    # 2. Data Quality Analysis
    missing_cells = int(clean_df.isna().sum().sum())
    total_cells = total_rows * total_columns if total_rows and total_columns else 1
    missing_percentage = round(float((missing_cells / total_cells) * 100), 2)
    
    cols_with_missing = [str(col) for col in clean_df.columns if clean_df[col].isna().sum() > 0]
    
    duplicate_rows = int(clean_df.duplicated().sum()) if total_rows > 0 else 0
    duplicate_percentage = round(float((duplicate_rows / total_rows) * 100), 2) if total_rows > 0 else 0.0

    empty_rows = int(clean_df.isna().all(axis=1).sum()) if total_rows > 0 else 0
    empty_columns = int(clean_df.isna().all(axis=0).sum()) if total_columns > 0 else 0
    
    # Constant columns: exactly 1 distinct value, excluding columns that are already 100% empty
    constant_columns = int(sum(
        (clean_df[col].nunique(dropna=True) == 1) and not clean_df[col].isna().all()
        for col in clean_df.columns
    ))

    # Overall Health Score (0.0 - 100.0)
    quality_score = calculate_data_quality_score(
        missing_percentage=missing_percentage,
        duplicate_percentage=duplicate_percentage,
        empty_columns=empty_columns,
        empty_rows=empty_rows,
        constant_columns=constant_columns
    )

    quality = {
        "score": quality_score,
        "missing_cells": missing_cells,
        "missing_percentage": missing_percentage,
        "columns_with_missing": cols_with_missing,
        "columns_with_missing_count": len(cols_with_missing),
        "duplicate_rows": duplicate_rows,
        "duplicate_percentage": duplicate_percentage,
        "empty_rows": empty_rows,
        "empty_columns": empty_columns,
        "constant_columns": constant_columns
    }

    # 3. Column Profiles & Statistics
    columns_profile = []
    numeric_stats = {}

    for col in clean_df.columns:
        series = clean_df[col]
        null_count = int(series.isna().sum())
        null_pct = round(float((null_count / total_rows) * 100), 2) if total_rows > 0 else 0.0
        unique_count = int(series.nunique(dropna=True))
        semantic_type = detect_semantic_type(series)

        # Sample values (up to 5 non-null items)
        samples = [to_json_serializable(x) for x in series.dropna().head(5).tolist()]

        col_info: Dict[str, Any] = {
            "name": str(col),
            "pandas_dtype": str(series.dtype),
            "semantic_type": semantic_type,
            "null_count": null_count,
            "null_percentage": null_pct,
            "unique_count": unique_count,
            "sample_values": samples
        }

        # Numeric Statistics
        if semantic_type == "numeric":
            num_series = pd.to_numeric(series, errors="coerce").dropna()
            if not num_series.empty:
                col_stats = {
                    "min": to_json_serializable(num_series.min()),
                    "max": to_json_serializable(num_series.max()),
                    "mean": round(float(num_series.mean()), 4),
                    "median": round(float(num_series.median()), 4),
                    "std": round(float(num_series.std()), 4) if len(num_series) > 1 else 0.0,
                    "q25": round(float(num_series.quantile(0.25)), 4) if len(num_series) > 1 else None,
                    "q75": round(float(num_series.quantile(0.75)), 4) if len(num_series) > 1 else None
                }
                col_info["numeric_stats"] = col_stats
                numeric_stats[str(col)] = col_stats

        # Categorical Statistics
        elif semantic_type in ("categorical", "boolean", "text"):
            val_counts = series.dropna().value_counts().head(5)
            col_info["top_values"] = [
                {"value": to_json_serializable(k), "count": int(v)}
                for k, v in val_counts.items()
            ]

        # Datetime Statistics
        elif semantic_type == "datetime":
            try:
                date_series = pd.to_datetime(series, errors="coerce").dropna()
                if not date_series.empty:
                    min_date = date_series.min()
                    max_date = date_series.max()
                    days = (max_date - min_date).days
                    col_info["datetime_stats"] = {
                        "min_date": min_date.isoformat(),
                        "max_date": max_date.isoformat(),
                        "range_days": int(days)
                    }
            except Exception:
                pass

        columns_profile.append(col_info)

    return {
        "dataset": metadata,
        "quality": quality,
        "columns": columns_profile,
        "numeric_statistics": numeric_stats
    }

def save_uploaded_dataset(file_obj, original_filename: str) -> Dict[str, Any]:
    """
    Saves an uploaded file to uploads/datasets/ and generates its initial profile.
    Returns the complete profile dictionary.
    """
    safe_name = sanitize_filename(original_filename)
    ext = os.path.splitext(safe_name)[1].lower()

    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file format '{ext}'. InsightOS supports: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )

    dataset_id = str(uuid.uuid4())
    stored_path = get_safe_dataset_path(dataset_id, ext)

    # Save to disk
    file_size = 0
    with open(stored_path, "wb+") as f:
        while chunk := file_obj.read(1024 * 1024): # 1MB chunks
            file_size += len(chunk)
            if file_size > MAX_FILE_SIZE_BYTES:
                os.remove(stored_path)
                raise ValueError(f"File size exceeds maximum allowed limit of {MAX_FILE_SIZE_BYTES // (1024*1024)} MB.")
            f.write(chunk)

    try:
        df = load_dataframe_from_file(stored_path, ext)
        profile = calculate_dataset_profile(
            df=df,
            dataset_id=dataset_id,
            original_filename=safe_name,
            stored_filename=os.path.basename(stored_path),
            file_type=ext.replace(".", ""),
            file_size=file_size
        )

        # Save metadata JSON
        meta_path = get_meta_path(dataset_id)
        with open(meta_path, "w", encoding="utf-8") as meta_file:
            json.dump(profile, meta_file, indent=2)

        return profile

    except Exception as e:
        # Clean up disk file on failure
        if os.path.exists(stored_path):
            os.remove(stored_path)
        raise e

def list_all_datasets() -> List[Dict[str, Any]]:
    """Returns a list of metadata for all uploaded datasets."""
    datasets = []
    if not os.path.exists(DATASETS_DIR):
        return datasets

    for f in os.listdir(DATASETS_DIR):
        if f.endswith(".meta.json"):
            meta_path = os.path.join(DATASETS_DIR, f)
            try:
                with open(meta_path, "r", encoding="utf-8") as mf:
                    data = json.load(mf)
                    if "dataset" in data:
                        # Include key summary fields for fast listing
                        datasets.append({
                            **data["dataset"],
                            "quality_score": data.get("quality", {}).get("score", 100),
                            "missing_percentage": data.get("quality", {}).get("missing_percentage", 0.0)
                        })
            except Exception:
                continue

    # Sort descending by upload timestamp
    datasets.sort(key=lambda x: x.get("upload_timestamp", ""), reverse=True)
    return datasets

def get_dataset_profile_by_id(dataset_id: str) -> Dict[str, Any]:
    """Retrieves full profile for a given dataset ID."""
    meta_path = get_meta_path(dataset_id)
    if not os.path.exists(meta_path):
        raise FileNotFoundError(f"Dataset profile '{dataset_id}' not found.")

    with open(meta_path, "r", encoding="utf-8") as mf:
        return json.load(mf)

def get_dataset_preview(dataset_id: str, limit: int = 20) -> Dict[str, Any]:
    """
    Returns a safe JSON-serializable preview of the dataset (first `limit` rows).
    Does NOT leak local filesystem paths.
    """
    profile = get_dataset_profile_by_id(dataset_id)
    dataset_meta = profile["dataset"]
    ext = f".{dataset_meta['file_type']}"
    stored_path = get_safe_dataset_path(dataset_id, ext)

    df = load_dataframe_from_file(stored_path, ext)
    clean_df = normalize_columns_for_analysis(df)

    preview_df = clean_df.head(min(limit, 100))
    rows = []
    for record in preview_df.to_dict(orient="records"):
        rows.append({str(k): to_json_serializable(v) for k, v in record.items()})

    return {
        "dataset_id": dataset_id,
        "original_filename": dataset_meta["original_filename"],
        "columns": list(clean_df.columns),
        "total_rows": int(len(clean_df)),
        "total_columns": int(len(clean_df.columns)),
        "preview_rows": rows
    }

def delete_dataset_by_id(dataset_id: str) -> bool:
    """Safely deletes a dataset file and its metadata from disk."""
    meta_path = get_meta_path(dataset_id)
    if os.path.exists(meta_path):
        try:
            with open(meta_path, "r", encoding="utf-8") as mf:
                data = json.load(mf)
                ext = f".{data.get('dataset', {}).get('file_type', 'csv')}"
                stored_path = get_safe_dataset_path(dataset_id, ext)
                if os.path.exists(stored_path):
                    os.remove(stored_path)
            os.remove(meta_path)
            return True
        except Exception as e:
            if os.path.exists(meta_path):
                os.remove(meta_path)
            return True
    return False
