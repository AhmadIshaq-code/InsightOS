"""
InsightOS Reasoning Brain (reasoning_brain.py)
Safe AI Tool Orchestration and Query Routing Layer.

Guarantees:
- Zero arbitrary code execution (no eval, exec, shell, or PandasAgent).
- Closed safe tool registry (ai_tools.TOOL_REGISTRY).
- Pydantic argument validation before tool execution.
- Deterministic-first intent routing (DATA, DOCS, HYBRID, GENERAL).
- Grounded multi-evidence synthesis (strictly separated Data Findings and Document Evidence).
- Backward compatibility: answer, sources, sources_text, tool_calls, data_facts, document_evidence, citations.
"""

import os
import re
from typing import Dict, List, Any, Optional
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate

from config import MODEL, get_groq_api_key
from dataset_service import list_all_datasets, get_dataset_profile_by_id
from data_brain import get_dataset_summary, get_kpis as db_get_kpis
from knowledge_service import search_documents as kb_search_documents
from ai_tools import (
    TOOL_REGISTRY,
    execute_tool,
    analyze_dataset_tool,
    get_kpis_tool,
    get_data_quality_tool,
    search_documents_tool,
    detect_data_operation_and_columns
)


class ReasoningBrain:
    """
    Safe orchestrator that plans, validates, and executes approved deterministic tools
    from ai_tools.TOOL_REGISTRY, and synthesizes grounded executive answers.
    """

    def __init__(self):
        pass

    # =========================================================================
    # 1. Dataset Resolution & Safe Helpers
    # =========================================================================

    def get_dataset_context(self, dataset_id: Optional[str] = None) -> Dict[str, Any]:
        """Retrieves deterministic dataset metadata."""
        target_id = dataset_id
        if not target_id:
            datasets = list_all_datasets()
            if datasets and "dataset_id" in datasets[0]:
                target_id = datasets[0]["dataset_id"]

        if not target_id:
            return {"available": False, "reason": "No datasets uploaded."}

        try:
            profile = get_dataset_profile_by_id(target_id)
            summary = get_dataset_summary(target_id)
            kpis = db_get_kpis(target_id)
            return {
                "available": True,
                "dataset_id": target_id,
                "filename": profile.get("dataset", {}).get("original_filename", "Dataset"),
                "summary": summary,
                "kpis": kpis.get("kpis", {}),
                "profile": profile
            }
        except Exception as e:
            return {"available": False, "reason": str(e), "dataset_id": target_id}

    def resolve_dataset_id(self, dataset_id: Optional[str] = None) -> Optional[str]:
        """
        Resolves the dataset ID via get_dataset_context().
        Never invents or fabricates an ID.
        """
        if dataset_id and str(dataset_id).strip():
            return str(dataset_id).strip()
        ctx = self.get_dataset_context(dataset_id)
        if ctx.get("available", False):
            return ctx.get("dataset_id")
        return None

    def analyze_dataset(
        self,
        question: str,
        dataset_id: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Delegates directly to approved analyze_dataset tool via execute_tool."""
        target_id = self.resolve_dataset_id(dataset_id)
        args = {"question": question, "dataset_id": target_id}
        args.update(kwargs)
        return execute_tool("analyze_dataset", args)

    def get_kpis(self, dataset_id: Optional[str] = None) -> Dict[str, Any]:
        """Delegates directly to approved get_kpis tool via execute_tool."""
        target_id = self.resolve_dataset_id(dataset_id)
        return execute_tool("get_kpis", {"dataset_id": target_id or ""})

    def get_data_quality(self, dataset_id: Optional[str] = None) -> Dict[str, Any]:
        """Delegates directly to approved get_data_quality tool via execute_tool."""
        target_id = self.resolve_dataset_id(dataset_id)
        return execute_tool("get_data_quality", {"dataset_id": target_id or ""})

    def detect_anomalies(
        self,
        dataset_id: Optional[str] = None,
        metric_column: str = "",
        date_column: Optional[str] = None,
        dimension_column: Optional[str] = None,
        limit: int = 20,
        **kwargs
    ) -> Dict[str, Any]:
        """Delegates directly to approved detect_anomalies tool via execute_tool."""
        target_id = self.resolve_dataset_id(dataset_id)
        args = {
            "dataset_id": target_id or "",
            "metric_column": metric_column,
            "date_column": date_column,
            "dimension_column": dimension_column,
            "limit": limit
        }
        args.update(kwargs)
        return execute_tool("detect_anomalies", args)

    def forecast_metric(
        self,
        dataset_id: Optional[str] = None,
        metric_column: str = "",
        date_column: str = "",
        periods: int = 3,
        frequency: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Delegates directly to approved forecast_metric tool via execute_tool."""
        target_id = self.resolve_dataset_id(dataset_id)
        args = {
            "dataset_id": target_id or "",
            "metric_column": metric_column,
            "date_column": date_column,
            "periods": periods,
            "frequency": frequency
        }
        args.update(kwargs)
        return execute_tool("forecast_metric", args)

    def search_documents(
        self,
        query: str,
        document_id: Optional[str] = None,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """Delegates to approved search_documents tool and returns chunk list."""
        res = execute_tool("search_documents", {"query": query, "document_id": document_id, "top_k": top_k})
        if isinstance(res, dict):
            return res.get("chunks", [])
        return []

    # =========================================================================
    # 2. Intent Classification (Deterministic-First)
    # =========================================================================

    def classify_intent(
        self,
        question: str,
        dataset_id: Optional[str] = None,
        document_id: Optional[str] = None,
        api_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Classifies incoming query into DATA, DOCS, HYBRID, or GENERAL.
        Deterministic heuristics are evaluated first.
        If ambiguous, invokes Groq temperature=0 fallback.
        Safe fallback: defaults to GENERAL if uncertain.
        """
        q = question.strip().lower()

        # 1. Deterministic GENERAL heuristics
        general_patterns = [
            r"^(hi|hello|hey|greetings|good\s+(morning|afternoon|evening))\b",
            r"\b(who are you|what are you|what can you do|how do you work|what is insightos|help me|capabilities)\b",
            r"^what is this (app|tool|system|platform)\b"
        ]
        if any(re.search(pat, q) for pat in general_patterns) and not any(k in q for k in ["salary", "sales", "policy", "handbook", "revenue", "dataset"]):
            return {
                "intent": "GENERAL",
                "confidence": 0.98,
                "reason": "Deterministic match: greeting or general capability question",
                "dataset_id": dataset_id,
                "document_id": document_id
            }

        # Keywords
        data_keywords = [
            "sales", "revenue", "salary", "salaries", "profit", "dataset", "rows",
            "columns", "data quality", "missing values", "null", "kpi", "kpis", "metrics",
            "average", "avg", "total", "sum", "mean", "median", "minimum", "maximum",
            "min", "max", "highest", "lowest", "top", "bottom", "trend", "how many employees",
            "most", "least", "generated", "units", "quantity", "breakdown", "product", "products",
            "category", "categories", "unusual", "anomaly", "anomalies", "outlier", "outliers", "abnormal",
            "forecast", "predict", "prediction", "projected", "projection", "future"
        ]
        docs_keywords = [
            "policy", "handbook", "sop", "procedure", "procedures", "guideline",
            "guidelines", "protocol", "security policy", "acceptable use", "code of conduct",
            "incident response", "incident reporting", "escalation", "vacation",
            "leave policy", "compliance", "employee handbook", "what does the", "according to the policy"
        ]

        has_data = any(re.search(r"\b" + re.escape(kw) + r"\b", q) for kw in data_keywords)
        has_docs = any(re.search(r"\b" + re.escape(kw) + r"\b", q) for kw in docs_keywords)

        # 2. Deterministic HYBRID detection
        hybrid_phrases = [
            r"why did .+ according to the policy",
            r"compare .+ (findings|results?) with .+ (policy|document)",
            r"explain .+ (result|finding|metric) using .+ (document|policy|handbook)",
            r"what does the (handbook|policy) say about .+ (lowest|highest|salary|sales|employee)",
            r"why might .+ (business result|sales|metric) be related to .+ (policy|handbook|procedure)"
        ]
        is_hybrid_phrase = any(re.search(pat, q) for pat in hybrid_phrases)

        if is_hybrid_phrase or (has_data and has_docs):
            return {
                "intent": "HYBRID",
                "confidence": 0.92,
                "reason": "Deterministic match: query cross-references structured data metrics with document evidence",
                "dataset_id": dataset_id,
                "document_id": document_id
            }

        # 3. Deterministic DATA detection
        if has_data and not has_docs:
            return {
                "intent": "DATA",
                "confidence": 0.95,
                "reason": "Deterministic match: query targets tabular dataset statistics/metrics",
                "dataset_id": dataset_id,
                "document_id": None
            }

        # 4. Deterministic DOCS detection
        if has_docs and not has_data:
            return {
                "intent": "DOCS",
                "confidence": 0.95,
                "reason": "Deterministic match: query asks for policies, SOPs, or textual document knowledge",
                "dataset_id": None,
                "document_id": document_id
            }

        # 5. LLM Fallback Classification (Only when deterministic scoring is ambiguous)
        active_key = get_groq_api_key(api_key)
        if active_key:
            try:
                llm = ChatGroq(temperature=0, model=MODEL, api_key=active_key)
                prompt = ChatPromptTemplate.from_messages([
                    ("system", """You are the master routing agent for InsightOS.
Classify the user question into exactly ONE of the following 4 categories:
1. 'DATA': Pure numerical calculations, statistics, counts, tabular aggregations, metrics, or spreadsheet profiling.
2. 'DOCS': Company policies, employee handbooks, SOPs, guidelines, legal/compliance text.
3. 'HYBRID': Questions requiring cross-referencing tabular data metrics with document policies/explanations.
4. 'GENERAL': Greetings, general chit-chat, or questions about what InsightOS is and how it works.

Respond with ONLY the single category name: DATA, DOCS, HYBRID, or GENERAL.
If you are uncertain, respond with GENERAL."""),
                    ("human", "{question}")
                ])
                res = (prompt | llm).invoke({"question": question})
                category = res.content.strip().upper()
                if category in ["DATA", "DOCS", "HYBRID", "GENERAL"]:
                    return {
                        "intent": category,
                        "confidence": 0.85,
                        "reason": f"LLM classification: {category}",
                        "dataset_id": dataset_id if category in ["DATA", "HYBRID"] else None,
                        "document_id": document_id if category in ["DOCS", "HYBRID"] else None
                    }
            except Exception:
                pass

        # Safe Fallback: Never guess DATA/DOCS/HYBRID if uncertain
        return {
            "intent": "GENERAL",
            "confidence": 0.40,
            "reason": "Classification uncertain; safe fallback to GENERAL to prevent unintended tool calls.",
            "dataset_id": None,
            "document_id": None
        }

    # =========================================================================
    # 3. Safe Tool Planning (Minimal Execution Rule)
    # =========================================================================

    def plan_tools(
        self,
        intent: str,
        question: str,
        dataset_id: Optional[str] = None,
        document_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Creates a minimal structured tool plan.
        Only approved tools from TOOL_REGISTRY are selected.
        """
        plan: List[Dict[str, Any]] = []
        q_lower = question.lower()

        if intent == "GENERAL":
            return []

        resolved_ds_id = self.resolve_dataset_id(dataset_id)

        if intent == "DATA":
            # Constraint 3: Minimal Tool Execution
            if any(k in q_lower for k in ["kpi", "kpis", "key performance indicator"]):
                plan.append({
                    "tool": "get_kpis",
                    "arguments": {"dataset_id": resolved_ds_id or ""}
                })
            elif any(k in q_lower for k in ["data quality", "quality score", "missing value", "missing values", "health score", "how good is my data"]):
                plan.append({
                    "tool": "get_data_quality",
                    "arguments": {"dataset_id": resolved_ds_id or ""}
                })
            elif any(k in q_lower for k in ["unusual", "anomaly", "anomalies", "outlier", "outliers", "abnormal"]):
                metric_col = ""
                date_col = None
                dim_col = None
                if resolved_ds_id:
                    ctx = self.get_dataset_context(resolved_ds_id)
                    profile = ctx.get("profile", {})
                    if profile:
                        detection = detect_data_operation_and_columns(question, profile)
                        if detection.get("metric_column"):
                            metric_col = detection["metric_column"]
                        if detection.get("date_column"):
                            date_col = detection["date_column"]
                        if detection.get("dimension_column"):
                            dim_col = detection["dimension_column"]

                plan.append({
                    "tool": "detect_anomalies",
                    "arguments": {
                        "dataset_id": resolved_ds_id or "",
                        "metric_column": metric_col,
                        "date_column": date_col,
                        "dimension_column": dim_col,
                        "limit": 20
                    }
                })
            elif any(k in q_lower for k in ["forecast", "predict", "prediction", "projected", "projection", "future", "look like next"]) or bool(re.search(r'\bnext\s+(?:\d+\s+)?(?:month|quarter|year|week|day)s?\b', q_lower)):
                metric_col = ""
                date_col = ""
                periods = 3
                freq = None
                if resolved_ds_id:
                    ctx = self.get_dataset_context(resolved_ds_id)
                    profile = ctx.get("profile", {})
                    if profile:
                        detection = detect_data_operation_and_columns(question, profile)
                        if detection.get("metric_column"):
                            metric_col = detection["metric_column"]
                        if detection.get("date_column"):
                            date_col = detection["date_column"]
                        if detection.get("periods"):
                            periods = detection["periods"]
                        if detection.get("frequency"):
                            freq = detection["frequency"]

                plan.append({
                    "tool": "forecast_metric",
                    "arguments": {
                        "dataset_id": resolved_ds_id or "",
                        "metric_column": metric_col,
                        "date_column": date_col,
                        "periods": periods,
                        "frequency": freq
                    }
                })
            else:
                ad_args: Dict[str, Any] = {"question": question, "dataset_id": resolved_ds_id}
                if resolved_ds_id:
                    ctx = self.get_dataset_context(resolved_ds_id)
                    profile = ctx.get("profile", {})
                    if profile:
                        detection = detect_data_operation_and_columns(question, profile)
                        if not detection.get("ambiguous"):
                            if detection.get("operation") in ["top", "trend"]:
                                ad_args["operation"] = detection["operation"]
                            if detection.get("dimension_column"):
                                ad_args["dimension_column"] = detection["dimension_column"]
                            if detection.get("metric_column"):
                                ad_args["metric_column"] = detection["metric_column"]
                            if detection.get("date_column"):
                                ad_args["date_column"] = detection["date_column"]
                            if detection.get("limit"):
                                ad_args["limit"] = detection["limit"]
                            if detection.get("frequency"):
                                ad_args["frequency"] = detection["frequency"]

                plan.append({
                    "tool": "analyze_dataset",
                    "arguments": ad_args
                })

        elif intent == "DOCS":
            plan.append({
                "tool": "search_documents",
                "arguments": {
                    "query": question,
                    "document_id": document_id,
                    "top_k": 5
                }
            })

        elif intent == "HYBRID":
            ad_args: Dict[str, Any] = {"question": question, "dataset_id": resolved_ds_id}
            if resolved_ds_id:
                ctx = self.get_dataset_context(resolved_ds_id)
                profile = ctx.get("profile", {})
                if profile:
                    detection = detect_data_operation_and_columns(question, profile)
                    if not detection.get("ambiguous"):
                        if detection.get("operation") in ["top", "trend"]:
                            ad_args["operation"] = detection["operation"]
                        if detection.get("dimension_column"):
                            ad_args["dimension_column"] = detection["dimension_column"]
                        if detection.get("metric_column"):
                            ad_args["metric_column"] = detection["metric_column"]
                        if detection.get("date_column"):
                            ad_args["date_column"] = detection["date_column"]
                        if detection.get("limit"):
                            ad_args["limit"] = detection["limit"]
                        if detection.get("frequency"):
                            ad_args["frequency"] = detection["frequency"]

            plan.append({
                "tool": "analyze_dataset",
                "arguments": ad_args
            })
            search_args: Dict[str, Any] = {
                "query": question,
                "top_k": 5
            }
            if document_id:
                search_args["document_id"] = document_id
            plan.append({
                "tool": "search_documents",
                "arguments": search_args
            })

        return plan

    # =========================================================================
    # 4. Tool Execution & Grounded Synthesis
    # =========================================================================

    def process_question(
        self,
        question: str,
        dataset_id: Optional[str] = None,
        document_id: Optional[str] = None,
        api_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Executes safe tool orchestration and returns structured response.
        """
        routing = self.classify_intent(
            question=question,
            dataset_id=dataset_id,
            document_id=document_id,
            api_key=api_key
        )
        intent = routing["intent"]

        # ---------------------------------------------------------------------
        # GENERAL Intent
        # ---------------------------------------------------------------------
        if intent == "GENERAL":
            answer = (
                "👋 **Hello! I am the InsightOS Intelligence Brain.**\n\n"
                "I can help you analyze and cross-reference your business assets:\n"
                "- 📊 **Data Brain**: Deterministic calculations, KPIs, trends, and quality analysis on CSV/Excel spreadsheets.\n"
                "- 📄 **Knowledge Brain**: Grounded semantic search and question-answering across corporate PDF policies and SOPs.\n"
                "- ⚡ **Hybrid Reasoning**: Synthesize data findings with document guidelines without fabricating facts.\n\n"
                "How can I assist you with your data or documents today?"
            )
            return {
                "intent": "GENERAL",
                "tool_calls": [],
                "answer": answer,
                "data_facts": [],
                "document_evidence": [],
                "citations": [],
                "sources": [],
                "sources_text": "",
                "confidence": routing["confidence"],
                "warnings": []
            }

        # ---------------------------------------------------------------------
        # Tool Planning & Execution
        # ---------------------------------------------------------------------
        tool_plan = self.plan_tools(
            intent=intent,
            question=question,
            dataset_id=dataset_id,
            document_id=document_id
        )

        tool_calls: List[Dict[str, Any]] = []
        tool_results: Dict[str, Any] = {}
        warnings: List[str] = []

        for item in tool_plan:
            tool_name = item["tool"]
            args = item["arguments"]

            # Safety check: enforce TOOL_REGISTRY membership
            if tool_name not in TOOL_REGISTRY:
                warnings.append(f"Tool '{tool_name}' rejected: not in approved TOOL_REGISTRY.")
                tool_calls.append({"tool": tool_name, "status": "failed"})
                continue

            if tool_name == "analyze_dataset":
                result = self.analyze_dataset(**args)
            elif tool_name == "get_kpis":
                result = self.get_kpis(dataset_id=args.get("dataset_id"))
            elif tool_name == "get_data_quality":
                result = self.get_data_quality(dataset_id=args.get("dataset_id"))
            elif tool_name == "detect_anomalies":
                result = self.detect_anomalies(**args)
            elif tool_name == "search_documents":
                search_ret = self.search_documents(
                    query=args.get("query", question),
                    document_id=args.get("document_id"),
                    top_k=args.get("top_k", 5)
                )
                if isinstance(search_ret, dict):
                    result = search_ret
                else:
                    cites = []
                    for c in search_ret:
                        fname = c.get("filename", "Document.pdf")
                        page = c.get("page", 1)
                        cite = f"{fname} (Page {page})"
                        if cite not in cites:
                            cites.append(cite)
                    result = {
                        "success": True,
                        "query": args.get("query", question),
                        "count": len(search_ret),
                        "chunks": search_ret,
                        "citations": cites
                    }
            else:
                result = execute_tool(tool_name, args)

            status = "success" if result.get("success", False) else "failed"
            tool_calls.append({"tool": tool_name, "status": status})
            tool_results[tool_name] = result

            if not result.get("success", False) and result.get("error"):
                warnings.append(result["error"])

        # ---------------------------------------------------------------------
        # DATA Intent Synthesis
        # ---------------------------------------------------------------------
        if intent == "DATA":
            data_res = (
                tool_results.get("analyze_dataset")
                or tool_results.get("get_kpis")
                or tool_results.get("get_data_quality")
                or tool_results.get("detect_anomalies")
                or tool_results.get("forecast_metric")
            )
            if not data_res or not data_res.get("success", False):
                err_msg = data_res.get("error", "No active structured dataset found.") if data_res else "No active structured dataset found."
                answer = f"📊 **InsightOS Data Brain:**\n\nNo active structured dataset is available ({err_msg}). Please upload a CSV or Excel dataset to perform deterministic analytics."
                return {
                    "intent": "DATA",
                    "tool_calls": tool_calls,
                    "answer": answer,
                    "data_facts": [],
                    "document_evidence": [],
                    "citations": [],
                    "sources": [],
                    "sources_text": "",
                    "confidence": routing["confidence"],
                    "warnings": warnings or [err_msg]
                }

            facts = data_res.get("facts", [])
            answer_text = data_res.get("text", "")
            return {
                "intent": "DATA",
                "tool_calls": tool_calls,
                "answer": answer_text,
                "data_facts": facts,
                "document_evidence": [],
                "citations": [],
                "sources": [],
                "sources_text": "",
                "confidence": routing["confidence"],
                "warnings": warnings,
                "summary": facts[0] if facts else ""
            }

        # ---------------------------------------------------------------------
        # DOCS Intent Synthesis (Single Retrieval)
        # ---------------------------------------------------------------------
        if intent == "DOCS":
            docs_res = tool_results.get("search_documents", {})
            chunks = docs_res.get("chunks", [])
            citations = docs_res.get("citations", [])

            if not chunks:
                answer = "📄 **Document Insights:**\n\nI could not find any relevant information in the indexed documents regarding your question."
                return {
                    "intent": "DOCS",
                    "tool_calls": tool_calls,
                    "answer": answer,
                    "data_facts": [],
                    "document_evidence": [],
                    "citations": [],
                    "sources": [],
                    "sources_text": "",
                    "confidence": routing["confidence"],
                    "warnings": ["No matching document passages found."]
                }

            context_blocks = []
            for idx, c in enumerate(chunks, start=1):
                cite_tag = f"{c['filename']} (Page {c['page']})"
                context_blocks.append(f"[Passage {idx} | {cite_tag}]:\n{c['text']}")

            sources_text = "\n".join([f"- {c}" for c in citations])
            context_text = "\n\n".join(context_blocks)

            active_key = get_groq_api_key(api_key)
            grounded_body = ""
            if active_key:
                try:
                    llm = ChatGroq(temperature=0, model=MODEL, api_key=active_key)
                    prompt = ChatPromptTemplate.from_messages([
                        ("system", """You are the Knowledge Assistant for InsightOS.
Answer the user's question using ONLY the provided document passages.
STRICT RULES:
1. Every claim must be directly backed by the provided passages.
2. If the passages do not contain sufficient evidence, state that explicitly.
3. NEVER invent citations, page numbers, or external facts.
4. Keep the answer professional, concise, and factual."""),
                        ("human", """Document Passages:
{context}

Question:
{question}""")
                    ])
                    res = (prompt | llm).invoke({
                        "context": context_text,
                        "question": question
                    })
                    grounded_body = res.content.strip()
                except Exception:
                    grounded_body = f"Retrieved relevant policy context:\n\n{chunks[0]['text']}"
            else:
                grounded_body = f"Retrieved relevant policy context:\n\n{chunks[0]['text']}"

            full_answer = f"📄 **Document Insights:**\n\n{grounded_body}\n\n**Sources:**\n{sources_text}"

            return {
                "intent": "DOCS",
                "tool_calls": tool_calls,
                "answer": full_answer,
                "data_facts": [],
                "document_evidence": chunks,
                "citations": citations,
                "sources": citations,
                "sources_text": sources_text,
                "confidence": routing["confidence"],
                "warnings": warnings
            }

        # ---------------------------------------------------------------------
        # HYBRID Intent Synthesis (Multi-Tool Execution)
        # ---------------------------------------------------------------------
        if intent == "HYBRID":
            data_res = tool_results.get("analyze_dataset", {})
            docs_res = tool_results.get("search_documents", {})
            return self.synthesize_hybrid(
                question=question,
                data_result=data_res,
                docs_result=docs_res,
                tool_calls=tool_calls,
                confidence=routing["confidence"],
                warnings=warnings,
                api_key=api_key
            )

    # =========================================================================
    # 5. Dedicated HYBRID Grounded Synthesis
    # =========================================================================

    def synthesize_hybrid(
        self,
        question: str,
        data_result: Dict[str, Any],
        docs_result: Dict[str, Any],
        tool_calls: Optional[List[Dict[str, Any]]] = None,
        confidence: float = 0.92,
        warnings: Optional[List[str]] = None,
        api_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Synthesizes deterministic structured data findings and grounded document evidence.
        Strict Safety Contract:
        1. Numerical facts are strictly authoritative from Data Brain. Never invent, estimate, or alter numbers.
        2. Document claims are strictly derived from retrieved Knowledge Brain chunks.
        3. Citations and page numbers are generated ONLY from real chunk metadata.
        4. Never assert causation unless supported by explicit evidence.
        5. If data or document evidence is missing, explicitly state so.
        6. Four clearly separated sections in answer:
           - 📊 DATA FINDINGS
           - 📄 DOCUMENT EVIDENCE
           - ⚡ AI INTERPRETATION
           - 🔗 CITATIONS
        """
        combined_warnings = list(warnings or [])

        # 1. Data Findings Extraction
        has_data = data_result.get("success", False)
        data_facts = list(data_result.get("facts", [])) if has_data else []
        raw_data_text = data_result.get("text", "") if has_data else ""

        if has_data and raw_data_text:
            cleaned_data_text = re.sub(r"^📊\s*\**DATA FINDINGS\**\s*", "", raw_data_text.strip(), flags=re.IGNORECASE).strip()
            data_section_body = cleaned_data_text if cleaned_data_text else "\n".join(f"• {f}" for f in data_facts)
        else:
            err_detail = data_result.get("error", "No active structured dataset found.")
            data_section_body = f"No active structured dataset is available ({err_detail})."
            if "No active structured dataset" not in " ".join(combined_warnings):
                combined_warnings.append("No active structured dataset available.")

        # 2. Document Evidence Extraction
        has_docs = docs_result.get("success", False)
        chunks = list(docs_result.get("chunks", [])) if has_docs else []

        # Build strict citations from chunk metadata
        citations = []
        for c in chunks:
            fname = c.get("filename", "Document.pdf")
            page = c.get("page", 1)
            cite = f"{fname} (Page {page})"
            if cite not in citations:
                citations.append(cite)

        if not citations and docs_result.get("citations"):
            citations = list(docs_result["citations"])

        sources_text = "\n".join([f"- {c}" for c in citations])

        if chunks:
            doc_passages_list = []
            for c in chunks:
                doc_passages_list.append(f"• [{c.get('filename', 'Document.pdf')} (Page {c.get('page', 1)})]:\n  {c.get('text', '').strip()}")
            docs_section_body = "\n\n".join(doc_passages_list)
        else:
            docs_section_body = "No matching document evidence found."
            if "No matching document passages found." not in " ".join(combined_warnings):
                combined_warnings.append("No matching document passages found.")

        # Context text for LLM
        context_blocks = [f"[{c.get('filename', 'Document.pdf')} (Page {c.get('page', 1)})]: {c.get('text', '')}" for c in chunks]
        context_text = "\n\n".join(context_blocks) if context_blocks else "No relevant document passages found."

        # 3. Grounded AI Interpretation
        active_key = get_groq_api_key(api_key)
        interpretation = ""

        if active_key and (data_facts or chunks):
            try:
                llm = ChatGroq(temperature=0, model=MODEL, api_key=active_key)
                synthesis_prompt = ChatPromptTemplate.from_messages([
                    ("system", """You are the Executive Reasoning Brain for InsightOS.
Synthesize findings between the Structured Dataset facts and the Document Evidence.
STRICT SAFETY CONTRACT:
1. Numbers from the Structured Dataset are authoritative. Never invent, estimate, calculate, or alter any numbers.
2. Document claims must be derived STRICTLY from the provided Document Passages.
3. NEVER invent a citation, page number, or document name.
4. Do NOT claim causation unless explicitly supported by evidence. Never confuse correlation with causation.
5. If evidence is insufficient to connect the data to the document policies, explicitly state that evidence is insufficient.
6. Provide an objective, analytical interpretation connecting the two sources."""),
                    ("human", """Structured Data Facts:
{data_facts}

Document Evidence Passages:
{doc_passages}

User Question:
{question}""")
                ])
                res = (synthesis_prompt | llm).invoke({
                    "data_facts": "\n".join(f"- {f}" for f in data_facts) if data_facts else "None",
                    "doc_passages": context_text,
                    "question": question
                })
                interpretation = res.content.strip()
            except Exception:
                interpretation = ""

        if not interpretation:
            # Deterministic, safe, grounded fallback (ensuring offline and test safety)
            if data_facts and chunks:
                facts_preview = "; ".join(data_facts[:3])
                doc_ref = f"{chunks[0].get('filename', 'Document.pdf')} (Page {chunks[0].get('page', 1)})"
                interpretation = (
                    f"Based on the structured dataset, {facts_preview}. "
                    f"According to {doc_ref}, the policy/guidelines outline specific operational requirements. "
                    f"No causal link is asserted between the quantitative metrics and document policies without explicit supporting evidence."
                )
            elif data_facts and not chunks:
                facts_preview = "; ".join(data_facts[:3])
                interpretation = (
                    f"Structured data findings ({facts_preview}) were successfully calculated from the dataset, "
                    f"but no matching document evidence was found to provide policy or procedural context."
                )
            elif not data_facts and chunks:
                doc_ref = f"{chunks[0].get('filename', 'Document.pdf')} (Page {chunks[0].get('page', 1)})"
                interpretation = (
                    f"Document evidence was retrieved from {doc_ref}, but no active structured dataset "
                    f"was available to cross-reference quantitative findings."
                )
            else:
                interpretation = (
                    "Neither structured dataset metrics nor document evidence were available to perform hybrid synthesis."
                )

        # 4. Assembling Required Answer Structure
        citations_body = f"**Sources:**\n{sources_text}" if citations else "No document citations available."

        combined_answer = (
            f"⚡ **InsightOS Hybrid Synthesis:**\n\n"
            f"### 📊 DATA FINDINGS\n{data_section_body}\n\n"
            f"### 📄 DOCUMENT EVIDENCE\n{docs_section_body}\n\n"
            f"### ⚡ AI INTERPRETATION\n{interpretation}\n\n"
            f"### 🔗 CITATIONS\n{citations_body}"
        )

        return {
            "intent": "HYBRID",
            "tool_calls": tool_calls or [],
            "answer": combined_answer,
            "data_facts": data_facts,
            "document_evidence": chunks,
            "citations": citations,
            "confidence": confidence,
            "warnings": combined_warnings,
            "sources": citations,
            "sources_text": sources_text,
            "summary": data_result.get("summary", {}) if has_data else {}
        }
