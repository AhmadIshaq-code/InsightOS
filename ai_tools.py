"""
InsightOS Safe AI Tool Registry (ai_tools.py)
Approved deterministic tool contracts for Reasoning Brain orchestration.
Provides strictly isolated, deterministic operations for data and documents.
"""

from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from pydantic import BaseModel, Field, ValidationError

import re
import numpy as np

from dataset_service import get_dataset_profile_by_id
from data_brain import (
    get_dataset_summary,
    get_kpis as db_get_kpis,
    get_top_categories,
    get_time_trend,
    aggregate_by_category,
    get_numeric_statistics,
    detect_anomalies as db_detect_anomalies,
    forecast_metric as db_forecast_metric
)
from knowledge_service import search_documents as kb_search_documents


# =====================================================================
# 1. Pydantic Tool Input Schemas
# =====================================================================

class AnalyzeDatasetInput(BaseModel):
    question: str = Field(..., description="The analytics question or metric to investigate.")
    dataset_id: Optional[str] = Field(None, description="The ID of the dataset to analyze.")
    operation: Optional[str] = Field(None, description="Optional operation: 'top', 'bottom', 'aggregate', 'trend', 'kpis', 'summary'.")
    dimension_column: Optional[str] = Field(None, description="Optional category or dimension column for aggregation.")
    metric_column: Optional[str] = Field(None, description="Optional numerical metric column for calculation.")
    date_column: Optional[str] = Field(None, description="Optional date/time column for time trend.")
    aggregation: Optional[str] = Field("sum", description="Optional aggregation function (sum, mean, count, min, max).")
    frequency: Optional[str] = Field("auto", description="Optional frequency for time trend (day, week, month, quarter, year, auto).")
    limit: Optional[int] = Field(5, ge=1, le=100, description="Optional limit for top/bottom ranking.")


class GetKpisInput(BaseModel):
    dataset_id: str = Field(..., description="The UUID of the dataset to calculate KPIs for.")


class GetDataQualityInput(BaseModel):
    dataset_id: str = Field(..., description="The UUID of the dataset to evaluate data quality for.")


class SearchDocumentsInput(BaseModel):
    query: str = Field(..., description="The semantic search query to look up in indexed documents.")
    document_id: Optional[str] = Field(None, description="Optional document UUID filter.")
    top_k: int = Field(default=5, ge=1, le=50, description="Maximum number of chunks to retrieve.")


class DetectAnomaliesInput(BaseModel):
    dataset_id: str = Field(..., description="The UUID of the dataset to analyze for anomalies.")
    metric_column: str = Field(..., description="The numerical column to detect anomalies in.")
    date_column: Optional[str] = Field(None, description="Optional date/time column for temporal context.")
    dimension_column: Optional[str] = Field(None, description="Optional categorical/dimension column for context.")
    limit: Optional[int] = Field(20, ge=1, le=1000, description="Maximum number of anomaly records to return.")


class ForecastMetricInput(BaseModel):
    dataset_id: str = Field(..., description="The UUID of the dataset to generate forecasts for.")
    metric_column: str = Field(..., description="The numerical column to forecast.")
    date_column: str = Field(..., description="The date/time column for time-series aggregation.")
    periods: int = Field(default=3, ge=1, le=24, description="Number of future periods to forecast (1 to 24).")
    frequency: Optional[str] = Field(None, description="Optional time frequency: 'daily', 'weekly', 'monthly', 'quarterly', 'yearly'.")


# =====================================================================
# Helper Functions for Deterministic Formatting & Column Detection
# =====================================================================

def format_period_label(period_str: str) -> str:
    """Formats period string (e.g. 2026-01) to human readable (e.g. Jan 2026)."""
    m = re.match(r"^(\d{4})-(\d{2})$", str(period_str).strip())
    if m:
        year, month = int(m.group(1)), int(m.group(2))
        month_names = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        if 1 <= month <= 12:
            return f"{month_names[month]} {year}"
    return str(period_str)


def format_numeric_value(val: Any) -> str:
    """Formats numeric values with commas for thousands."""
    if val is None:
        return "N/A"
    if isinstance(val, (int, np.integer)):
        return f"{val:,}"
    if isinstance(val, (float, np.floating)):
        return f"{val:,.2f}".rstrip("0").rstrip(".") if val % 1 != 0 else f"{int(val):,}"
    try:
        fval = float(val)
        return f"{fval:,.2f}".rstrip("0").rstrip(".") if fval % 1 != 0 else f"{int(fval):,}"
    except (ValueError, TypeError):
        return str(val)


