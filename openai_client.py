import os
import json

def interpret_intent(user_input, mode="mock", azure_key=None, azure_endpoint=None):
    """
    Very small intent extractor. If mode=='openai' and credentials provided,
    this function would call Azure/OpenAI. Here we provide a simple rule-based fallback.
    """
    text = (user_input or "").lower()
    if "failed workflow" in text or "failed workflows" in text or "failed" in text:
        return ("get_failed_workflows", {})
    if "why is" in text or "stuck" in text or "why" in text:
        # try to extract an item key pattern (PO followed by digits)
        import re
        m = re.search(r"(po|req|req)\s*#?\s*([0-9]+)", text)
        if m:
            return ("get_workflow_by_item", {"item": m.group(0).replace(" ", "")})
        # else fallback
        return ("get_workflow_by_item", {"item": ""})
    if "create incident" in text or "create ticket" in text or "servicenow" in text:
        return ("create_incident", {})
    # fallback: general question -> either call LLM or return generic intent
    return ("chat", {"query": user_input})

def generate_answer(user_input, mode="mock", azure_key=None, azure_endpoint=None):
    """
    If mode=='openai' and credentials present, you can wire this to Azure OpenAI / OpenAI.
    In this local test, we return a canned reply or a simple formatted echo.
    """
    if mode == "openai" and azure_key:
        # Placeholder: real Azure OpenAI call would go here.
        # Because internet is unavailable in this environment, return a message telling user to wire up keys.
        return "OpenAI mode selected but this environment cannot reach external APIs. Provide keys and run in your environment."
    # Mocked response:
    return f"I understand: `{user_input}`. (This is a local test-mode response. To enable real LLM responses, configure Azure OpenAI keys in the sidebar.)"
