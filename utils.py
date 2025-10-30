def render_workflow_card(row):
    # simple HTML card
    html = f"""
    <div style="border:1px solid #ddd;padding:10px;border-radius:6px;margin-bottom:8px">
      <strong>{row.get('ITEM_TYPE')} - {row.get('ITEM_KEY')}</strong><br/>
      <em>{row.get('ACTIVITY_NAME')} · {row.get('END_DATE')}</em><br/>
      <p style="color:darkred"><strong>Status:</strong> {row.get('ACTIVITY_STATUS')}</p>
      <p><strong>Error:</strong> {row.get('ERROR_MESSAGE')}</p>
    </div>
    """
    return html
