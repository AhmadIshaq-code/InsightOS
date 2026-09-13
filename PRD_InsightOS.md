# Product Requirements Document (PRD)

# InsightOS — AI-Powered Universal Data Analytics & Business Intelligence Platform

**Document Version:** 1.0.1 (Production-Deployed MVP Audit)  
**Status:** Implemented & Verified in Production MVP  
**Frontend Production URL:** [https://insight-os-taupe.vercel.app](https://insight-os-taupe.vercel.app)  
**Backend Production URL:** [https://insightos-production.up.railway.app](https://insightos-production.up.railway.app)  
**Target Audience:** Hackathon Judges, Technical Evaluators, Enterprise Investors, Core Engineering Team  

---

## 1. Executive Summary

**InsightOS** is an AI-powered universal business intelligence and conversational analytics platform engineered to solve the chronic disconnect between quantitative numerical data (spreadsheets, metrics, KPIs) and qualitative institutional knowledge (corporate policies, SOPs, audit reports).

Traditional business intelligence platforms (PowerBI, Tableau, Metabase) answer *"what happened?"* through static dashboards but require manual human analysis to uncover root causes and cannot contextualize metrics against business policies. Conversely, standard enterprise search and RAG tools answer *"what does the policy say?"* but hallucinate when asked to compute totals, trends, outlier thresholds, or projections.

InsightOS bridges this divide through an architectural tri-brain system:
1. **Data Brain:** A deterministic numerical calculation engine built upon Pandas and NumPy. It performs deterministic numerical computation for KPIs, statistical summaries, category aggregations, outlier detection via Interquartile Range (IQR), and linear trend forecasting, validated by automated regression test suites. **The LLM is strictly prohibited from inventing numbers.**
2. **Knowledge Brain:** An incremental, vector-grounded document intelligence engine powered by PyMuPDF, Sentence-Transformers (`all-MiniLM-L6-v2`), and Chroma vector database. It guarantees that all text claims cite verified page-level document evidence without hallucinated sources.
3. **Reasoning Brain:** A secure intent classification and multi-tool orchestration engine that analyzes natural language queries, classifies intent (`DATA`, `DOCS`, `HYBRID`, `GENERAL`), invokes validated tools from a closed tool registry, and synthesizes structured executive answers clearly distinguishing **Data Findings**, **Document Evidence**, and **AI Interpretation**.

The platform is a production-deployed MVP, verified with end-to-end regression suites, and deployed with a Vite/React 19 frontend on Vercel and a FastAPI backend on Railway.

---

## 2. Product Vision

To become the definitive, hallucination-free AI Operating System for enterprise analytics—where every business decision is grounded in verifiable mathematical data and corroborated by official organizational documents, delivered through an intuitive executive dashboard and conversational AI analyst.

---

## 3. Problem Statement

Modern organizations suffer from fragmented intelligence:
- **Spreadsheet & Tabular Data Silos:** Financial ledgers, sales logs, inventory sheets, and workforce metrics reside in disparate CSV, XLS, and XLSX files. Analyzing them requires pivot tables, custom scripts, or rigid dashboards that take days to configure.
- **Unstructured Document Silos:** Critical business context—standard operating procedures (SOPs), vendor SLAs, procurement guidelines, compliance frameworks, and executive memos—reside in unstructured PDF documents.
- **The "Why" Gap in BI:** A traditional BI dashboard shows that quarterly revenue dropped by 18% in a specific quarter, but cannot explain why. An analyst must manually scour incident logs or change-of-policy memos to find the underlying operational reason.
- **The Hallucination Danger of Generative AI:** Naive LLM chatbots applied to business data hallucinate calculations (inventing revenue sums or averages) or fabricate document policies and citations, creating severe operational and legal risks.

---

## 4. Proposed Solution

InsightOS eliminates these challenges through:
- **Universal Drag-and-Drop Ingestion:** Instant upload and profiling of CSV, XLS, and XLSX tabular files, alongside unstructured PDF documents.
- **Deterministic-First Computation:** Offloading all math to Python's numerical stack (Pandas/NumPy) via strict typed tool schemas (Pydantic), ensuring that every metric, sum, percentage, outlier, and forecast point is mathematically derived.
- **Incremental Knowledge Retrieval:** Page-aware text extraction, deterministic overlap chunking, SHA-256 deduplication, and vector search with Chroma.
- **Hybrid AI Synthesis:** Coordinated multi-tool execution combining tabular aggregations and document search into a unified response template with verifiable citations and confidence scores.
- **Executive Glassmorphic Interface:** A modern, high-density dashboard featuring automatic KPI cards, dynamic area/bar charts, outlier alerts, forecast projections, and a responsive AI Analyst chat interface.

---

## 5. Target Users & Personas

| Persona | Core Pain Point | How InsightOS Solves It |
| :--- | :--- | :--- |
| **Business & Financial Analyst** | Spends 60% of time wrangling messy spreadsheets and matching numbers against policy documents. | Automates instant profiling, KPI extraction, category rankings, and IQR anomaly scans in seconds. |
| **Startup Founder / Executive** | Needs quick, high-level answers across both financial sheets and investor updates without learning SQL or BI software. | Uses the conversational AI Analyst to ask hybrid questions like *"What was our total revenue, and what does our hiring policy say about bonuses?"* |
| **Operations Manager** | Tracks logistics, inventory discrepancies, and SOP compliance across multiple locations. | Leverages deterministic IQR anomaly detection to spot metric spikes and pulls exact SOP response steps. |
| **Compliance & Audit Lead** | Needs absolute auditability; cannot tolerate LLM hallucinations or fabricated citations. | Relies on InsightOS's verifiable page citations, deterministic KPIs, and source transparency. |

---

## 6. Goals

- **Deterministic Numerical Facts:** All numerical facts, sums, statistics, outlier bounds, and trend slopes must originate from the Data Brain via Pandas/NumPy execution rather than LLM token prediction.
- **Grounded Document Evidence:** Document claims and citations must correspond strictly to retrieved chunks from indexed documents with verifiable page numbers.
- **Multi-Modal Tri-Brain Orchestration:** Successfully classify and route user inquiries across `DATA`, `DOCS`, `HYBRID`, and `GENERAL` intents without requiring manual mode toggles.
- **Target Performance Benchmark:** Sub-second analytical computations for common tabular datasets (< 50,000 rows) and fast vector retrieval for indexed documents.
- **Production Resilience:** Strict type validation, automated health checks, CORS compliance, and secure environment key handling.

---

## 7. Non-Goals (Explicitly Out of Scope for MVP)

To maintain focus and deliver a robust MVP, the following are explicitly out of scope:
- **No Multi-Tenancy or User Authentication:** No login, user registration, JWT sessions, or team permission roles.
- **No External SQL / Live Cloud Connectors:** No live connectors to Snowflake, PostgreSQL, BigQuery, Salesforce, or Google Sheets.
- **No Arbitrary Python Execution:** No dynamic `eval()`, `exec()`, or unstructured LangChain Pandas agents.
- **No Complex Background Queue Infrastructure:** No Celery, Redis queues, or Kafka streaming brokers.
- **No Multivariate Machine Learning Forecasts:** No ARIMA, Prophet, or Deep Learning models for time-series forecasting (deterministic linear trend projection is implemented).
- **No Mobile Applications:** Mobile responsive web UI only; no native iOS or Android apps.

---

## 8. MVP Scope

The current implemented MVP covers:
1. **Universal Dataset Upload & Profiling:** CSV, XLS, XLSX formats up to 50MB.
2. **Deterministic Data Brain:** KPIs, descriptive statistics, category aggregations, top/bottom rankings, time trends.
3. **Data Quality Engine:** Automated calculation of quality score (0-100%), missing cell counts, duplicate rows, empty rows/columns, and constant columns.
4. **IQR Anomaly Detection:** Interquartile Range ($Q1 - 1.5 \times IQR$, $Q3 + 1.5 \times IQR$) identification of outliers with temporal and categorical context.
5. **Linear Trend Forecasting:** Ordinary Least Squares ($y = mx + c$) projection for 1-24 future periods with frequency auto-detection and minimum observation checks.
6. **PDF Knowledge Brain:** Multi-document PyMuPDF parsing, text chunking, SHA-256 duplicate detection, Chroma vector store indexing, semantic search, and document-level deletion.
7. **Reasoning Brain & Safe AI Tools:** Intent classification, closed tool registry, Pydantic argument validation, and grounded response synthesis with Groq LLaMA 3.3 70B.
8. **Executive Analytics Dashboard:** KPI spotlight, time-series area charts, category bar charts, low-performer tables, interactive anomaly detection panel, and forecasting projection charts.
9. **AI Analyst Chat UI:** Interactive chat interface with dataset dropdown selector, structured response rendering, citations badges, and sample question prompts.
10. **Cloud Production Deployment:** FastAPI backend hosted on Railway; React 19 frontend hosted on Vercel with production CORS configuration.

---

## 9. Key User Journeys

```
[Journey 1: Dataset Exploration]
User uploads CSV/XLSX -> Data Brain profiles types & quality -> Dashboard displays KPI cards & charts

[Journey 2: Intelligence & Forecasting]
User navigates to Dashboard -> Selects metric in Intelligence section -> Detects IQR anomalies & forecasts next periods

[Journey 3: Document Grounding]
User uploads PDF handbook -> Knowledge Brain chunks & vectors to Chroma -> User searches semantic snippets with page citations

[Journey 4: Hybrid AI Analyst Chat]
User asks: "Why did revenue dip in Q1 and what does our incident SOP require?"
  -> Reasoning Brain routes to HYBRID
  -> Calls analyze_dataset(metric_column="Revenue", operation="trend")
  -> Calls search_documents(query="incident reporting policy")
  -> Synthesizes structured answer with Data Findings, Document Evidence, and Page Citations
```

---

## 10. Functional Requirements Matrix

| ID | Module | Feature Description | Priority | Acceptance Criteria |
| :--- | :--- | :--- | :--- | :--- |
| **FR-001** | Ingestion | Multi-format dataset upload | Critical | Accepts CSV, XLSX, XLS; rejects unsupported formats with HTTP 400. |
| **FR-002** | Data Brain | Semantic type detection | Critical | Classifies columns as numeric, datetime, categorical, or boolean. |
| **FR-003** | Data Brain | Automated Data Quality scoring | High | Computes authoritative health score (0-100%), null percentages, duplicates, empty rows/columns, constant columns. |
| **FR-004** | Data Brain | Identifier column exclusion | High | Excludes ID, UUID, and code columns from business KPI aggregations. |
| **FR-005** | Data Brain | Deterministic KPIs | Critical | Calculates total, average, min, median, max via Pandas aggregation. |
| **FR-006** | Data Brain | Category rankings | High | Computes top-N and bottom-N categories sorted descending/ascending. |
| **FR-007** | Data Brain | Time-series trend aggregation | High | Aggregates metric over date column with auto/day/week/month/quarter/year frequency. |
| **FR-008** | Data Brain | Deterministic IQR anomaly detection | High | Identifies values strictly outside $[Q1 - 1.5 \times IQR, Q3 + 1.5 \times IQR]$. |
| **FR-009** | Data Brain | Linear trend forecasting | High | Fits $y = mx + c$ over time series, projects 1–24 periods, flags trend direction (`up`, `down`, `flat`). |
| **FR-010** | Knowledge Brain | PDF document indexing | Critical | Extracts text via PyMuPDF, chunks with RecursiveCharacterTextSplitter (1000/200), generates embeddings. |
| **FR-011** | Knowledge Brain | SHA-256 duplicate detection | Medium | Prevents duplicate vectorization of previously indexed PDFs. |
| **FR-012** | Knowledge Brain | Incremental document deletion | High | Deletes specific document vectors from Chroma without wiping other documents. |
| **FR-013** | Knowledge Brain | Page-grounded semantic search | Critical | Returns ranked text snippets with document ID, filename, and exact page number. |
| **FR-014** | Reasoning Brain | Multi-intent classification | Critical | Classifies queries into `DATA`, `DOCS`, `HYBRID`, or `GENERAL`. |
| **FR-015** | Reasoning Brain | Closed tool registry execution | Critical | Executes only registered tools with Pydantic argument validation. |
| **FR-016** | Reasoning Brain | Structured multi-evidence synthesis| Critical | Separates Data Findings, Document Evidence, AI Interpretation, and Citations. |
| **FR-017** | Dashboard | Dynamic KPI & Chart Rendering | High | Recharts rendering of area trends, category bars, and metric spotlights. |
| **FR-018** | Dashboard | Embedded Intelligence Panel | High | UI controls to trigger IQR anomaly detection and time-series forecasting. |
| **FR-019** | AI Chat | Conversational Analyst Interface | High | Message history, dataset context selector, sample prompts, and markdown tables. |
| **FR-020** | Platform | Production CORS & Configuration | Critical | Allows verified Vercel origins with credentials; blocks unauthorized origins. |

---

## 11. Data Brain Requirements

### 11.1 Column Semantic Typing
The Data Brain inspects tabular data to categorize columns into four operational types:
- **Numeric:** Floating point and integer metrics suitable for aggregation (Revenue, Price, Cost, Profit).
- **Datetime:** Temporal timestamps parsed via Pandas `to_datetime(errors='coerce')` for trend analysis.
- **Categorical:** Low-cardinality text or discrete values for group-by operations (Product, Category, Department).
- **Boolean:** Binary flags (True/False, 1/0).

### 11.2 Anti-Explosion & Identifier Heuristic
To prevent dashboard pollution and mathematically meaningless aggregations (such as summing `Employee_ID` or `Postal_Code`):
- Any numeric column whose name contains `id`, `code`, `zip`, `ssn`, `key`, `number`, or `no` is categorized as an Identifier.
- If a numeric column has a uniqueness ratio $> 90\%$ of total row count, it is flagged as an ID.
- Identifiers are preserved for row previews and detail inspection, but **automatically excluded from KPI cards and default metric aggregations**.

### 11.3 Authoritative Data Quality Score Formula
The deterministic Data Quality Health Score is implemented in `dataset_service.py` as:

$$\text{Base Score} = 100.0$$

$$\text{Deductions} = \left(\text{missing\_percentage} \times 0.4\right) + \left(\text{duplicate\_percentage} \times 0.4\right) + \left(\text{empty\_columns} \times 5.0\right) + \left(\text{empty\_rows} \times 5.0\right) + \left(\text{constant\_columns} \times 2.0\right)$$

$$\text{Quality Score} = \max\left(0.0, \min\left(100.0, \text{round}\left(100.0 - \text{Deductions}, 1\right)\right)\right)$$

### 11.4 Anomaly Detection (IQR Method)
Implemented in `data_brain.py`:
- Calculates first quartile ($Q_1$, 25th percentile) and third quartile ($Q_3$, 75th percentile) on valid, non-null, non-infinite numeric values.
- Interquartile Range: $\text{IQR} = Q_3 - Q_1$.
- Lower bound: $\text{lower\_bound} = Q_1 - 1.5 \times \text{IQR}$.
- Upper bound: $\text{upper\_bound} = Q_3 + 1.5 \times \text{IQR}$.
- An observation is flagged as anomalous strictly if: $\text{value} < \text{lower\_bound}$ or $\text{value} > \text{upper\_bound}$.
- **Edge cases:** If valid observations are fewer than 4, anomaly count defaults to 0 and IQR is 0.0 without throwing errors.
- Results return outlier records sorted by distance from normal boundary (most extreme first), with configurable limit between 1 and 1000 (default 20).

### 11.5 Time-Series Forecasting (Linear Trend)
Implemented in `data_brain.py`:
- Aggregates historical metrics by frequency (`auto`, `day`, `week`, `month`, `quarter`, `year`).
- **Minimum Historical Observation Requirement:** Requires at least 3 historical time periods ($n \ge 3$). If fewer than 3 periods exist, raises `DataBrainError("INSUFFICIENT_DATA", ...)`.
- Fits Ordinary Least Squares (OLS) linear trend regression:
  $$m = \frac{\sum_{i=1}^n (x_i - \bar{x})(y_i - \bar{y})}{\sum_{i=1}^n (x_i - \bar{x})^2}, \quad c = \bar{y} - m\bar{x}$$
- Future projected period values: $\hat{y}_{\text{fut}} = m \cdot x_{\text{fut}} + c$.
- Supported forecast horizon: 1 to 24 periods (default 3).
- Trend direction classification:
  - $\text{slope} > 0.001 \rightarrow \text{"up"}$
  - $\text{slope} < -0.001 \rightarrow \text{"down"}$
  - Otherwise $\rightarrow \text{"flat"}$
- Note: This is a deterministic linear regression model for directional baseline projection; it does not compute confidence intervals or model complex seasonal Fourier cycles in MVP.

---

## 12. Knowledge Brain Requirements

### 12.1 Ingestion & Processing Pipeline
1. **Validation:** Checks for valid PDF magic bytes and rejects corrupt or non-PDF files with HTTP 400. File size limit is enforced at 50MB.
2. **SHA-256 Hashing:** Computes content hash of uploaded PDF. If an identical hash already exists in metadata index, skips vectorization and returns existing document record.
3. **Page-Aware Extraction:** Iterates through pages via PyMuPDF (`fitz`), preserving text blocks and metadata tagging (`page_number: N`).
4. **Deterministic Chunking:** Employs `RecursiveCharacterTextSplitter` with **chunk size: 1000 characters** and **chunk overlap: 200 characters** to preserve sentence context.
5. **Vectorization:** Generates 384-dimensional dense vector embeddings using `sentence-transformers/all-MiniLM-L6-v2`.
6. **Chroma Storage:** Persists embeddings into the collection `insightos_knowledge` in local persistent storage (`chroma_db/`).

### 12.2 Semantic Search & Retrieval
- Computes cosine distance between user query embedding and indexed chunk embeddings.
- Returns top-$K$ chunks (default: 5) formatted with:
  - `document_id`: UUID of the parent document.
  - `filename`: Original PDF name.
  - `page`: 1-indexed page number.
  - `content`: Raw text snippet.
  - `score`: Relevance similarity score.

---

## 13. Reasoning Brain Requirements

### 13.1 Intent Classification Engine
The Reasoning Brain analyzes user questions and resolves intent:
- **`DATA`:** Queries concerning numerical statistics, totals, averages, comparisons, rankings, time trends, anomalies, or forecasts (e.g., *"What is total revenue by category?"*, *"Detect anomalies in sales"*).
- **`DOCS`:** Queries inquiring about rules, SOPs, handbooks, guidelines, security policies, or definitions (e.g., *"What is the policy for incident escalation?"*).
- **`HYBRID`:** Queries combining empirical facts and qualitative explanations (e.g., *"How did revenue perform and what does the policy say about reporting incidents?"*).
- **`GENERAL`:** General conversational greetings or system capability questions.

### 13.2 Closed Tool Registry (`ai_tools.py`)
No raw shell or dynamic Pandas code is executed. The Reasoning Brain routes calls strictly through six approved tools:
1. `analyze_dataset`: Executes aggregations, rankings, statistics, and trends on a structured dataset.
2. `get_kpis`: Retrieves pre-computed deterministic business KPIs.
3. `get_data_quality`: Returns completeness, missing percentages, and quality scores.
4. `detect_anomalies`: Runs IQR outlier detection on a selected numeric column.
5. `forecast_metric`: Computes linear trend projection for 1–24 future periods.
6. `search_documents`: Executes Chroma vector search over indexed PDF documents.

Each tool call is validated against a strict **Pydantic schema** prior to execution. If validation fails, execution aborts with a structured error.

---

## 14. AI Analyst Synthesis Requirements

The AI Analyst synthesizes multi-tool outputs into a grounded, structured template:

```markdown
### Summary
[Executive summary answering the user's core inquiry]

### Data Findings
- [Deterministic numerical facts, totals, averages, or outlier counts derived from Data Brain]
- [Category breakdowns or time-series trajectory calculated via Pandas]

### Document Evidence
- [Verbatim or paraphrased policy/procedural evidence retrieved from Knowledge Brain]

### AI Interpretation & Recommendations
- [Analytical synthesis connecting data trends with documented policies or operating procedures]

### Sources & Citations
- [filename.pdf — Page N]
- [dataset: original_filename.csv]
```

---

## 15. Executive Dashboard Requirements

The frontend dashboard provides an interactive analytics command center:
1. **Executive Header & Dataset Selector:** Quick switching between uploaded datasets, displaying original filename, total rows, columns, and upload timestamp.
2. **Global Data Health Cards:** Visual badges for Quality Score (0-100%), Missing Data Percentage, and Duplicate Rows Percentage.
3. **Metric Spotlight Grid:** Automatic generation of KPI cards displaying Total, Average, Minimum, Median, and Maximum for the primary business metric.
4. **Time Trend Area Chart:** Recharts Area chart with gradient fills, custom hover tooltips, and frequency switching (Daily, Monthly, Auto).
5. **Category Performance Bar Chart:** Bar chart visualizing categorical group breakdowns.
6. **Underperforming Segments Table:** Dedicated view identifying the lowest-ranking categories.
7. **Intelligence Section — Anomaly Detection:** Interactive controls to select metric, date column, and dimension; one-click detection displaying outlier counts, IQR bounds, and detailed tabular breakdown.
8. **Intelligence Section — Forecasting:** Controls to select horizon periods (1 to 24); dual-line chart visualizing historical data and projected trend lines with standard disclaimer.

---

## 16. Security & Safety Requirements

| Protection Area | Implemented Mechanism |
| :--- | :--- |
| **No Arbitrary Code Execution** | No dynamic `eval()`, `exec()`, or dynamic Pandas code agents. All analytics run through static, pre-compiled Pandas functions. |
| **Closed Tool Registry** | LLM cannot execute arbitrary system functions; tools are mapped against a hardcoded registry dictionary. |
| **Pydantic Argument Validation** | Tool inputs are validated for types, value ranges (e.g., periods 1–24, limit 1–1000), and non-empty strings before execution. |
| **Filesystem Safety** | `sanitize_filename` removes path traversal components (`../`), and paths are verified to remain within designated upload directories (`uploads/datasets` and `uploads/documents`). |
| **API Key Isolation** | Groq API keys are handled server-side via environment variables or explicit per-request parameters. **Never exposed in frontend bundles.** |
| **Upload Guardrails** | File format validation (CSV, XLSX, XLS, PDF) and size limit enforcement (50MB maximum). |
| **CORS Restriction** | Production CORS whitelist strictly restricts origins to verified Vercel domains (`https://insight-os-taupe.vercel.app`) and local development ports. Wildcard `allow_origins=["*"]` is not used. |

---

## 17. Non-Functional Requirements (NFRs)

- **Performance (Target Benchmarks):** Designed for low-latency analytical computation on tabular files up to 50,000 rows and vector search retrieval over indexed PDF collections.
- **Reliability:** Graceful error handling across all endpoints. Datasets with missing columns or invalid dates return structured HTTP 400 responses with descriptive error codes (`INVALID_COLUMN`, `NON_NUMERIC_METRIC`, `INVALID_DATETIME_COLUMN`).
- **Explainability:** Numerical figures in the dashboard or chat response map directly to underlying Pandas computations. Document statements cite indexed chunks and page numbers.
- **Responsive Design:** Dark-mode glassmorphic interface built with Tailwind CSS v4, optimized for desktop displays and tablet viewports.

---

## 18. System Architecture

```
+-----------------------------------------------------------------------------------+
|                                  USER INTERFACE                                   |
|                        React 19 + Vite 8 + Tailwind CSS v4                        |
|   [Upload Page]          [Executive Dashboard]            [AI Analyst Chat]       |
+-----------------------------------------------------------------------------------+
                                         |
                                         | HTTPS / REST / JSON
                                         v
+-----------------------------------------------------------------------------------+
|                                FASTAPI BACKEND                                    |
|                         FastAPI 0.115 + Uvicorn 0.30                              |
|   - CORS Middleware (Production Vercel + Local Origins)                           |
|   - Multipart File Upload Handlers (CSV, XLSX, PDF)                               |
|   - Error Formatter & Exception Middleware                                        |
+-----------------------------------------------------------------------------------+
         |                                |                               |
         v                                v                               v
+------------------+             +------------------+            +------------------+
|    DATA BRAIN    |             | KNOWLEDGE BRAIN  |            | REASONING BRAIN  |
|  (data_brain.py) |             |(knowledge_service|            |(reasoning_brain) |
|                  |             |       .py)       |            |                  |
| - Dataset Profiler             | - PyMuPDF Parser |            | - Intent Router  |
| - KPI Engine     |             | - Recursive Chunk|            |   (DATA/DOCS/    |
| - IQR Outliers   |             |   (1000 / 200)   |            |    HYBRID)       |
| - Linear Trend   |             | - MiniLM-L6-v2   |            | - Closed Tools   |
|   Forecaster     |             | - Chroma Vector  |            | - Groq LLaMA 3.3 |
| - Pandas / NumPy |             |   ("insightos_   |            | - Multi-Evidence |
|                  |             |    knowledge")   |            |   Synthesis      |
+------------------+             +------------------+            +------------------+
         |                                |                               |
         +--------------------------------+-------------------------------+
                                         |
                                         v
                         +-------------------------------+
                         |      STRUCTURED EVIDENCE      |
                         |  (Data Facts + Doc Citations) |
                         +-------------------------------+
                                         |
                                         v
                         +-------------------------------+
                         |   GROUNDED EXECUTIVE ANSWER   |
                         +-------------------------------+
```

---

## 19. End-to-End Data Flow

### 19.1 Tabular Ingestion Flow
1. User uploads a `.csv`, `.xlsx`, or `.xls` file on the upload interface.
2. Axios posts multipart form-data to `POST /api/datasets/upload`.
3. `dataset_service.py` validates format, sanitizes filename, and writes file to `uploads/datasets/{uuid}.ext`.
4. Profiler detects semantic types, computes nulls, duplicates, empty elements, and calculates the authoritative Quality Score.
5. Writes metadata profile to `uploads/datasets/{uuid}.meta.json`.
6. Dashboard fetches profile, summary (`GET /api/datasets/{uuid}/summary`), and KPIs (`GET /api/datasets/{uuid}/kpis`).
7. Recharts renders KPI spotlight cards, time trend graphs, and category distributions.

### 19.2 PDF Knowledge Flow
1. User uploads a PDF document on the documents interface.
2. Axios posts multipart form-data to `POST /api/documents/upload`.
3. `knowledge_service.py` validates PDF headers, extracts text page-by-page with PyMuPDF.
4. Splits text using `RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)`, tracking 1-indexed `page_number`.
5. Embeddings generated via `sentence-transformers/all-MiniLM-L6-v2`.
6. Chunks persisted into Chroma collection `insightos_knowledge` in `chroma_db/`.

### 19.3 Hybrid AI Query Flow
1. User submits a multi-part query through the AI Analyst chat interface.
2. Frontend posts payload to `POST /api/chat`.
3. `reasoning_brain.py` classifies the query as `HYBRID`.
4. Dispatches tool execution:
   - Tool 1: `analyze_dataset` (e.g. time trend or category aggregation on the selected dataset).
   - Tool 2: `search_documents` (semantic search over indexed PDF documents).
5. Gathers deterministic findings and retrieved text chunks with document citations.
6. Synthesizes a structured response via Groq LLaMA 3.3 70B separating Data Findings and Document Evidence.
7. Returns response with citation metadata to the chat UI.

---

## 20. API Overview

| Endpoint | Method | Purpose | Input / Parameters | Response Structure |
| :--- | :--- | :--- | :--- | :--- |
| `/api/health` | GET | Service health check | None | `{"status": "ok", "service": "InsightOS Core API", "supported_datasets": [...]}` |
| `/api/chat` | POST | Conversational AI analyst query | `ChatRequest(query, api_key, dataset_id, document_id)` | `{"status": "success", "response": {...}}` |
| `/api/datasets/upload` | POST | Upload CSV/Excel dataset | `file: UploadFile` | `{"status": "success", "dataset": {...}, "quality": {...}, "columns": [...]}` |
| `/api/datasets` | GET | List all active datasets | None | `{"status": "success", "datasets": [...]}` |
| `/api/datasets/{dataset_id}/profile` | GET | Get full dataset profile | `dataset_id: str` | `{"status": "success", "profile": {...}}` |
| `/api/datasets/{dataset_id}/summary` | GET | Get structural data summary | `dataset_id: str` | `{"status": "success", "dataset_id": str, "result": {...}}` |
| `/api/datasets/{dataset_id}/kpis` | GET | Compute business KPIs | `dataset_id: str` | `{"status": "success", "dataset_id": str, "result": {"kpis": {...}}}` |
| `/api/datasets/{dataset_id}/statistics/{column}` | GET | Descriptive numeric stats | `dataset_id: str, column: str` | `{"status": "success", "dataset_id": str, "result": {...}}` |
| `/api/datasets/{dataset_id}/aggregate` | POST | Group-by aggregation | `AggregateRequest(category_column, metric_column, aggregation)` | `{"status": "success", "dataset_id": str, "result": [...]}` |
| `/api/datasets/{dataset_id}/top` | POST | Top-N categories | `CategoryRankRequest(category_column, metric_column, aggregation, limit)` | `{"status": "success", "dataset_id": str, "result": [...]}` |
| `/api/datasets/{dataset_id}/bottom` | POST | Bottom-N categories | `CategoryRankRequest(category_column, metric_column, aggregation, limit)` | `{"status": "success", "dataset_id": str, "result": [...]}` |
| `/api/datasets/{dataset_id}/trend` | POST | Time trend calculation | `TrendRequest(date_column, metric_column, aggregation, frequency)` | `{"status": "success", "dataset_id": str, "result": [...]}` |
| `/api/datasets/{dataset_id}/anomalies` | POST / GET | IQR outlier detection | `POST: AnomalyRequest(metric_column, date_column, dimension_column, limit)`<br>`GET: query params (metric_column, date_column, dimension_column, limit)` | `{"status": "success", "dataset_id": str, "result": {"anomalies": [...]}}` |
| `/api/datasets/{dataset_id}/forecast` | POST / GET | Linear trend projection | `POST: ForecastRequest(metric_column, date_column, periods, frequency)`<br>`GET: query params (metric_column, date_column, periods, frequency)` | `{"status": "success", "dataset_id": str, "result": {"forecast": [...]}}` |
| `/api/datasets/{dataset_id}/preview` | GET | Safe row preview | `dataset_id: str, limit: int = 20` | `{"status": "success", "preview": [...]}` |
| `/api/datasets/{dataset_id}` | DELETE | Delete dataset and profile | `dataset_id: str` | `{"status": "success", "message": "..."}` |
| `/api/documents/upload` | POST | Upload and index PDF | `file: UploadFile` (alias: `/api/upload`) | `{"status": "success", "document": {...}, "id": str, "name": str}` |
| `/api/documents` | GET | List all indexed documents | None | `{"status": "success", "documents": [...], "files": [...]}` |
| `/api/documents/{doc_id_or_name}` | DELETE | Incremental vector deletion | `doc_id_or_name: str` | `{"status": "success", "message": "..."}` |
| `/api/documents/search` | POST | Semantic vector search | `DocumentSearchRequest(query, top_k, document_id)` | `{"status": "success", "query": str, "results": [...]}` |
| `/api/sync` | POST | Legacy compatibility stub | `SyncRequest(url)` | `{"status": "info", "message": "External live syncing archived to legacy for MVP."}` |

---

## 21. Technology Stack

### 21.1 Frontend (`insight-agent/package.json`)
- **Core Framework:** React 19.2.7 (`react`, `react-dom`)
- **Build Tool:** Vite 8.0.12 (`@vitejs/plugin-react`, `@tailwindcss/vite`)
- **Styling:** Tailwind CSS 4.3.0, Autoprefixer 10.5.0, PostCSS 8.5.15
- **Charts & Data Visualization:** Recharts 3.8.1
- **Icons:** Lucide React 1.17.0, React Icons 5.6.0
- **Routing:** React Router DOM 7.17.0
- **HTTP Client:** Axios 1.17.0 with dynamic `VITE_API_URL` environment resolution
- **File Upload Dropzone:** React Dropzone 15.0.0
- **Markdown Rendering:** React Markdown 10.1.0, Remark GFM 4.0.1
- **State Management:** Zustand 5.0.14

### 21.2 Backend (`requirements.txt`, `pyproject.toml`)
- **API Framework:** FastAPI >= 0.115.0
- **ASGI Server:** Uvicorn >= 0.30.0
- **Multipart Form Support:** Python-Multipart >= 0.0.9
- **Validation & Serialization:** Pydantic >= 2.7.0
- **Tabular Data Stack:** Pandas >= 2.2.0, NumPy >= 1.26.0, OpenPyXL >= 3.1.0, XLRD >= 2.0.1
- **Document Processing:** PyMuPDF >= 1.24.0
- **Vector Database:** ChromaDB >= 0.5.0, LangChain-Chroma >= 0.1.4
- **Text Splitters:** LangChain-Text-Splitters >= 0.3.0
- **Embeddings:** Sentence-Transformers >= 3.0.0 (`all-MiniLM-L6-v2`), LangChain-HuggingFace >= 0.1.0
- **LLM Provider & Orchestration:** Groq >= 0.11.0, LangChain-Groq >= 0.2.0, LangChain-Core >= 0.3.0 (Default model: `llama-3.3-70b-versatile`)
- **Environment Management:** Python-Dotenv >= 1.0.0

### 21.3 Cloud Deployment & Infrastructure
- **Frontend Hosting:** Vercel ([https://insight-os-taupe.vercel.app](https://insight-os-taupe.vercel.app))
- **Backend Hosting:** Railway Container PaaS ([https://insightos-production.up.railway.app](https://insightos-production.up.railway.app))
- **Version Control:** Git & GitHub (`AhmadIshaq-code/InsightOS`, branch `main`)

---

## 22. Success Metrics (Target & Evaluation Criteria)

| Metric Category | Target / Evaluation Criteria | Validation Mechanism |
| :--- | :--- | :--- |
| **Deterministic Computation** | Calculations match Pandas outputs | Automated regression tests asserting mathematical outputs against reference values. |
| **Zero Numerical Hallucination** | No unverified numbers in data answers | Prompt engineering and tool contracts ensure numerical facts derive from Data Brain outputs. |
| **Citation Grounding** | Citations match retrieved chunks | Grounding validation tests confirm citations match indexed document filenames and page numbers. |
| **Intent Routing Quality** | High classification accuracy | Automated test suite verifying intent classification across diverse sample queries for DATA, DOCS, HYBRID, and GENERAL. |
| **Ingestion Support** | Clean ingestion across file types | Unit tests verifying CSV, XLSX, and XLS parsing, column normalization, and quality scoring. |
| **Anomaly Detection Validity** | Strict IQR bounds compliance | Test assertions verifying flagged values strictly fall outside $[Q1 - 1.5 \times IQR, Q3 + 1.5 \times IQR]$. |
| **Forecast Consistency** | Valid OLS trend extrapolation | Test assertions verifying future points align with linear regression slope and intercept. |
| **Service Availability** | High uptime on Railway container | Health endpoint monitoring via `GET /api/health`. |

---

## 23. Testing & Quality Assurance

The repository includes a suite of automated unit, integration, and scenario tests:
1. `test_data_brain.py`: Deterministic assertions for summaries, KPIs, aggregations, identifier exclusion heuristics, and edge cases.
2. `test_dataset_service.py`: Filename sanitization, CSV and Excel XLSX profiling, authoritative data quality scoring on messy data, and preview generation.
3. `test_knowledge_service.py`: PDF document ingestion, text chunking, SHA-256 deduplication, vector similarity search, and document-level deletion.
4. `test_knowledge_api.py`: FastAPI TestClient integration tests for document upload, listing, filtered search, deletion isolation, and error validation.
5. `test_reasoning_brain.py`: Intent classification across sample test queries, missing context handling, closed tool routing, and citation grounding checks.
6. `test_reasoning_phase2.py`: Integration testing for hybrid query execution, tool plan execution, and synthesized grounded answers.
7. `test_anomaly_detection.py`: Mathematical verification of IQR outlier boundaries, normal datasets, outlier detection, and edge cases.
8. `test_forecasting.py`: Verification of linear trend regression, multi-period extrapolation, frequency aliasing, and minimum observation enforcement.
9. `test_cors.py`: FastAPI TestClient verification of preflight OPTIONS and GET CORS headers for production Vercel origin and localhost origins.
10. `test_dashboard_backend.py`: Verification of 12-column datasets, categorical-only datasets, anti-explosion heuristic, and error codes.

---

## 24. Deployment Configuration

### 24.1 Production Environment Variables
- **Backend (Railway):**
  - `GROQ_API_KEY`: API authentication key for Groq inference.
  - `GROQ_MODEL`: Model name (default `llama-3.3-70b-versatile`).
  - `PORT`: Assigned dynamically by Railway.
- **Frontend (Vercel):**
  - `VITE_API_URL`: Configured to `https://insightos-production.up.railway.app`.

### 24.2 Production CORS Configuration (`server.py`)
```python
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
```

---

## 25. Current Known Limitations (MVP)

1. **Ephemeral Container Storage:** In the default Railway deployment, uploaded datasets and Chroma vector data reside on the container filesystem. Without a configured Railway persistent volume, dynamic file storage resets upon container redeployments.
2. **File Size Boundary:** Optimized for datasets up to 50MB and common tabular analysis. Extremely large files may cause browser or memory constraints.
3. **Linear Forecasting Scope:** The forecast algorithm uses deterministic Ordinary Least Squares linear trend. It models baseline direction and trend slope, but does not capture complex multi-seasonal cycles or confidence interval bands.
4. **Single-Tenant MVP Scope:** No user login or separated private workspaces; all uploaded datasets in storage are accessible via the platform interface.

---

## 26. Future Roadmap

### Phase 2: Persistence, Auth & Cloud Storage *(Planned / Not Implemented in MVP)*
- User authentication and workspace isolation via Supabase / Auth0.
- Cloud object storage for uploaded files (AWS S3 / Cloudflare R2).
- PostgreSQL database for persistent dataset metadata and user chat history.
- Multi-variate seasonal forecasting using Prophet / NeuralProphet with confidence intervals.

### Phase 3: Team Collaboration & Integrations *(Planned / Not Implemented in MVP)*
- Multi-tenancy and Role-Based Access Control (Admin, Analyst, Viewer).
- Direct connectors for Google Sheets, PostgreSQL, Snowflake, and BigQuery.
- Automated email and Slack anomaly alerts on scheduled data syncs.
- Exportable executive PDF and PowerPoint summary report generation.

### Phase 4: Enterprise Intelligence *(Planned / Not Implemented in MVP)*
- Local LLM inference support (Ollama / vLLM) for on-prem air-gapped deployments.
- Auto-generated visual data stories with voice narration for executive briefings.
- Complex multi-agent debate architecture for predictive business scenario modeling.

---

## 27. Hackathon Demo Scenarios

### Demo Scenario 1: Sales Analytics & Executive Dashboard
- **Dataset:** Tabular sales data (`Date`, `Product`, `Category`, `Revenue`).
- **Flow:** Drag and drop file onto Upload screen $\rightarrow$ Quality score and column profiles computed $\rightarrow$ Navigate to "Dashboard".
- **Result:** KPI spotlight displays total, average, min, median, and max for revenue. Time trend area chart shows period trajectory, and category bar chart displays category distributions.

### Demo Scenario 2: Deterministic IQR Anomaly Detection
- **Flow:** Scroll to "Intelligence" section in Dashboard $\rightarrow$ Select metric `Revenue` $\rightarrow$ Click "Detect Anomalies".
- **Result:** Returns detected outliers with exact metric values, calculated IQR bounds ($Q1 - 1.5 \times IQR$, $Q3 + 1.5 \times IQR$), and associated date/dimension context.

### Demo Scenario 3: Time-Series Metric Forecasting
- **Flow:** Select `Revenue`, set forecast periods (e.g., 3 or 4) $\rightarrow$ Click "Generate Forecast".
- **Result:** Dual-line chart renders historical data transitioning into projected future periods, displaying the calculated trend direction (`up`, `down`, or `flat`) and standard disclaimer.

### Demo Scenario 4: Policy Knowledge Extraction (PDF RAG)
- **Document:** Upload policy PDF (e.g. `sop_incident_response.pdf`, `it_security_policy.pdf`, or `hr_employee_handbook.pdf`).
- **Flow:** Upload PDF on Documents tab $\rightarrow$ Ask AI Analyst a procedural question regarding incident escalation or guidelines.
- **Result:** AI retrieves relevant policy section from the indexed PDF, citing the exact page number and text snippet without fabrication.

### Demo Scenario 5: Multi-Modal Hybrid Business Query
- **Question:** *"How did revenue perform and what does the company policy say about incident reporting?"*
- **Execution:** Reasoning Brain routes to `HYBRID`, calculates the empirical revenue trend from the dataset, searches the incident response SOP for protocol guidance, and generates a structured synthesis clearly separating Data Findings from Document Evidence.

---

## 28. Final MVP Summary

The InsightOS hackathon MVP is fully implemented and deployed in production:
- **Separation of Concerns:** Clear architectural division between deterministic tabular math (Data Brain) and vector retrieval (Knowledge Brain).
- **Production-Deployed MVP:** Live on Vercel and Railway with verified CORS, environment resolution, and comprehensive test coverage.
- **Modern Executive UX:** High-aesthetic glassmorphism dashboard providing actionable intelligence in seconds.
- **Architectural Scalability:** Modular design ready for enterprise database and cloud storage expansion in Phase 2.

---
*Authored by the InsightOS Core Development Team — September 2026*
