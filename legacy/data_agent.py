import os
import json
import pandas as pd
from langchain_groq import ChatGroq
from langchain_experimental.agents import create_pandas_dataframe_agent
from config import MODEL, get_groq_api_key

"""
LEGACY / PROTOTYPE DATA AGENT
=============================
CRITICAL SECURITY NOTE:
This component uses LangChain's experimental pandas dataframe agent with
`allow_dangerous_code=True`. It is retained strictly as temporary legacy functionality
for baseline compatibility. In Phase 3, this will be replaced by the safe,
deterministic InsightOS Data Brain (DuckDB / validated aggregations).
"""

def _extract_json(raw_str: str) -> str:
    """Strip markdown fences from LLM output."""
    raw_str = raw_str.strip()
    if raw_str.startswith("```json"):
        raw_str = raw_str[7:]
    elif raw_str.startswith("```"):
        raw_str = raw_str[3:]
    if raw_str.endswith("```"):
        raw_str = raw_str[:-3]
    raw_str = raw_str.strip()
    if not raw_str.startswith("{"):
        start = raw_str.find("{")
        end = raw_str.rfind("}")
        if start != -1 and end > start:
            raw_str = raw_str[start:end + 1]
    return raw_str.strip()

def _parse_agent_json(raw_str: str) -> dict:
    """Parse one or more JSON objects from agent output and merge into a single dict."""
    text = _extract_json(raw_str)
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    merged = {}
    decoder = json.JSONDecoder()
    idx = 0
    while idx < len(text):
        while idx < len(text) and text[idx] in " \t\n\r":
            idx += 1
        if idx >= len(text):
            break
        if text[idx] != "{":
            next_obj = text.find("{", idx)
            if next_obj == -1:
                break
            idx = next_obj
        obj, end = decoder.raw_decode(text, idx)
        if isinstance(obj, dict):
            merged.update(obj)
        idx = end

    if merged:
        return merged
    raise json.JSONDecodeError("No valid JSON object found", text, 0)

def _serialize_records(records):
    """Convert DataFrame records to JSON-safe native Python types."""
    result = []
    for row in records:
        clean = {}
        for k, v in row.items():
            if hasattr(v, "item"):
                v = v.item()
            if isinstance(v, float) and v == int(v):
                v = int(v)
            clean[str(k)] = v if isinstance(v, (int, float, str, bool)) or v is None else str(v)
        result.append(clean)
    return result

def _enrich_chart_data(df, chart):
    """Fill empty chart.data from the dataframe when the agent omits computed values."""
    if not chart:
        return chart
    data = chart.get("data")
    if isinstance(data, dict) and data:
        x_key = chart.get("x_key")
        y_key = chart.get("y_key") or "count"
        chart["data"] = [{x_key: k, y_key: v} for k, v in data.items()]
        return chart
    if isinstance(data, list) and len(data) > 0:
        return chart

    x_key = chart.get("x_key")
    y_key = chart.get("y_key") or "count"
    if not x_key or x_key not in df.columns:
        return chart

    try:
        if chart.get("type") == "line":
            grouped = df.groupby(x_key, dropna=False).size().reset_index(name=y_key)
            grouped = grouped.sort_values(x_key).head(15)
        else:
            grouped = df[x_key].value_counts().head(15).reset_index()
            grouped.columns = [x_key, y_key]
        chart["data"] = _serialize_records(grouped.to_dict("records"))
    except Exception:
        pass
    return chart

def _normalize_agent_output(raw_output: str, df) -> str:
    """Parse agent JSON, enrich empty charts, and re-serialize."""
    try:
        parsed = _parse_agent_json(raw_output)
        chart = parsed.get("chart")
        if chart:
            parsed["chart"] = _enrich_chart_data(df, chart)
            if not parsed["chart"].get("data"):
                parsed.pop("chart")
                note = " (Chart could not be generated — no data available for this visualization.)"
                parsed["answer"] = (parsed.get("answer", "") + note).strip()
        return json.dumps(parsed)
    except json.JSONDecodeError:
        return raw_output

def query_structured_data(query: str, csv_path: str = None, api_key: str = None):
    """
    LEGACY / PROTOTYPE: Queries a structured CSV dataset using the Pandas agent.
    """
    if not csv_path:
        # Check standard paths: current tickets.csv or bundled test_live_data.csv
        base_dir = os.path.dirname(__file__)
        primary_csv = os.path.join(base_dir, "tickets.csv")
        fallback_csv = os.path.join(base_dir, "test_live_data.csv")
        csv_path = primary_csv if os.path.exists(primary_csv) else fallback_csv

    if not os.path.exists(csv_path):
        return json.dumps({"answer": f"Error: Dataset {os.path.basename(csv_path)} not found."})

    active_api_key = get_groq_api_key(api_key)
    if not active_api_key:
        return json.dumps({"answer": "Error: GROQ_API_KEY is not configured. Please set it in Settings or your .env file."})

    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        return json.dumps({"answer": f"Error loading CSV file: {str(e)}"})

    # Clean empty rows and columns
    df.dropna(how='all', axis=1, inplace=True)
    df.dropna(how='all', axis=0, inplace=True)

    if any("Unnamed" in str(col) for col in df.columns) and not df.empty:
        df.columns = df.iloc[0]
        df = df[1:].reset_index(drop=True)
        df.columns.name = None

    llm = ChatGroq(
        temperature=0,
        model=MODEL,
        api_key=active_api_key
    )

    agent = create_pandas_dataframe_agent(
        llm, 
        df, 
        verbose=False,
        allow_dangerous_code=True,
        agent_type="tool-calling",
        max_iterations=25,
        max_execution_time=60
    )

    instructions = """
You are an expert business intelligence data analyst interacting with a pandas dataframe `df`.
You must query `df` using the `python_repl_ast` tool to find the answer — NEVER guess or answer from assumption.

CRITICAL RULES:
1. SCHEMA FIRST: Inspect the dataframe's actual structure — check `df.columns.tolist()` and `df.dtypes` to learn real column names.
2. COLUMN/VALUE MATCHING: If the user references a concept, search for the closest match before answering.
3. EXACT MATH: Always compute sums, counts, and aggregations directly via pandas — never estimate.
4. MISSING DATA: If a column doesn't exist, state that clearly.

OUTPUT FORMAT:
You MUST return your final answer as EXACTLY ONE JSON object:
{
  "summary": "Complete summary of findings.",
  "risks": ["Risk 1 based on data", "Risk 2 based on data"],
  "bottlenecks": ["Bottleneck 1", "Bottleneck 2"],
  "recommendations": ["Recommendation 1", "Recommendation 2"],
  "recommended_visualization": "priority_distribution",
  "chart": {
    "type": "bar",
    "title": "Descriptive title",
    "x_key": "actual column name used for grouping",
    "y_key": "count",
    "data": []
  }
}
NOTE: "risks", "bottlenecks", "recommendations", and "chart" are optional. If you include "chart", leave "data" empty; the backend will compute it based on "x_key".
"""

    full_query = f"{instructions}\n\nUser Query: {query}"
    
    try:
        result = agent.invoke(full_query)
        raw_output = result.get("output", "")
        return _normalize_agent_output(raw_output, df)
    except Exception as e:
        error_msg = str(e)
        if "Failed to call a function" in error_msg or "Could not parse" in error_msg:
            return json.dumps({"answer": "Could not interpret that as a specific data request. Please ask a specific question about the dataset."})
        return json.dumps({"answer": f"Data Agent encountered an error: {error_msg}"})
