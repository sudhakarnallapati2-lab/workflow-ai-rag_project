# servicenow_client.py
# Mock ServiceNow integration for local testing

import random

def create_incident(row, idempotency_key=None):
    """Pretend to create an incident and return a fake number."""
    inc_num = f"INC{random.randint(100000, 999999)}"
    return {
        "status": "created",
        "incident": {
            "number": inc_num,
            "short_description": row.get("ERROR_MESSAGE", "N/A"),
        },
    }

def search_incidents(query=None, limit=50):
    """Return a list of fake incidents for demo purposes."""
    data = []
    for i in range(limit):
        data.append({
            "number": f"INC{1000+i}",
            "short_description": f"Workflow issue {i}",
            "description": f"Workflow failed for PO{1000+i}",
            "state": "Closed" if i % 2 == 0 else "Open",
            "sys_updated_on": "2025-10-30 10:00:00"
        })
    return {"result": data}
