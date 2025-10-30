import streamlit as st
import os
from oracle_db import init_db, query_failed_workflows, query_workflow_by_item, retry_failed_workflow, log_audit, fetch_audit
from servicenow_client import create_incident, search_incidents
from openai_client import interpret_intent, generate_answer
from utils import render_workflow_card

from rag_engine import build_vector_db_with_sources, get_qa_chain

st.set_page_config(page_title="Workflow AI - RAG Dynamic", layout="wide")
st.title("Workflow AI — RAG (Docs + Oracle Audit + ServiceNow)")

init_db()

with st.sidebar:
    st.header("Controls")
    api_provider = st.selectbox("Assistant mode", ["Mock (default)", "Azure/OpenAI (requires key)"])
    openai_key = st.text_input("AZURE_OPENAI_KEY / OPENAI_API_KEY (optional)", type="password")
    st.markdown("**RAG / Knowledge Base**")
    if st.button("Build combined RAG DB (Docs + Audit + ServiceNow)"):
        try:
            doc_path = os.path.join(os.getcwd(), "Workflow_AI.docx")
            build_vector_db_with_sources(doc_path=doc_path, include_audit=True, include_servicenow=True)
            st.success("✅ Combined RAG DB built and persisted to 'rag_db' (or RAG_PERSIST_DIR).")
        except Exception as e:
            st.error(f"Failed to build combined RAG DB: {e}")
    if st.button("Build doc-only RAG DB"):
        try:
            doc_path = os.path.join(os.getcwd(), "Workflow_AI.docx")
            build_vector_db_with_sources(doc_path=doc_path, include_audit=False, include_servicenow=False)
            st.success("✅ Doc-only RAG DB built.")
        except Exception as e:
            st.error(f"Failed to build doc-only RAG DB: {e}")
    st.markdown("---")
    st.markdown("**Actions**")
    if st.button("Show failed workflows (last 24h)"):
        st.session_state["last_action"] = "failed_workflows"
    if st.button("View Audit Log"):
        st.session_state["view_audit"] = True
    if st.button("Clear logs"):
        st.session_state.clear()

st.subheader("Ask a question")
user_input = st.text_input("Type a natural language query (e.g., 'search docs: recent actions for PO12345')")

col1, col2 = st.columns([2,1])

with col1:
    if st.button("Send") or (user_input and st.session_state.get("last_action")!="failed_workflows"):
        intent, params = interpret_intent(user_input, mode="mock")
        st.markdown(f"**Interpreted intent:** `{intent}`  \n**Params:** `{params}`")

        if user_input and user_input.lower().startswith("search docs:"):
            query = user_input.split(":",1)[1].strip() if ":" in user_input else user_input
            st.info("Running RAG query against combined knowledge base...")
            try:
                qa = get_qa_chain()
                answer = qa.run(query)
                st.success("Answer (RAG):")
                st.write(answer)
                log_audit("RAGQuery", None, None, f"Query: {query}")
            except Exception as e:
                st.error(f"RAG query failed: {e}")
                st.error("Make sure you have built the combined RAG DB first.")

        elif intent == "get_failed_workflows":
            rows = query_failed_workflows()
            log_audit("QueryFailedWorkflows", None, None, f"Returned {len(rows)} rows")
            if not rows:
                st.success("✅ No failed workflows in the last 24 hours.")
            else:
                st.warning(f"⚠️ {len(rows)} failed workflows found.")
                for r in rows:
                    st.markdown(render_workflow_card(r), unsafe_allow_html=True)

        elif intent == "create_incident":
            item = params.get("item") or "PO12345"
            row = query_workflow_by_item(item) or {"ITEM_KEY": item, "ERROR_MESSAGE": "Sample error", "ITEM_TYPE": "PO"}
            try:
                resp = create_incident(row, idempotency_key=item)
                status = resp.get("status")
                inc_no = resp.get("incident", {}).get("number") if resp.get("incident") else None
                if status == "created":
                    st.success(f"🧾 Incident created: {inc_no}")
                elif status == "exists":
                    st.info(f"Incident already exists: {resp['incident'].get('number')}")
                log_audit("CreateIncident", row.get("ITEM_TYPE"), row.get("ITEM_KEY"), status, inc_no)
            except Exception as e:
                st.error(f"Failed to create incident: {e}")
                log_audit("CreateIncident", row.get("ITEM_TYPE"), row.get("ITEM_KEY"), f"ERROR: {e}", None)

        elif intent == "retry_failed_workflows":
            rows = query_failed_workflows()
            if not rows:
                st.info("✅ No failed workflows to retry.")
            else:
                st.warning(f"Retrying {len(rows)} failed workflows...")
                for r in rows:
                    resp = retry_failed_workflow(r['ITEM_TYPE'], r['ITEM_KEY'], user="streamlit_user")
                    st.markdown(f"- {r['ITEM_KEY']}: {resp['message']}")
                log_audit("RetryBatch", None, None, f"Retried {len(rows)} workflows")

        elif intent == "retry_workflow":
            item = params.get("item")
            if not item:
                st.error("No item key provided.")
            else:
                row = query_workflow_by_item(item)
                if not row:
                    st.warning(f"No workflow found for {item}.")
                else:
                    resp = retry_failed_workflow(row['ITEM_TYPE'], row['ITEM_KEY'], user="streamlit_user")
                    if resp['status']=="success':
                        st.success(resp['message'])
                    else:
                        st.error(resp['message'])
                    log_audit("RetryWorkflow", row.get("ITEM_TYPE"), row.get("ITEM_KEY"), resp.get("message"))

        else:
            answer = generate_answer(user_input, mode="mock")
            st.info("Assistant response")
            st.write(answer)

with col2:
    st.subheader("Sample quick queries")
    if st.button("Show failed workflows (quick)"):
        rows = query_failed_workflows()
        log_audit("QueryFailedWorkflows", None, None, f"Returned {len(rows)} rows")
        if not rows:
            st.success("✅ No failed workflows in the last 24 hours.")
        else:
            st.warning(f"⚠️ {len(rows)} failed workflows found.")
            for r in rows:
                st.markdown(render_workflow_card(r), unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("Audit Log (recent)")
    if st.session_state.get("view_audit"):
        import pandas as pd
        df = pd.DataFrame(fetch_audit(200))
        st.dataframe(df)

st.markdown("---")
st.markdown("### Change log / debug")
st.write(st.session_state)
