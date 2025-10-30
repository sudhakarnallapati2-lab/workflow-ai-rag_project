# rag_engine.py
"""
RAG engine using LangChain + Chroma + Hugging Face sentence-transformers embeddings.
This version supports combining:
 - Workflow_AI.docx (static docs)
 - Oracle audit logs (via oracle_db.fetch_audit)
 - ServiceNow incidents (via servicenow_client.search_incidents)

Usage:
    from rag_engine import build_vector_db_with_sources, get_qa_chain
    build_vector_db_with_sources(doc_path="Workflow_AI.docx")
    qa = get_qa_chain()
    answer = qa.run("How do I retry a workflow?")
"""
import os
import logging
from typing import List, Optional

from langchain.document_loaders import UnstructuredWordDocumentLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.vectorstores import Chroma
from langchain.chains import RetrievalQA
from langchain.llms import OpenAI
from langchain.schema import Document

# optional imports for dynamic sources
try:
    from oracle_db import fetch_audit
except Exception:
    fetch_audit = None

try:
    from servicenow_client import search_incidents
except Exception:
    search_incidents = None

logger = logging.getLogger("rag_engine")
logger.setLevel(logging.INFO)
if not logger.handlers:
    import sys
    h = logging.StreamHandler(sys.stdout)
    h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(h)

PERSIST_DIR = os.getenv("RAG_PERSIST_DIR", "rag_db")
EMBEDDING_MODEL = os.getenv("RAG_HF_MODEL", "sentence-transformers/all-MiniLM-L6-v2")

def _load_workflow_doc(doc_path: str) -> List[Document]:
    if not os.path.isfile(doc_path):
        logger.warning("Workflow document not found at %s", doc_path)
        return []
    loader = UnstructuredWordDocumentLoader(doc_path)
    docs = loader.load()
    logger.info("Loaded %d documents from %s", len(docs), doc_path)
    return docs

def _load_audit_docs(limit: int = 200) -> List[Document]:
    docs = []
    if fetch_audit is None:
        logger.warning("oracle_db.fetch_audit not available; skipping audit logs")
        return docs
    try:
        audits = fetch_audit(limit=limit)
        for a in audits:
            text = f"[Audit] {a.get('log_timestamp')} | user:{a.get('user_name')} | action:{a.get('action_type')} | item:{a.get('item_key')} | result:{a.get('result_message')} | incident:{a.get('incident_number')}"
            docs.append(Document(page_content=text, metadata={"source": "oracle_audit", "item_key": a.get("item_key")}))
        logger.info("Loaded %d audit documents", len(docs))
    except Exception as e:
        logger.exception("Failed to fetch audit logs: %s", e)
    return docs

def _load_servicenow_docs(limit: int = 100) -> List[Document]:
    docs = []
    if search_incidents is None:
        logger.warning("servicenow_client.search_incidents not available; skipping ServiceNow")
        return docs
    try:
        res = search_incidents("ORDERBYDESCsys_created_on", limit=limit)
        results = res.get("result", []) if isinstance(res, dict) else []
        for inc in results:
            num = inc.get("number", "N/A")
            short = inc.get("short_description", "")
            desc = inc.get("description", "")
            state = inc.get("state")
            updated = inc.get("sys_updated_on")
            text = f"[ServiceNow] {num} | {short} | {desc} | state:{state} | updated:{updated}"
            docs.append(Document(page_content=text, metadata={"source":"servicenow", "incident_number":num}))
        logger.info("Loaded %d ServiceNow documents", len(docs))
    except Exception as e:
        logger.exception("Failed to fetch ServiceNow incidents: %s", e)
    return docs

def build_vector_db_with_sources(doc_path: str = "Workflow_AI.docx",
                                 include_audit: bool = True,
                                 include_servicenow: bool = True,
                                 persist_directory: str = PERSIST_DIR,
                                 chunk_size: int = 800,
                                 chunk_overlap: int = 100,
                                 audit_limit: int = 200,
                                 servicenow_limit: int = 100):
    """
    Build a combined vector DB from the workflow doc, Oracle audit logs, and ServiceNow incidents.
    """
    all_docs: List[Document] = []

    # static doc
    all_docs.extend(_load_workflow_doc(doc_path))

    # dynamic sources
    if include_audit:
        all_docs.extend(_load_audit_docs(limit=audit_limit))
    if include_servicenow:
        all_docs.extend(_load_servicenow_docs(limit=servicenow_limit))

    if not all_docs:
        raise ValueError("No documents found to index. Provide Workflow_AI.docx or enable sources.")

    splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    chunks = splitter.split_documents(all_docs)

    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
    vectordb = Chroma.from_documents(chunks, embedding=embeddings, persist_directory=persist_directory)
    vectordb.persist()
    logger.info("Built combined vector DB with %d chunks at %s", len(chunks), persist_directory)
    return vectordb

def build_vector_db(doc_path: str = "Workflow_AI.docx", persist_directory: str = PERSIST_DIR, chunk_size: int = 800, chunk_overlap: int = 100):
    """Backwards-compatible: index only the static doc."""
    return build_vector_db_with_sources(doc_path=doc_path, include_audit=False, include_servicenow=False,
                                       persist_directory=persist_directory, chunk_size=chunk_size, chunk_overlap=chunk_overlap)

def load_vector_db(persist_directory: str = PERSIST_DIR):
    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
    vectordb = Chroma(persist_directory=persist_directory, embedding_function=embeddings)
    return vectordb

def get_qa_chain(persist_directory: str = PERSIST_DIR, k: int = 3, llm_model: Optional[str] = None):
    vectordb = load_vector_db(persist_directory=persist_directory)
    retriever = vectordb.as_retriever(search_kwargs={"k": k})
    # default to OpenAI LLM if configured; user may replace with local LLM
    if llm_model:
        llm = OpenAI(model_name=llm_model, temperature=0)
    else:
        llm = OpenAI(temperature=0)
    qa = RetrievalQA.from_chain_type(llm=llm, chain_type="stuff", retriever=retriever)
    return qa
