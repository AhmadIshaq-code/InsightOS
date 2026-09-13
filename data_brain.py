import os
import re
from typing import Dict, Any, List, Optional, Tuple, Union
import numpy as np
import pandas as pd

from dataset_service import (
    get_dataset_profile_by_id,
    get_safe_dataset_path,
    load_dataframe_from_file,
    normalize_columns_for_analysis,
    to_json_serializable
)

"""
INSIGHTOS DATA BRAIN
====================
Deterministic, safe, and authoritative business analytics engine for InsightOS.

SECURITY GUARANTEES:
- Zero arbitrary code execution (no eval, no exec, no LangChain Python REPL, no unsafe execution permissions).
- Controlled Pandas operations with strict column, datatype, and boundary validations.
- Path traversal prevention via dataset_service.
- Clean application-level error codes without raw stack trace leakage.
"""

class DataBrainError(Exception):
    """Structured error raised by Data Brain with machine-readable error codes."""
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


# =====================================================================
# 1. Safe Dataset & Column Validation Helpers
# =====================================================================

def require_dataset(dataset_id: str) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Safely loads a dataset by ID through the dataset_service.
    Returns (clean_dataframe, profile_metadata).
    Raises DataBrainError if dataset does not exist or cannot be read.
    """
    try:
        profile = get_dataset_profile_by_id(dataset_id)
    except FileNotFoundError:
        raise DataBrainError(
            "DATASET_NOT_FOUND",
            f"Dataset '{dataset_id}' was not found in storage."
        )
    except Exception as e:
        raise DataBrainError(
            "DATASET_LOAD_ERROR",
            f"Failed to retrieve metadata for dataset '{dataset_id}': {str(e)}"
        )

    dataset_meta = profile.get("dataset", {})
    file_type = dataset_meta.get("file_type", "csv")
    ext = f".{file_type}"
    try:
        stored_path = get_safe_dataset_path(dataset_id, ext)
        raw_df = load_dataframe_from_file(stored_path, ext)
        clean_df = normalize_columns_for_analysis(raw_df)
        return clean_df, profile
    except Exception as e:
        raise DataBrainError(
            "DATASET_READ_ERROR",
            f"Failed to read dataset file '{dataset_id}': {str(e)}"
        )

def require_column(df: pd.DataFrame, column: str) -> str:
    """
    Ensures that a specified column exists in the DataFrame.
    Returns the valid column name or raises DataBrainError.
    """
    if column not in df.columns:
        # Case-insensitive fallback check for user convenience
        match = next((c for c in df.columns if c.lower() == column.lower()), None)
        if match:
            return match
        raise DataBrainError(
            "INVALID_COLUMN",
            f"Column '{column}' does not exist in dataset. Available columns: {list(df.columns)}"
        )
    return column

def require_numeric_column(df: pd.DataFrame, column: str) -> Tuple[str, pd.Series]:
    """
    Validates that a column exists and is numeric (or safely coercible to numeric).
    Returns (column_name, numeric_series).
    """
    col_name = require_column(df, column)
    series = df[col_name]

    if pd.api.types.is_numeric_dtype(series):
        return col_name, pd.to_numeric(series, errors="coerce")

    # If dtype is object/string, attempt safe numeric conversion if a majority of values convert
    coerced = pd.to_numeric(series, errors="coerce")
    non_null_original = series.dropna()
    valid_converted = coerced.dropna()

    if len(non_null_original) > 0 and (len(valid_converted) / len(non_null_original)) >= 0.7:
        return col_name, coerced

    raise DataBrainError(
        "NON_NUMERIC_COLUMN",
        f"Column '{col_name}' is not numeric (type: {series.dtype}). Numeric calculations cannot be performed."
    )

def require_datetime_column(df: pd.DataFrame, column: str) -> Tuple[str, pd.Series]:
    """
    Validates that a column exists and contains valid datetime entries.
    Returns (column_name, datetime_series).
    """
    col_name = require_column(df, column)
    series = df[col_name]

    if pd.api.types.is_datetime64_any_dtype(series):
        return col_name, series

    try:
        dt_series = pd.to_datetime(series, errors="coerce")
        if dt_series.dropna().empty and not series.dropna().empty:
            raise ValueError()
        return col_name, dt_series
    except Exception:
        raise DataBrainError(
            "INVALID_DATETIME_COLUMN",
            f"Column '{col_name}' could not be parsed as a datetime series."
        )

def is_likely_identifier_column(series: pd.Series, col_name: str) -> bool:
    """
    Heuristic to detect likely identifier/index columns that should be excluded
    from business KPI calculations (e.g. Employee_ID, TransactionID, RowNum).

    CRITERIA:
    1. Name matching regex:
       - Starts with 'id_' or 'id' + uppercase
       - Ends with '_id' or 'id'
       - Equals 'id', 'guid', 'uuid', 'code', 'index', 'row_num', 'pk'
    2. High cardinality integer sequences:
       - 100% unique non-null integers where count > 3
       - Monotonically increasing sequence (e.g. 1, 2, 3... or 1001, 1002...)
    """
    lower_col = col_name.strip().lower()

    # Rule 1: Name patterns
    name_patterns = [
        r"^id$",
        r"^id[_\s]",
        r"[_\s]id$",
        r"identifier",
        r"uuid",
        r"guid",
        r"^pk$",
        r"index",
        r"row[_\s]?num"
    ]
    for pattern in name_patterns:
        if re.search(pattern, lower_col):
            return True

    # Rule 2: Uniqueness and integer sequence heuristics
    clean_series = series.dropna()
    total_count = len(clean_series)
    if total_count >= 5 and pd.api.types.is_integer_dtype(series):
        unique_count = clean_series.nunique()
        if unique_count == total_count:
            # Check if sorted sequence has constant difference of 1
            sorted_vals = clean_series.sort_values().values
            diffs = np.diff(sorted_vals)
            if np.all(diffs == 1):
                return True

    return False


# =====================================================================
# 2. Core Controlled Analytics Functions
# =====================================================================

def get_dataset_summary(dataset_id: str) -> Dict[str, Any]:
    """
    Returns high-level structural and semantic summary of an uploaded dataset.
    Reuses existing deterministic profiling metadata.
    """
    df, profile = require_dataset(dataset_id)
    quality = profile.get("quality", {})
    columns_meta = profile.get("columns", [])

    numeric_cols = []
    categorical_cols = []
    datetime_cols = []
    text_cols = []

    for c in columns_meta:
        c_name = c["name"]
        s_type = c.get("semantic_type", "text")
        if s_type == "numeric":
            numeric_cols.append(c_name)
        elif s_type == "categorical":
            categorical_cols.append(c_name)
        elif s_type == "datetime":
            datetime_cols.append(c_name)
        else:
            text_cols.append(c_name)

    return {
        "dataset_id": dataset_id,
        "original_filename": profile.get("dataset", {}).get("original_filename", ""),
        "row_count": int(len(df)),
        "column_count": int(len(df.columns)),
        "columns": list(df.columns),
        "numeric_columns": numeric_cols,
        "categorical_columns": categorical_cols,
        "datetime_columns": datetime_cols,
        "text_columns": text_cols,
        "missing_cells": int(quality.get("missing_cells", 0)),
        "missing_percentage": float(quality.get("missing_percentage", 0.0)),
        "duplicate_rows": int(quality.get("duplicate_rows", 0)),
        "duplicate_percentage": float(quality.get("duplicate_percentage", 0.0)),
        "quality_score": float(quality.get("score", 100.0))
    }


def get_numeric_statistics(dataset_id: str, column: str) -> Dict[str, Any]:
    """
    Calculates deterministic descriptive statistics for a specified numeric column.
    """
    df, _ = require_dataset(dataset_id)
    col_name, series = require_numeric_column(df, column)

    clean_vals = series.dropna()
    total_count = int(len(clean_vals))
    missing_count = int(series.isna().sum())

    if total_count == 0:
        return {
            "column": col_name,
            "count": 0,
            "missing": missing_count,
            "min": None,
            "max": None,
            "mean": None,
            "median": None,
            "standard_deviation": None,
            "sum": 0.0
        }

    return {
        "column": col_name,
        "count": total_count,
        "missing": missing_count,
        "min": to_json_serializable(clean_vals.min()),
        "max": to_json_serializable(clean_vals.max()),
        "mean": round(float(clean_vals.mean()), 4),
        "median": to_json_serializable(clean_vals.median()),
        "standard_deviation": round(float(clean_vals.std()), 4) if total_count > 1 else 0.0,
        "sum": to_json_serializable(clean_vals.sum())
    }


def aggregate_by_category(
    dataset_id: str,
    category_column: str,
    metric_column: str,
    aggregation: str = "sum"
) -> List[Dict[str, Any]]:
    """
    Groups data by a category column and aggregates a metric column.
    Supported aggregations: 'sum', 'mean', 'count', 'min', 'max'.
    """
    df, _ = require_dataset(dataset_id)
    cat_col = require_column(df, category_column)
    agg_op = aggregation.lower().strip()

    valid_aggs = {"sum", "mean", "count", "min", "max"}
    if agg_op not in valid_aggs:
        raise DataBrainError(
            "INVALID_AGGREGATION",
            f"Unsupported aggregation '{aggregation}'. Supported aggregations: {sorted(list(valid_aggs))}"
        )

    if agg_op == "count":
        # Metric column can be any existing column for counting
        met_col = require_column(df, metric_column) if metric_column else cat_col
        grouped = df.groupby(cat_col, dropna=False)[met_col].count()
    else:
        met_col, num_series = require_numeric_column(df, metric_column)
        temp_df = pd.DataFrame({cat_col: df[cat_col], met_col: num_series})
        if agg_op == "sum":
            grouped = temp_df.groupby(cat_col, dropna=False)[met_col].sum()
        elif agg_op == "mean":
            grouped = temp_df.groupby(cat_col, dropna=False)[met_col].mean().round(4)
        elif agg_op == "min":
            grouped = temp_df.groupby(cat_col, dropna=False)[met_col].min()
        elif agg_op == "max":
            grouped = temp_df.groupby(cat_col, dropna=False)[met_col].max()

    results = []
    for cat_val, val in grouped.items():
        label = "Unknown / Missing" if pd.isna(cat_val) else str(cat_val)
        results.append({
            "category": label,
            "value": to_json_serializable(val)
        })

    return results


def get_top_categories(
    dataset_id: str,
    category_column: str,
    metric_column: str,
    aggregation: str = "sum",
    limit: int = 10
) -> Dict[str, Any]:
    """
    Calculates top performing categories sorted descending by aggregated value.
    """
    if limit < 1 or limit > 100:
        raise DataBrainError("INVALID_LIMIT", "Limit must be an integer between 1 and 100.")

    items = aggregate_by_category(dataset_id, category_column, metric_column, aggregation)
    # Sort descending by value (nulls last)
    items.sort(key=lambda x: (x["value"] is not None, x["value"]), reverse=True)
    top_items = items[:limit]

    return {
        "category_column": category_column,
        "metric_column": metric_column,
        "aggregation": aggregation,
        "limit": limit,
        "items": top_items
    }


def get_bottom_categories(
    dataset_id: str,
    category_column: str,
    metric_column: str,
    aggregation: str = "sum",
    limit: int = 10
) -> Dict[str, Any]:
    """
    Calculates lowest performing categories sorted ascending by aggregated value.
    """
    if limit < 1 or limit > 100:
        raise DataBrainError("INVALID_LIMIT", "Limit must be an integer between 1 and 100.")

    items = aggregate_by_category(dataset_id, category_column, metric_column, aggregation)
    # Filter out None values for sensible bottom sorting
    valid_items = [it for it in items if it["value"] is not None]
    valid_items.sort(key=lambda x: x["value"], reverse=False)
    bottom_items = valid_items[:limit]

    return {
        "category_column": category_column,
        "metric_column": metric_column,
        "aggregation": aggregation,
        "limit": limit,
        "items": bottom_items
    }


def get_time_trend(
    dataset_id: str,
    date_column: str,
    metric_column: str,
    aggregation: str = "sum",
    frequency: str = "auto"
) -> Dict[str, Any]:
    """
    Calculates deterministic time-series trends over a date column.
    Supports auto frequency detection or explicit: 'day', 'week', 'month', 'quarter', 'year'.
    """
    df, _ = require_dataset(dataset_id)
    dt_col, dt_series = require_datetime_column(df, date_column)
    agg_op = aggregation.lower().strip()

    valid_aggs = {"sum", "mean", "count", "min", "max"}
    if agg_op not in valid_aggs:
        raise DataBrainError(
            "INVALID_AGGREGATION",
            f"Unsupported aggregation '{aggregation}'. Supported aggregations: {sorted(list(valid_aggs))}"
        )

    if agg_op == "count":
        met_col = require_column(df, metric_column) if metric_column else dt_col
        val_series = df[met_col]
    else:
        met_col, val_series = require_numeric_column(df, metric_column)

    # Filter rows with valid dates
    valid_mask = dt_series.notna()
    if not valid_mask.any():
        raise DataBrainError(
            "NO_VALID_DATES",
            f"Column '{dt_col}' contains no valid datetime entries."
        )

    clean_dates = dt_series[valid_mask]
    clean_vals = val_series[valid_mask]

    min_date = clean_dates.min()
    max_date = clean_dates.max()
    span_days = (max_date - min_date).days

    freq = frequency.lower().strip()
    valid_freqs = {"auto", "day", "daily", "week", "weekly", "month", "monthly", "quarter", "quarterly", "year", "yearly"}

    if freq not in valid_freqs:
        raise DataBrainError(
            "INVALID_FREQUENCY",
            f"Unsupported frequency '{frequency}'. Supported: 'auto', 'day', 'week', 'month', 'quarter', 'year'."
        )

    if freq == "auto":
        if span_days <= 31:
            chosen_freq = "day"
        elif span_days <= 180:
            chosen_freq = "week"
        elif span_days <= 730:
            chosen_freq = "month"
        elif span_days <= 1825:
            chosen_freq = "quarter"
        else:
            chosen_freq = "year"
    else:
        # Normalize alias
        alias_map = {"daily": "day", "weekly": "week", "monthly": "month", "quarterly": "quarter", "yearly": "year"}
        chosen_freq = alias_map.get(freq, freq)

    trend_df = pd.DataFrame({"datetime": clean_dates, "metric": clean_vals})
    trend_df = trend_df.sort_values("datetime")

    # Group by period
    if chosen_freq == "month":
        trend_df["period"] = trend_df["datetime"].dt.strftime("%Y-%m")
    elif chosen_freq == "day":
        trend_df["period"] = trend_df["datetime"].dt.strftime("%Y-%m-%d")
    elif chosen_freq == "year":
        trend_df["period"] = trend_df["datetime"].dt.strftime("%Y")
    elif chosen_freq == "quarter":
        trend_df["period"] = trend_df["datetime"].apply(lambda d: f"{d.year}-Q{d.quarter}")
    elif chosen_freq == "week":
        trend_df["period"] = trend_df["datetime"].apply(lambda d: f"{d.year}-W{d.isocalendar().week:02d}")

    if agg_op == "sum":
        grouped = trend_df.groupby("period", sort=True)["metric"].sum()
    elif agg_op == "mean":
        grouped = trend_df.groupby("period", sort=True)["metric"].mean().round(4)
    elif agg_op == "min":
        grouped = trend_df.groupby("period", sort=True)["metric"].min()
    elif agg_op == "max":
        grouped = trend_df.groupby("period", sort=True)["metric"].max()
    elif agg_op == "count":
        grouped = trend_df.groupby("period", sort=True)["metric"].count()

    trend_data = []
    for period_str, val in grouped.items():
        trend_data.append({
            "period": period_str,
            "value": to_json_serializable(val)
        })

    return {
        "metadata": {
            "date_column": dt_col,
            "metric_column": met_col,
            "aggregation": agg_op,
            "frequency": chosen_freq,
            "date_range": {
                "min": min_date.isoformat(),
                "max": max_date.isoformat(),
                "span_days": span_days
            },
            "number_of_periods": len(trend_data)
        },
        "data": trend_data
    }


def get_kpis(dataset_id: str) -> Dict[str, Any]:
    """
    KPI Engine: Automatically discovers suitable business numeric columns and calculates
    deterministic business KPIs, safely excluding ID-like columns.
    """
    df, profile = require_dataset(dataset_id)
    quality = profile.get("quality", {})

    excluded_id_columns = []
    kpi_metrics = {}

    for col in df.columns:
        series = df[col]
        if not pd.api.types.is_numeric_dtype(series):
            # Attempt safe numeric coercion check
            coerced = pd.to_numeric(series, errors="coerce")
            if coerced.dropna().empty:
                continue
            series = coerced

        # Check identifier heuristic
        if is_likely_identifier_column(series, col):
            excluded_id_columns.append(col)
            continue

        clean_vals = series.dropna()
        if len(clean_vals) == 0:
            continue

        kpi_metrics[col] = {
            "total": to_json_serializable(clean_vals.sum()),
            "average": round(float(clean_vals.mean()), 2),
            "minimum": to_json_serializable(clean_vals.min()),
            "maximum": to_json_serializable(clean_vals.max()),
            "median": to_json_serializable(clean_vals.median()),
            "count": int(len(clean_vals))
        }

    return {
        "dataset_id": dataset_id,
        "row_count": int(len(df)),
        "column_count": int(len(df.columns)),
        "missing_cells": int(quality.get("missing_cells", 0)),
        "duplicate_rows": int(quality.get("duplicate_rows", 0)),
        "quality_score": float(quality.get("score", 100.0)),
        "excluded_id_columns": excluded_id_columns,
        "kpis": kpi_metrics
    }


def detect_anomalies(
    dataset_or_id: Union[str, pd.DataFrame],
    metric_column: str,
    date_column: Optional[str] = None,
    dimension_column: Optional[str] = None,
    limit: int = 20
) -> Dict[str, Any]:
    """
    Deterministic anomaly and outlier detection using the Interquartile Range (IQR) method.
    Q1 = 25th percentile
    Q3 = 75th percentile
    IQR = Q3 - Q1
    lower_bound = Q1 - 1.5 * IQR
    upper_bound = Q3 + 1.5 * IQR
    An observation is flagged anomalous strictly if value < lower_bound or value > upper_bound.
    """
    if limit < 1 or limit > 1000:
        raise DataBrainError("INVALID_LIMIT", "Limit must be an integer between 1 and 1000.")

    if isinstance(dataset_or_id, pd.DataFrame):
        df = dataset_or_id
    else:
        df, _ = require_dataset(dataset_or_id)

    if len(df) == 0:
        raise DataBrainError("EMPTY_DATASET", "Dataset is empty.")

    met_col, num_series = require_numeric_column(df, metric_column)

    # Optional columns validation
    dt_col = None
    if date_column:
        dt_col = require_column(df, date_column)

    dim_col = None
    if dimension_column:
        dim_col = require_column(df, dimension_column)

    # Filter out NaNs, infinite values, and missing values
    valid_mask = num_series.notna() & ~np.isinf(num_series)
    valid_series = num_series[valid_mask]
    total_valid = len(valid_series)

    # Edge cases: all-null, or fewer than 4 valid observations
    if total_valid < 4:
        return {
            "column": met_col,
            "method": "IQR",
            "q1": 0.0 if total_valid == 0 else round(float(valid_series.min()), 4),
            "q3": 0.0 if total_valid == 0 else round(float(valid_series.max()), 4),
            "iqr": 0.0,
            "lower_bound": 0.0 if total_valid == 0 else round(float(valid_series.min()), 4),
            "upper_bound": 0.0 if total_valid == 0 else round(float(valid_series.max()), 4),
            "anomaly_count": 0,
            "anomaly_percentage": 0.0,
            "anomalies": [],
            "normal_count": total_valid
        }

    q1 = float(np.percentile(valid_series, 25))
    q3 = float(np.percentile(valid_series, 75))
    iqr = float(q3 - q1)
    lower_bound = float(q1 - 1.5 * iqr)
    upper_bound = float(q3 + 1.5 * iqr)

    anomalies = []
    for idx, val in valid_series.items():
        is_low = val < lower_bound
        is_high = val > upper_bound
        if is_low or is_high:
            anomaly_record = {
                "row_index": int(idx) if isinstance(idx, (int, np.integer)) else str(idx),
                "metric_value": to_json_serializable(val),
                "value": to_json_serializable(val),
                "direction": "high" if is_high else "low"
            }
            if dt_col:
                date_val = df.loc[idx, dt_col]
                anomaly_record["date"] = None if pd.isna(date_val) else str(date_val)
            if dim_col:
                dim_val = df.loc[idx, dim_col]
                anomaly_record["category"] = None if pd.isna(dim_val) else str(dim_val)
                anomaly_record["dimension"] = anomaly_record["category"]
            anomalies.append(anomaly_record)

    def deviation_magnitude(a):
        v = float(a["value"])
        if a["direction"] == "high":
            return v - upper_bound
        return lower_bound - v

    anomalies.sort(key=deviation_magnitude, reverse=True)

    anomaly_count = len(anomalies)
    normal_count = total_valid - anomaly_count
    anomaly_percentage = round((anomaly_count / total_valid) * 100, 2) if total_valid > 0 else 0.0

    return {
        "column": met_col,
        "method": "IQR",
        "q1": round(q1, 4),
        "q3": round(q3, 4),
        "iqr": round(iqr, 4),
        "lower_bound": round(lower_bound, 4),
        "upper_bound": round(upper_bound, 4),
        "anomaly_count": anomaly_count,
        "anomaly_percentage": anomaly_percentage,
        "anomalies": anomalies[:limit],
        "normal_count": normal_count
    }


def forecast_metric(
    dataset_or_id: Union[str, pd.DataFrame],
    metric_column: str,
    date_column: str,
    periods: int = 3,
    frequency: Optional[str] = None
) -> Dict[str, Any]:
    """
    Deterministic time-series forecasting using linear trend regression (y = a*x + b).
    Aggregates historical data by frequency, fits linear slope and intercept via least-squares,
    and extrapolates deterministic predictions for future periods.
    """
    if not isinstance(periods, int) or periods < 1 or periods > 24:
        raise DataBrainError("INVALID_PERIODS", "Periods must be an integer between 1 and 24.")

    if isinstance(dataset_or_id, pd.DataFrame):
        df = dataset_or_id
    else:
        df, _ = require_dataset(dataset_or_id)

    if len(df) == 0:
        raise DataBrainError("EMPTY_DATASET", "Dataset is empty.")

    met_col, num_series = require_numeric_column(df, metric_column)
    dt_col, dt_series = require_datetime_column(df, date_column)

    # Filter out NaNs, infinite values, and missing dates
    valid_mask = num_series.notna() & ~np.isinf(num_series) & dt_series.notna()
    if not valid_mask.any():
        raise DataBrainError("NO_VALID_DATA", "Dataset contains no valid numeric and datetime entries for forecasting.")

    clean_dates = dt_series[valid_mask]
    clean_vals = num_series[valid_mask]

    min_date = clean_dates.min()
    max_date = clean_dates.max()
    span_days = (max_date - min_date).days

    freq_raw = (frequency or "auto").lower().strip()
    valid_freqs = {"auto", "day", "daily", "week", "weekly", "month", "monthly", "quarter", "quarterly", "year", "yearly"}
    if freq_raw not in valid_freqs:
        raise DataBrainError(
            "INVALID_FREQUENCY",
            f"Unsupported frequency '{frequency}'. Supported: 'daily', 'weekly', 'monthly', 'quarterly', 'yearly'."
        )

    alias_map = {"daily": "day", "weekly": "week", "monthly": "month", "quarterly": "quarter", "yearly": "year"}
    chosen_freq = alias_map.get(freq_raw, freq_raw)

    if chosen_freq == "auto":
        if span_days <= 31:
            chosen_freq = "day"
        elif span_days <= 180:
            chosen_freq = "week"
        elif span_days <= 730:
            chosen_freq = "month"
        elif span_days <= 1825:
            chosen_freq = "quarter"
        else:
            chosen_freq = "year"

    trend_df = pd.DataFrame({"datetime": clean_dates, "metric": clean_vals}).sort_values("datetime")

    if chosen_freq == "month":
        trend_df["period"] = trend_df["datetime"].dt.strftime("%Y-%m")
        trend_df["period_dt"] = trend_df["datetime"].dt.to_period("M").dt.start_time
    elif chosen_freq == "day":
        trend_df["period"] = trend_df["datetime"].dt.strftime("%Y-%m-%d")
        trend_df["period_dt"] = trend_df["datetime"].dt.floor("D")
    elif chosen_freq == "year":
        trend_df["period"] = trend_df["datetime"].dt.strftime("%Y")
        trend_df["period_dt"] = trend_df["datetime"].dt.to_period("Y").dt.start_time
    elif chosen_freq == "quarter":
        trend_df["period"] = trend_df["datetime"].apply(lambda d: f"{d.year}-Q{d.quarter}")
        trend_df["period_dt"] = trend_df["datetime"].dt.to_period("Q").dt.start_time
    elif chosen_freq == "week":
        trend_df["period"] = trend_df["datetime"].apply(lambda d: f"{d.year}-W{d.isocalendar().week:02d}")
        trend_df["period_dt"] = trend_df["datetime"].dt.to_period("W").dt.start_time

    grouped = trend_df.groupby(["period", "period_dt"], sort=True)["metric"].sum().reset_index()
    grouped = grouped.sort_values("period_dt").reset_index(drop=True)

    n = len(grouped)
    if n < 3:
        raise DataBrainError(
            "INSUFFICIENT_DATA",
            f"Forecasting requires at least 3 historical time periods, but only {n} were found."
        )

    x = np.arange(n, dtype=float)
    y = grouped["metric"].values.astype(float)

    x_mean = float(np.mean(x))
    y_mean = float(np.mean(y))
    denom = float(np.sum((x - x_mean) ** 2))

    if denom == 0.0:
        slope = 0.0
        intercept = y_mean
    else:
        slope = float(np.sum((x - x_mean) * (y - y_mean)) / denom)
        intercept = float(y_mean - slope * x_mean)

    if slope > 0.001:
        trend_direction = "up"
    elif slope < -0.001:
        trend_direction = "down"
    else:
        trend_direction = "flat"

    last_p_dt = grouped["period_dt"].iloc[-1]
    forecast_points = []

    for step in range(1, periods + 1):
        x_fut = (n - 1) + step
        pred_val = slope * x_fut + intercept

        if chosen_freq == "month":
            fut_p = pd.Period(last_p_dt, freq="M") + step
            fut_label = fut_p.strftime("%Y-%m")
        elif chosen_freq == "day":
            fut_dt = last_p_dt + pd.Timedelta(days=step)
            fut_label = fut_dt.strftime("%Y-%m-%d")
        elif chosen_freq == "week":
            fut_p = pd.Period(last_p_dt, freq="W") + step
            fut_label = f"{fut_p.year}-W{fut_p.week:02d}"
        elif chosen_freq == "quarter":
            fut_p = pd.Period(last_p_dt, freq="Q") + step
            fut_label = f"{fut_p.year}-Q{fut_p.quarter}"
        elif chosen_freq == "year":
            fut_p = pd.Period(last_p_dt, freq="Y") + step
            fut_label = str(fut_p.year)

        forecast_points.append({
            "period": fut_label,
            "date": fut_label,
            "predicted_value": round(float(pred_val), 4),
            "value": round(float(pred_val), 4)
        })

    historical_points = []
    for _, row in grouped.iterrows():
        historical_points.append({
            "period": row["period"],
            "date": row["period"],
            "value": to_json_serializable(row["metric"])
        })

    return {
        "metric_column": met_col,
        "date_column": dt_col,
        "frequency": chosen_freq,
        "method": "linear_trend",
        "historical_count": n,
        "forecast_periods": periods,
        "trend_slope": round(slope, 4),
        "trend_direction": trend_direction,
        "historical": historical_points,
        "forecast": forecast_points
    }

