class PluginHooks:
    """Central registry for all plugin hook points"""
    
    # Interactive session hooks
    INTERACTIVE_COMMAND = "interactive.command"           # Custom /commands
    INTERACTIVE_SESSION_START = "interactive.session_start"  # Session begins
    INTERACTIVE_SESSION_END = "interactive.session_end"     # Session ends
    INTERACTIVE_PRE_RESPONSE = "interactive.pre_response"   # Before LLM response
    INTERACTIVE_POST_RESPONSE = "interactive.post_response" # After LLM response
    
    # Core system hooks
    ARTICLE_FETCHED = "core.article_fetched"             # New article added
    BRIEFING_GENERATED = "core.briefing_generated"       # Briefing complete
    CONFIG_UPDATED = "core.config_updated"               # Config changed