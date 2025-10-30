# Workflow AI - RAG Dynamic (Docs + Oracle Audit + ServiceNow)

This version extends the RAG engine to index:
- Workflow_AI.docx (static documentation)
- Oracle audit logs (wf_ai_audit_log)
- ServiceNow incidents (via API)

## How to use
1. Ensure `Workflow_AI.docx` is in the project folder.
2. Create and activate a virtualenv.
3. Install: `pip install -r requirements.txt`
4. Run: `streamlit run app.py`
5. In the sidebar, click **Build combined RAG DB (Docs + Audit + ServiceNow)**.
6. After build completes, query with: `search docs: recent actions for PO12345`

## Notes
- Building embeddings downloads Hugging Face models; requires internet.
- ServiceNow/API access requires env vars configured (see servicenow_client.py usage).
- For production, prefer scheduled re-indexing (nightly) and larger vector stores (Pinecone/Milvus).
