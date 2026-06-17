import datetime

def build_doc_blocks(themes: list[dict], iso_week: str, window_weeks: int) -> list[dict]:
    """
    Translates Groq-summarized themes into structured document blocks 
    suitable for the Google Docs MCP append_section tool.
    """
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M Local Time")
    
    blocks = []
    
    # Header Paragraph
    blocks.append({
        "type": "paragraph",
        "text": f"Period: Last {window_weeks} weeks (rolling) · Source: Google Play Store · Generated: {now_str}"
    })
    
    # 1. Top themes
    blocks.append({"type": "heading_3", "text": "Top Themes"})
    for theme in themes:
        theme_name = theme.get("theme_name", "Unknown Theme")
        summary = theme.get("summary", "")
        size = theme.get("cluster_size", 0)
        score = theme.get("ranking_score", 0.0)
        blocks.append({
            "type": "bullet",
            "text": f"{theme_name} (Reviews: {size}, Score: {score}) — {summary}"
        })
        
    # 2. Real user quotes
    blocks.append({"type": "heading_3", "text": "Real User Quotes"})
    has_quotes = False
    for theme in themes:
        theme_name = theme.get("theme_name", "")
        for quote in theme.get("quotes", []):
            blocks.append({
                "type": "quote",
                "text": f"\"{quote}\" (Theme: {theme_name})"
            })
            has_quotes = True
    if not has_quotes:
        blocks.append({
            "type": "paragraph",
            "text": "No verbatim user quotes passed verification checks."
        })
        
    # 3. Action ideas
    blocks.append({"type": "heading_3", "text": "Action Ideas"})
    for theme in themes:
        theme_name = theme.get("theme_name", "")
        for action in theme.get("action_ideas", []):
            title = action.get("title", "")
            detail = action.get("detail", "")
            blocks.append({
                "type": "bullet",
                "text": f"{title} — {detail} (Theme: {theme_name})"
            })
            
    # 4. Who this helps
    blocks.append({"type": "heading_3", "text": "Who This Helps"})
    blocks.append({"type": "bullet", "text": "Product Management: For identifying trading indicator and feature requests."})
    blocks.append({"type": "bullet", "text": "Customer Support: For tracking brokerage and login complaint volumes."})
    blocks.append({"type": "bullet", "text": "Engineering: For addressing app stability, crashes, and search bugs."})
    
    return blocks
