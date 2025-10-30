# servicenow_client.py
# -------------------------------------------------------------------
# Minimal mock ServiceNow client so Streamlit app can import and run.
# -------------------------------------------------------------------

import random

def create_incident(row, idempotency_key=None):
    """Pretend to create a ServiceNow incident."""
    inc_num = f"INC{random.randint(100000,999999)}"
    return {
        "status": "created",
        "incident": {"number": inc_num,
                     "short_description": row.get("ERROR_MESSAGE","Mock incident")}
    }

def search_incidents(query=None, limit=50):
    """Return a few fake incidents."""
    incidents = []
    for i in range(limit):
        incidents.append({
            "number": f"INC{1000+i}",
            "short_description": f"Workflow issue {i}",
            "description": f"Workflow failed for PO{1000+i}",
            "state": "Closed" if i % 2 == 0 else "Open",
            "sys_updated_on": "2025-10-30 10:00:00"
        })
    return {"result": incidents}
