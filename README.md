# 🚀 InsightOS — AI-Powered Universal Data Analytics Platform

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688.svg)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-19-61DAFB.svg)](https://react.dev)
[![Vite](https://img.shields.io/badge/Vite-8-646CFF.svg)](https://vitejs.dev)
[![Groq](https://img.shields.io/badge/Groq-LLaMA--3.3--70B-F55036.svg)](https://groq.com)
[![Chroma](https://img.shields.io/badge/VectorDB-Chroma-red.svg)](https://www.trychroma.com)

InsightOS is an AI-powered universal business intelligence and data analytics platform designed to bridge unstructured corporate documents (PDF policies, SOPs, handbooks) with structured business metrics.

> **Status:** Phase 1 Foundation Complete (Cleaned & Normalized Core).

---

## ✨ Current Working Capabilities (MVP Foundation)

- **📄 PDF Ingestion & Chunking:** Fast page-by-page text extraction with `PyMuPDF` (`fitz`) and recursive sliding-window chunking (`1000` chars, `200` overlap).
- **🧠 Zero-Cost Local Embeddings:** Dense vector generation via HuggingFace `sentence-transformers/all-MiniLM-L6-v2` running entirely on CPU.
- **📚 Local Vector Store (Chroma DB):** Local persistent vector storage with similarity search and source attribution.
- **⚡ Ultra-Low Latency Inference:** Groq LPU integration running `llama-3.3-70b-versatile` with thread-safe explicit key passing.
- **🔀 Query Intent Classification:** Tri-mode routing (`DATA` vs `DOCS` vs `HYBRID`) for optimal handling of numeric vs document inquiries.
- **📊 Interactive Visualizations:** Dynamic Recharts (Bar, Pie, Line) with automatic responsive rendering.
- **💻 React 19 Frontend:** Modern dark-mode glassmorphic interface with markdown rendering, expandable citations, and drag-and-drop document upload.

---

## 🛣️ InsightOS Roadmap (Upcoming Phases)

The following advanced capabilities are scheduled for subsequent phases:

- [ ] **Phase 2: Universal Ingestion & Data Profiling**
  - Multi-sheet Excel (`.xlsx`, `.xls`) & dynamic multi-CSV dataset ingestion.
  - Automated schema understanding, column categorization, and data quality scoring.
  - Proactive metric/KPI summary cards upon dataset upload.
- [ ] **Phase 3: Deterministic Data Brain & Safe Analytics**
  - Safe, non-arbitrary code analytics using DuckDB and strict SQL compilation (retiring legacy pandas agent).
  - Outlier scanning, statistical anomaly detection, and time-series trend forecasting.
- [ ] **Phase 4: Executive Business Intelligence Dashboard**
  - Multi-panel executive canvas with interactive KPI cards and cross-dataset filtering.
  - True cross-modal synthesis combining regulatory/policy rules from PDFs with live financial/operational figures.
- [ ] **Phase 5: Streaming & Enterprise Polish**
  - Server-Sent Events (SSE) streaming for real-time token delivery in chat.
  - Exportable executive briefs (PDF/Markdown summaries).

---

## 📁 Project Structure

```text
├── config.py                 # Centralized configuration & normalized GROQ_API_KEY handler
├── server.py                 # FastAPI backend endpoints (/api/chat, /api/upload, /api/documents)
├── router.py                 # Intelligent query classification (DATA vs DOCS vs HYBRID)
├── rag_agent.py              # Chroma DB similarity search & cited Groq response generator
├── ingestion.py              # PyMuPDF extraction -> Text splitter -> Chroma DB indexing
├── data_agent.py             # (Legacy Prototype) Pandas DataFrame Agent for structured queries
├── main.py                   # Unified launcher for Uvicorn backend + Vite frontend
├── requirements.txt          # Clean, direct dependencies for backend RAG & analytics
├── .env.example              # Environment variable template (GROQ_API_KEY, VITE_API_URL)
├── test_live_data.csv        # Bundled sample dataset for testing
├── *.pdf                     # Bundled sample corporate PDFs (handbook, security, incident response)
│
├── legacy/                   # Archived scripts (live web pollers, GitHub scrapers, test scripts)
│   ├── README.md
│   ├── github_fetcher.py
│   ├── fetch_live_data.py
│   ├── live_handler.py
│   ├── infer.py
│   └── requirements.freeze.txt
│
└── insight-agent/            # React 19 + Vite + TailwindCSS Frontend Application
    ├── package.json
    ├── vite.config.js
    └── src/
        ├── App.jsx
        ├── components/
        │   ├── ChatInterface.jsx
        │   ├── MessageBubble.jsx  (Cleaned: Telemetry removed, Recharts renderer)
        │   └── Navigation.jsx
        ├── pages/
        │   ├── ChatPage.jsx
        │   ├── UploadPage.jsx
        │   └── SettingsPage.jsx
        ├── context/
        │   ├── APIContext.jsx
        │   ├── ChatContext.jsx
        │   └── FileContext.jsx
        └── services/
            └── groqService.js     (Normalized: VITE_API_URL target)
```

---

## 🚀 Quickstart

### 1. Configure Environment
Copy `.env.example` to `.env` and add your Groq API key:
```bash
cp .env.example .env
```
Edit `.env`:
```env
GROQ_API_KEY=gsk_your_actual_key_here
```

### 2. Install Backend Dependencies
```bash
pip install -r requirements.txt
```

### 3. Install Frontend Dependencies
```bash
cd insight-agent
npm install
cd ..
```

### 4. Launch Application
Run the unified launcher:
```bash
python main.py
```
- **Frontend:** http://localhost:5173
- **Backend API:** http://localhost:8000
- **Swagger Docs:** http://localhost:8000/docs
