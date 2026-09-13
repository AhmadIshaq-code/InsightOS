import os
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from config import MODEL, get_groq_api_key
from knowledge_service import search_documents

def query_rag_documents(query: str, k: int = 3, api_key: str = None, document_id: str = None):
    """
    Retrieves context from the Knowledge Brain and generates a grounded answer using Groq.
    Guarantees page-aware source citations and strict document grounding.
    """
    active_api_key = get_groq_api_key(api_key)
    if not active_api_key:
        return {
            "answer": "Error: GROQ_API_KEY is not configured. Please set it in Settings or your .env file.",
            "sources": [],
            "sources_text": ""
        }

    # 1. RETRIEVAL: Source-aware semantic search via Knowledge Brain
    try:
        search_results = search_documents(query, top_k=k, document_id=document_id)
    except Exception as e:
        return {"answer": f"Error retrieving document knowledge: {str(e)}", "sources": [], "sources_text": ""}

    if not search_results:
        return {
            "answer": "I cannot find the answer in the provided documents. The document evidence is insufficient for this query.",
            "sources": [],
            "sources_text": ""
        }

    # 2. Extract grounded context and citation references
    context_chunks = []
    sources = []
    seen_sources = set()

    for r in search_results:
        doc_label = f"{r['filename']} (Page {r['page']})"
        context_chunks.append(f"[Source: {doc_label}]\n{r['text']}")
        if doc_label not in seen_sources:
            seen_sources.add(doc_label)
            sources.append(doc_label)

    combined_context = "\n\n---\n\n".join(context_chunks)
    sources_text = "\n".join([f"- {s}" for s in sources])

    # 3. AUGMENTATION & GENERATION: Grounded Groq LLM chain
    llm = ChatGroq(
        temperature=0, 
        model=MODEL,
        api_key=active_api_key
    )

    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are an expert AI business intelligence and corporate document assistant for InsightOS.
Answer the user's question using ONLY the provided document context.
If the context does not contain the answer or is insufficient, explicitly state:
'I cannot find the answer in the provided documents.'
Do NOT fabricate, assume, or invent document facts.
Whenever stating facts, reference the specific document and page cited in the context."""),
        ("human", "Context:\n{context}\n\nQuestion: {question}")
    ])

    chain = prompt | llm

    try:
        response = chain.invoke({
            "context": combined_context,
            "question": query
        })
        return {
            "answer": response.content,
            "sources": sources,
            "sources_text": sources_text,
            "retrieved_chunks": search_results
        }
    except Exception as e:
        return {
            "answer": f"Error generating answer: {str(e)}",
            "sources": sources,
            "sources_text": sources_text
        }

if __name__ == "__main__":
    # Test Question (Make sure you have ingested some PDFs related to this first!)
    test_query = "What is the protocol for a production incident?"
    
    result = query_rag_documents(test_query)
    
    print("\n" + "="*50)
    print("--- FINAL ANSWER ---")
    print(result["answer"])
    print("\n--- SOURCES CITED ---")
    for source in result["sources"]:
        # Print just the filename, not the huge absolute path
        print(f"- {os.path.basename(source)}")
    print("="*50)