def detect_data_operation_and_columns(question: str, profile: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deterministically extracts operation, dimension column, metric column, and date column
    from the question and dataset metadata.
    Does NOT guess columns when ambiguous.
    """
    q_lower = question.lower().strip()
    columns_meta = profile.get("columns", [])

    date_cols = []
    num_cols = []
    cat_cols = []

    for c in columns_meta:
        cname = c.get("name", "")
        sem = c.get("semantic_type", "")
        dtype = str(c.get("pandas_dtype", "")).lower()
        if sem == "datetime" or any(h in cname.lower() for h in ["date", "timestamp", "time"]):
            date_cols.append(cname)
        elif sem == "numeric" or any(t in dtype for t in ["int", "float", "number"]):
            # Exclude obvious row IDs
            if not re.search(r'(?:_id|id$|^id)', cname.lower()):
                num_cols.append(cname)
        else:
            cat_cols.append(cname)

    # 1. Match numeric metrics from question
    matched_metrics = []
    for c in num_cols:
        clow = c.lower()
        if re.search(r'\b' + re.escape(clow) + r's?\b', q_lower):
            matched_metrics.append(c)
        elif clow in ["revenue", "sales", "turnover"] and any(w in q_lower for w in ["revenue", "revenues", "sales", "turnover", "selling"]):
            matched_metrics.append(c)
        elif clow in ["units", "quantity", "volume"] and any(w in q_lower for w in ["unit", "units", "quantity", "volume"]):
            matched_metrics.append(c)
        elif clow in ["salary", "compensation", "pay", "wage"] and any(w in q_lower for w in ["salary", "salaries", "compensation", "pay", "wage"]):
            matched_metrics.append(c)
        elif clow in ["cost", "expense", "spend"] and any(w in q_lower for w in ["cost", "costs", "expense", "expenses", "spend"]):
            matched_metrics.append(c)

    matched_metrics = list(dict.fromkeys(matched_metrics))

    # 2. Match dimension/category columns from question
    matched_dims = []
    for c in cat_cols:
        clow = c.lower()
        if re.search(r'\b' + re.escape(clow) + r's?\b', q_lower):
            matched_dims.append(c)
        elif clow.endswith('y') and re.search(r'\b' + re.escape(clow[:-1]) + r'ies\b', q_lower):
            matched_dims.append(c)
        elif clow in ["product", "item"] and any(w in q_lower for w in ["product", "products", "item", "items", "selling"]):
            matched_dims.append(c)
        elif clow in ["category", "type", "segment"] and any(w in q_lower for w in ["category", "categories", "type", "segment"]):
            matched_dims.append(c)
        elif clow in ["department", "dept"] and any(w in q_lower for w in ["department", "departments", "dept"]):
            matched_dims.append(c)
        elif clow in ["region", "territory", "location"] and any(w in q_lower for w in ["region", "regions", "territory", "location"]):
            matched_dims.append(c)

    matched_dims = list(dict.fromkeys(matched_dims))

    # 3. Match date columns from question
    matched_dates = []
    for c in date_cols:
        clow = c.lower()
        if re.search(r'\b' + re.escape(clow) + r's?\b', q_lower):
            matched_dates.append(c)
        elif any(w in q_lower for w in ["date", "time", "month", "monthly", "trend", "year", "yearly", "day", "daily", "timeline", "over time"]):
            matched_dates.append(c)

    matched_dates = list(dict.fromkeys(matched_dates))

    # Extract limit (e.g., "top 3")
    limit = 5
    m_lim = re.search(r'\btop\s+(\d+)\b', q_lower)
    if m_lim:
        try:
            limit = max(1, min(int(m_lim.group(1)), 100))
        except ValueError:
            limit = 5

    # Check for Trend intent
    is_trend = any(w in q_lower for w in [
        "trend", "over time", "by month", "monthly", "by year", "yearly",
        "by day", "daily", "across months", "over the months", "change over time",
        "plot over time", "timeline", "how did"
    ]) and any(w in q_lower for w in ["trend", "time", "month", "year", "day", "change", "over time"])

    # Check for Top / Ranking intent
    is_top = any(w in q_lower for w in [
        "most", "highest", "top", "best selling", "maximum", "greatest",
        "leader", "lead", "rank", "ranking"
    ])

    # Check for Breakdown intent
    is_breakdown = any(w in q_lower for w in [
        "by product", "by category", "by department", "by region",
        "per product", "per category", "revenue by", "sales by", "breakdown by"
    ]) or bool(re.search(r'\b(revenue|sales|units|quantity|salary|cost)\s+by\s+\w+', q_lower))

    # Check for Anomaly / Outlier intent
    is_anomaly = any(w in q_lower for w in [
        "unusual", "anomaly", "anomalies", "outlier", "outliers", "abnormal", "irregular", "deviat"
    ])

    if is_anomaly:
        if matched_metrics:
            metric_col = matched_metrics[0]
        elif len(num_cols) == 1:
            metric_col = num_cols[0]
        else:
            return {
                "operation": "ambiguous",
                "ambiguous": True,
                "message": "Could not determine which numeric column to check for anomalies.",
                "num_cols": num_cols,
                "cat_cols": cat_cols,
                "date_cols": date_cols
            }

        date_col = matched_dates[0] if matched_dates else (date_cols[0] if date_cols else None)
        dim_col = matched_dims[0] if matched_dims else (cat_cols[0] if cat_cols else None)

        return {
            "operation": "anomaly",
            "ambiguous": False,
            "metric_column": metric_col,
            "date_column": date_col,
            "dimension_column": dim_col,
            "limit": 20,
            "num_cols": num_cols,
            "cat_cols": cat_cols,
            "date_cols": date_cols
        }

    # Check for Forecast intent
    is_forecast = any(w in q_lower for w in [
        "forecast", "predict", "prediction", "projected", "projection",
        "future", "look like next"
    ]) or bool(re.search(r'\bnext\s+(?:\d+\s+)?(?:month|quarter|year|week|day)s?\b', q_lower))

    if is_forecast:
        m_per = re.search(r'\bnext\s+(\d+)\s+(?:month|quarter|year|week|day)s?\b', q_lower)
        forecast_periods = 3
        if m_per:
            try:
                forecast_periods = max(1, min(int(m_per.group(1)), 24))
            except ValueError:
                forecast_periods = 3

        forecast_freq = None
        if "quarter" in q_lower:
            forecast_freq = "quarterly"
        elif "month" in q_lower:
            forecast_freq = "monthly"
        elif "year" in q_lower:
            forecast_freq = "yearly"
        elif "week" in q_lower:
            forecast_freq = "weekly"
        elif "day" in q_lower:
            forecast_freq = "daily"

        if not date_cols:
            return {
                "operation": "error",
                "ambiguous": False,
                "message": "The active dataset does not have a date or timestamp column to calculate time-series forecasts.",
                "num_cols": num_cols,
                "cat_cols": cat_cols,
                "date_cols": date_cols
            }

        if matched_metrics:
            metric_col = matched_metrics[0]
        elif len(num_cols) == 1:
            metric_col = num_cols[0]
        else:
            return {
                "operation": "ambiguous",
                "ambiguous": True,
                "message": "Could not determine which numeric column to forecast.",
                "num_cols": num_cols,
                "cat_cols": cat_cols,
                "date_cols": date_cols
            }

        date_col = matched_dates[0] if matched_dates else date_cols[0]
        return {
            "operation": "forecast",
            "ambiguous": False,
            "metric_column": metric_col,
            "date_column": date_col,
            "periods": forecast_periods,
            "frequency": forecast_freq,
            "num_cols": num_cols,
            "cat_cols": cat_cols,
            "date_cols": date_cols
        }

    # Trend Operation
    if is_trend:
        if not date_cols:
            return {
                "operation": "error",
                "ambiguous": False,
                "message": "The active dataset does not have a date or timestamp column to calculate time trends.",
                "num_cols": num_cols,
                "cat_cols": cat_cols,
                "date_cols": date_cols
            }

        if matched_metrics:
            metric_col = matched_metrics[0]
        elif len(num_cols) == 1:
            metric_col = num_cols[0]
        else:
            # Ambiguous: multiple metrics and none specified in trend question
            return {
                "operation": "ambiguous",
                "ambiguous": True,
                "message": "Could not determine which numeric metric to calculate for the trend.",
                "num_cols": num_cols,
                "cat_cols": cat_cols,
                "date_cols": date_cols
            }

        date_col = matched_dates[0] if matched_dates else date_cols[0]
        freq = "month" if any(w in q_lower for w in ["month", "monthly", "trend", "over time"]) else "auto"

        return {
            "operation": "trend",
            "ambiguous": False,
            "metric_column": metric_col,
            "date_column": date_col,
            "frequency": freq,
            "dimension_column": None,
            "limit": limit,
            "num_cols": num_cols,
            "cat_cols": cat_cols,
            "date_cols": date_cols
        }

    # Top / Breakdown Operation
    if is_top or is_breakdown:
        if matched_dims:
            dim_col = matched_dims[0]
        else:
            # Dimension is ambiguous or not specified
            return {
                "operation": "ambiguous",
                "ambiguous": True,
                "message": "Could not determine which category or dimension to group by.",
                "num_cols": num_cols,
                "cat_cols": cat_cols,
                "date_cols": date_cols
            }

        if matched_metrics:
            metric_col = matched_metrics[0]
        elif len(num_cols) == 1:
            metric_col = num_cols[0]
        else:
            # Metric is ambiguous or not specified
            return {
                "operation": "ambiguous",
                "ambiguous": True,
                "message": f"Could not determine which numeric metric to analyze for '{dim_col}'.",
                "num_cols": num_cols,
                "cat_cols": cat_cols,
                "date_cols": date_cols
            }

        return {
            "operation": "top",
            "ambiguous": False,
            "dimension_column": dim_col,
            "metric_column": metric_col,
            "date_column": None,
            "limit": limit,
            "num_cols": num_cols,
            "cat_cols": cat_cols,
            "date_cols": date_cols
        }

    # General KPI / column stats fallback
    return {
        "operation": "kpis",
        "ambiguous": False,
        "dimension_column": matched_dims[0] if matched_dims else None,
        "metric_column": matched_metrics[0] if matched_metrics else None,
        "date_column": matched_dates[0] if matched_dates else None,
        "limit": limit,
        "num_cols": num_cols,
        "cat_cols": cat_cols,
        "date_cols": date_cols
    }


# =====================================================================
# 2. Tool Implementations (Strictly Deterministic)
# =====================================================================

def analyze_dataset_tool(
    question: str,
    dataset_id: Optional[str] = None,
    operation: Optional[str] = None,
    dimension_column: Optional[str] = None,
    metric_column: Optional[str] = None,
    date_column: Optional[str] = None,
    aggregation: Optional[str] = "sum",
    frequency: Optional[str] = "auto",
    limit: Optional[int] = 5
) -> Dict[str, Any]:
    """
    Interrogates Data Brain for dataset calculations.
    Deterministically routes to top category rankings, time trends, or KPI summaries.
    Rejects execution if dataset_id is missing.
    """
    if not dataset_id or not str(dataset_id).strip():
        return {
            "success": False,
            "error": "Missing dataset_id. A valid dataset_id is required to perform dataset analysis.",
            "facts": [],
            "text": "📊 **Data Brain Error:** No dataset specified for analysis."
        }

    try:
        profile = get_dataset_profile_by_id(dataset_id)
        filename = profile.get("dataset", {}).get("original_filename", "Dataset")
        detection = detect_data_operation_and_columns(question, profile)

        # Allow explicit parameters to override auto-detection if supplied
        op = operation or detection.get("operation", "kpis")
        dim_col = dimension_column or detection.get("dimension_column")
        met_col = metric_column or detection.get("metric_column")
        dt_col = date_column or detection.get("date_column")
        agg = aggregation or "sum"
        freq = frequency if frequency and frequency != "auto" else detection.get("frequency", "month")
        lim = limit or detection.get("limit", 5)

        # -----------------------------------------------------------------
        # A. Ambiguous Query Check (Do NOT Guess Columns)
        # -----------------------------------------------------------------
        if detection.get("ambiguous") and not (operation and (dim_col or dt_col)):
            msg = detection.get("message", "Could not determine required columns from your question.")
            cats_str = ", ".join(detection.get("cat_cols", [])) or "None"
            metrics_str = ", ".join(detection.get("num_cols", [])) or "None"
            text = (
                f"⚠️ **Ambiguous Query:** {msg}\n\n"
                f"**Available Categories:** {cats_str}\n"
                f"**Available Metrics:** {metrics_str}\n\n"
                "Please specify the exact category column (e.g. 'by Product') and numeric metric (e.g. 'by Revenue') to investigate."
            )
            return {
                "success": True,
                "ambiguous": True,
                "dataset_id": dataset_id,
                "filename": filename,
                "facts": [],
                "text": text
            }

        # -----------------------------------------------------------------
        # B. Product / Category Performance (Top Breakdown)
        # -----------------------------------------------------------------
        if op == "top" and dim_col and met_col:
            top_data = get_top_categories(
                dataset_id=dataset_id,
                category_column=dim_col,
                metric_column=met_col,
                aggregation=agg,
                limit=lim
            )
            items = top_data.get("items", [])
            facts = []
            lines = []
            for it in items:
                cat = it["category"]
                val = it["value"]
                val_str = format_numeric_value(val)
                lines.append(f"  * **{cat}**: {val_str}")
                facts.append(f"{dim_col} '{cat}' had {met_col} of {val_str}.")

            top_item = items[0] if items else None
            top_summary = ""
            if top_item:
                top_cat = top_item["category"]
                top_val_str = format_numeric_value(top_item["value"])
                top_summary = f"\n\n**Top {dim_col.lower()}:** {top_cat} with {met_col.lower()} of {top_val_str}."
                facts.insert(0, f"{top_cat} generated the most {met_col.lower()}: {top_val_str}.")

            breakdown_text = "\n".join(lines)
            text = (
                f"📊 **DATA FINDINGS**\n\n"
                f"* **{met_col} by {dim_col}:**\n"
                f"{breakdown_text}"
                f"{top_summary}\n\n"
                f"_Calculated deterministically via InsightOS Data Brain._"
            )

            return {
                "success": True,
                "dataset_id": dataset_id,
                "filename": filename,
                "operation": "top",
                "dimension_column": dim_col,
                "metric_column": met_col,
                "items": items,
                "facts": facts,
                "text": text
            }

        # -----------------------------------------------------------------
        # C. Time-Series Trend Analysis
        # -----------------------------------------------------------------
        if op == "trend" and dt_col and met_col:
            trend_res = get_time_trend(
                dataset_id=dataset_id,
                date_column=dt_col,
                metric_column=met_col,
                aggregation=agg,
                frequency=freq
            )
            trend_data = trend_res.get("data", [])
            facts = []
            lines = []
            for p in trend_data:
                raw_p = p["period"]
                fmt_p = format_period_label(raw_p)
                val_str = format_numeric_value(p["value"])
                lines.append(f"  * **{fmt_p}**: {val_str}")
                facts.append(f"{fmt_p} ({raw_p}) {met_col}: {val_str}.")

            trend_lines_text = "\n".join(lines)
            text = (
                f"📊 **DATA FINDINGS**\n\n"
                f"* **{met_col} Trend Over Time:**\n"
                f"{trend_lines_text}\n\n"
                f"_Calculated deterministically via InsightOS Data Brain._"
            )

            return {
                "success": True,
                "dataset_id": dataset_id,
                "filename": filename,
                "operation": "trend",
                "date_column": dt_col,
                "metric_column": met_col,
                "frequency": freq,
                "data": trend_data,
                "facts": facts,
                "text": text
            }

        # -----------------------------------------------------------------
        # D. Generic KPI / Summary Fallback
        # -----------------------------------------------------------------
        summary = get_dataset_summary(dataset_id)
        kpis_data = db_get_kpis(dataset_id)
        kpis = kpis_data.get("kpis", {})

        facts = [
            f"Dataset '{filename}' has {summary['row_count']} rows and {summary['column_count']} columns.",
            f"Data quality health score is {summary['quality_score']}% with {summary['missing_cells']} missing cells ({summary['missing_percentage']}%)."
        ]

        q_lower = question.lower()
        matched_kpis = []
        for col_name, metric in kpis.items():
            if col_name.lower() in q_lower or (met_col and col_name.lower() == met_col.lower()):
                matched_kpis.append((col_name, metric))

        kpis_to_show = matched_kpis if matched_kpis else list(kpis.items())[:4]
        kpi_lines = []
        for col, metric in kpis_to_show:
            line = f"- **{col}**: Total = {format_numeric_value(metric['total'])}, Average = {format_numeric_value(metric['average'])}, Min = {format_numeric_value(metric['minimum'])}, Max = {format_numeric_value(metric['maximum'])}"
            kpi_lines.append(line)
            facts.append(f"Metric '{col}': Total={format_numeric_value(metric['total'])}, Avg={format_numeric_value(metric['average'])}, Min={format_numeric_value(metric['minimum'])}, Max={format_numeric_value(metric['maximum'])}.")

        kpi_section = "\n".join(kpi_lines) if kpi_lines else "No suitable numerical KPI columns found."

        text = (
            f"📊 **DATA FINDINGS**\n\n"
            f"**Dataset Overview ({filename}):**\n"
            f"- Rows: {summary['row_count']} | Columns: {summary['column_count']}\n"
            f"- Quality Score: {summary['quality_score']}%\n"
            f"- Missing Cells: {summary['missing_cells']} ({summary['missing_percentage']}%)\n\n"
            f"**Deterministic Key Metrics:**\n"
            f"{kpi_section}\n\n"
            f"_Calculated deterministically via InsightOS Data Brain._"
        )

        return {
            "success": True,
            "dataset_id": dataset_id,
            "filename": filename,
            "summary": summary,
            "kpis": kpis,
            "facts": facts,
            "text": text
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "facts": [],
            "text": f"📊 **Data Brain Error:** Failed to analyze dataset '{dataset_id}': {str(e)}"
        }


def get_kpis_tool(dataset_id: str) -> Dict[str, Any]:
    """
    Computes deterministic KPIs (total, avg, min, max) for numeric columns.
    """
    if not dataset_id or not str(dataset_id).strip():
        return {
            "success": False,
            "error": "Missing dataset_id. A valid dataset_id is required to calculate KPIs.",
            "kpis": {},
            "facts": []
        }

    try:
        profile = get_dataset_profile_by_id(dataset_id)
        filename = profile.get("dataset", {}).get("original_filename", "Dataset")
        kpis_data = db_get_kpis(dataset_id)
        kpis = kpis_data.get("kpis", {})

        facts = []
        kpi_lines = []
        for col, metric in kpis.items():
            facts.append(f"Column '{col}' Total: {metric['total']}, Avg: {metric['average']}, Min: {metric['minimum']}, Max: {metric['maximum']}.")
            kpi_lines.append(f"- **{col}**: Total = {metric['total']}, Avg = {metric['average']}, Min = {metric['minimum']}, Max = {metric['maximum']}")

        kpi_section = "\n".join(kpi_lines) if kpi_lines else "No numerical KPI columns detected."
        text = f"📊 **Key Performance Indicators ({filename}):**\n\n{kpi_section}"

        return {
            "success": True,
            "dataset_id": dataset_id,
            "filename": filename,
            "kpis": kpis,
            "facts": facts,
            "text": text
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "kpis": {},
            "facts": [],
            "text": f"Error calculating KPIs: {str(e)}"
        }


def get_data_quality_tool(dataset_id: str) -> Dict[str, Any]:
    """
    Retrieves deterministic data quality audit metrics.
    """
    if not dataset_id or not str(dataset_id).strip():
        return {
            "success": False,
            "error": "Missing dataset_id. A valid dataset_id is required to evaluate data quality.",
            "quality": {},
            "facts": []
        }

    try:
        profile = get_dataset_profile_by_id(dataset_id)
        filename = profile.get("dataset", {}).get("original_filename", "Dataset")
        quality = profile.get("quality", {})
        summary = profile.get("summary", {})

        score = quality.get("score", 100.0)
        missing_cells = quality.get("missing_cells", 0)
        missing_pct = quality.get("missing_percentage", 0.0)
        dupes = quality.get("duplicate_rows", 0)
        dupe_pct = quality.get("duplicate_percentage", 0.0)

        facts = [
            f"Dataset '{filename}' overall health score is {score}%.",
            f"Missing cells: {missing_cells} ({missing_pct}%).",
            f"Duplicate rows: {dupes} ({dupe_pct}%)."
        ]

        text = (
            f"🛡️ **Data Quality & Health Audit ({filename}):**\n\n"
            f"- **Overall Health Score**: {score}%\n"
            f"- **Missing Values**: {missing_cells} cells ({missing_pct}%)\n"
            f"- **Duplicate Rows**: {dupes} rows ({dupe_pct}%)\n"
            f"- **Total Rows**: {summary.get('row_count', 'N/A')} | **Columns**: {summary.get('column_count', 'N/A')}"
        )

        return {
            "success": True,
            "dataset_id": dataset_id,
            "filename": filename,
            "quality": quality,
            "facts": facts,
            "text": text
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "quality": {},
            "facts": [],
            "text": f"Error retrieving data quality: {str(e)}"
        }


def search_documents_tool(
    query: str,
    document_id: Optional[str] = None,
    top_k: int = 5
) -> Dict[str, Any]:
    """
    Performs semantic vector search via Knowledge Brain.
    Reuses existing search_documents with verified supported parameters.
    """
    if not query or not str(query).strip():
        return {
            "success": False,
            "error": "Search query cannot be empty.",
            "chunks": [],
            "citations": []
        }

    clamped_k = max(1, min(int(top_k), 50))
    try:
        results = kb_search_documents(
            query=query.strip(),
            top_k=clamped_k,
            document_id=document_id,
            min_score=0.0
        )

        citations = []
        chunks_data = []
        for r in results:
            fname = r.get("filename", "Unknown Document.pdf")
            page = r.get("page", 1)
            cite = f"{fname} (Page {page})"
            if cite not in citations:
                citations.append(cite)
            chunks_data.append({
                "filename": fname,
                "page": page,
                "text": r.get("text", ""),
                "score": r.get("relevance_score", r.get("score", 0.0))
            })

        return {
            "success": True,
            "query": query,
            "count": len(chunks_data),
            "chunks": chunks_data,
            "citations": citations
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "chunks": [],
            "citations": []
        }


def detect_anomalies_tool(
    dataset_id: str,
    metric_column: str,
    date_column: Optional[str] = None,
    dimension_column: Optional[str] = None,
    limit: int = 20
) -> Dict[str, Any]:
    """
    Executes deterministic IQR anomaly detection on a numeric column via Data Brain.
    """
    if not dataset_id or not str(dataset_id).strip():
        return {
            "success": False,
            "error": "Missing dataset_id. Please provide an active dataset ID.",
            "facts": [],
            "anomalies": []
        }

    if not metric_column or not str(metric_column).strip():
        return {
            "success": False,
            "error": "Missing metric_column. A numeric column is required for anomaly detection.",
            "facts": [],
            "anomalies": []
        }

    try:
        results = db_detect_anomalies(
            dataset_or_id=dataset_id,
            metric_column=metric_column,
            date_column=date_column,
            dimension_column=dimension_column,
            limit=limit
        )

        col = results.get("column", metric_column)
        q1_str = format_numeric_value(results.get("q1"))
        q3_str = format_numeric_value(results.get("q3"))
        iqr_str = format_numeric_value(results.get("iqr"))
        low_str = format_numeric_value(results.get("lower_bound"))
        high_str = format_numeric_value(results.get("upper_bound"))
        anom_count = results.get("anomaly_count", 0)
        anom_pct = results.get("anomaly_percentage", 0.0)
        norm_count = results.get("normal_count", 0)
        total_obs = anom_count + norm_count
        anomalies_list = results.get("anomalies", [])

        facts = [
            f"Detected {anom_count} statistical anomalies in {col} ({anom_pct}% of {total_obs} observations).",
            f"IQR bounds for {col}: lower bound = {low_str}, upper bound = {high_str} (Q1 = {q1_str}, Q3 = {q3_str}, IQR = {iqr_str})."
        ]

        text_lines = [
            "📊 **DATA FINDINGS**\n",
            f"• **Statistical Anomaly Detection for {col} (IQR Method):**",
            f"  - Normal Range: [{low_str} to {high_str}]",
            f"  - Q1 (25th percentile): {q1_str} | Q3 (75th percentile): {q3_str} | IQR: {iqr_str}",
            f"  - Total Observations: {total_obs} (Normal: {norm_count}, Anomalies: {anom_count}, {anom_pct}%)"
        ]

        if anomalies_list:
            text_lines.append(f"\n• **Identified Outliers ({len(anomalies_list)} displayed):**")
            for a in anomalies_list:
                val_formatted = format_numeric_value(a.get("value"))
                dir_label = "High outlier" if a.get("direction") == "high" else "Low outlier"
                context_parts = []
                if a.get("date"):
                    context_parts.append(f"Date: {a['date']}")
                if a.get("category"):
                    context_parts.append(f"Category: {a['category']}")

                ctx_str = f" ({', '.join(context_parts)})" if context_parts else ""
                row_str = f"Row {a.get('row_index')}: " if a.get("row_index") is not None else ""
                facts.append(f"{row_str}{dir_label} in {col}: {val_formatted}{ctx_str}")
                text_lines.append(f"  - {dir_label}: **{val_formatted}**{ctx_str}")
        else:
            text_lines.append(f"\nNo statistical anomalies or outliers detected in {col}.")

        text_lines.append("\n_Calculated deterministically via InsightOS Data Brain._")

        return {
            "success": True,
            "facts": facts,
            "text": "\n".join(text_lines),
            "result": results,
            "anomalies": anomalies_list,
            "anomaly_count": anom_count,
            "anomaly_percentage": anom_pct
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "facts": [],
            "anomalies": []
        }


def forecast_metric_tool(
    dataset_id: str,
    metric_column: str,
    date_column: str,
    periods: int = 3,
    frequency: Optional[str] = None
) -> Dict[str, Any]:
    """
    Executes deterministic time-series forecasting via Data Brain linear trend regression.
    """
    if not dataset_id:
        return {
            "success": False,
            "error": "Missing dataset_id for forecast_metric tool.",
            "facts": [],
            "forecast": []
        }

    try:
        results = db_forecast_metric(
            dataset_or_id=dataset_id,
            metric_column=metric_column,
            date_column=date_column,
            periods=periods,
            frequency=frequency
        )

        col = results.get("metric_column", metric_column)
        dt_col = results.get("date_column", date_column)
        freq = results.get("frequency", "monthly")
        slope = results.get("trend_slope", 0.0)
        direction = results.get("trend_direction", "flat")
        hist_count = results.get("historical_count", 0)
        forecast_pts = results.get("forecast", [])

        slope_str = format_numeric_value(slope)
        dir_desc = "upward" if direction == "up" else ("downward" if direction == "down" else "flat")

        facts = [
            f"Forecasted {col} for the next {periods} {freq} period(s) based on {hist_count} historical observations.",
            f"Observed {dir_desc} linear trend with a slope of {slope_str} per {freq} period."
        ]

        text_lines = [
            "📊 **DATA FINDINGS (FORECAST)**\n",
            f"• **Deterministic Time-Series Forecast for {col} ({freq.capitalize()} Cadence):**",
            f"  - Baseline Method: Linear Trend Regression (y = a*x + b)",
            f"  - Historical Observations: {hist_count} periods",
            f"  - Identified Trend: {dir_desc.capitalize()} (Slope: {slope_str} per period)\n",
            f"• **Projected Estimates (Next {len(forecast_pts)} periods):**"
        ]

        for pt in forecast_pts:
            val_fmt = format_numeric_value(pt.get("predicted_value"))
            p_label = format_period_label(pt.get("period", ""))
            facts.append(f"Projected {col} for {p_label}: {val_fmt}.")
            text_lines.append(f"  - **{p_label}**: {val_fmt} *(projected)*")

        text_lines.append("\n⚠️ *Note: Projections are mathematical extrapolations of past linear trends and do not account for external market shifts or unforeseen events.*")
        text_lines.append("\n_Calculated deterministically via InsightOS Data Brain._")

        return {
            "success": True,
            "facts": facts,
            "text": "\n".join(text_lines),
            "result": results,
            "forecast": forecast_pts,
            "trend_slope": slope,
            "trend_direction": direction
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "facts": [],
            "forecast": []
        }


# =====================================================================
# 3. Tool Registry Definition
# =====================================================================

@dataclass
class ToolDefinition:
    name: str
    description: str
    input_model: type[BaseModel]
    func: Callable


TOOL_REGISTRY: Dict[str, ToolDefinition] = {
    "analyze_dataset": ToolDefinition(
        name="analyze_dataset",
        description="Analyzes structured datasets for statistics, metrics, and trends.",
        input_model=AnalyzeDatasetInput,
        func=analyze_dataset_tool
    ),
    "get_kpis": ToolDefinition(
        name="get_kpis",
        description="Calculates deterministic KPIs (totals, averages, min, max) for numeric columns.",
        input_model=GetKpisInput,
        func=get_kpis_tool
    ),
    "get_data_quality": ToolDefinition(
        name="get_data_quality",
        description="Evaluates data quality metrics (health score, missing cells, duplicate rows).",
        input_model=GetDataQualityInput,
        func=get_data_quality_tool
    ),
    "detect_anomalies": ToolDefinition(
        name="detect_anomalies",
        description="Detects statistical anomalies and outliers in numeric columns using the deterministic IQR method.",
        input_model=DetectAnomaliesInput,
        func=detect_anomalies_tool
    ),
    "forecast_metric": ToolDefinition(
        name="forecast_metric",
        description="Generates deterministic time-series forecasts for numeric metrics using linear trend regression.",
        input_model=ForecastMetricInput,
        func=forecast_metric_tool
    ),
    "search_documents": ToolDefinition(
        name="search_documents",
        description="Performs semantic search across indexed policy documents and SOPs in Knowledge Brain.",
        input_model=SearchDocumentsInput,
        func=search_documents_tool
    )
}


# =====================================================================
# 4. Safe Tool Execution Engine
# =====================================================================

def execute_tool(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validates tool name against TOOL_REGISTRY and arguments against the tool's Pydantic model.
    Rejects any unapproved tools or malformed parameters.
    """
    if tool_name not in TOOL_REGISTRY:
        return {
            "success": False,
            "error": f"Tool '{tool_name}' is not recognized in TOOL_REGISTRY.",
            "tool": tool_name
        }

    tool_def = TOOL_REGISTRY[tool_name]

    # Validate arguments via Pydantic model
    try:
        validated_args = tool_def.input_model(**(arguments or {}))
    except ValidationError as ve:
        return {
            "success": False,
            "error": f"Invalid arguments for tool '{tool_name}': {str(ve)}",
            "tool": tool_name
        }

    # Execute approved function
    try:
        # Pydantic v2 model_dump or v1 dict fallback
        args_dict = validated_args.model_dump() if hasattr(validated_args, "model_dump") else validated_args.dict()
        result = tool_def.func(**args_dict)
        return result
    except Exception as e:
        return {
            "success": False,
            "error": f"Execution error in tool '{tool_name}': {str(e)}",
            "tool": tool_name
        }
