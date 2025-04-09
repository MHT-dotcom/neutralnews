from werkzeug.utils import secure_filename

def secure_log_key(api_key, visible_chars=4):
    """
    Securely mask API keys and tokens for logging purposes.
    
    Args:
        api_key (str): The API key to mask
        visible_chars (int): Number of characters to show at start and end
    
    Returns:
        str: A masked version of the API key
    """
    if not api_key or not isinstance(api_key, str):
        return "Not set"
        
    if len(api_key) <= visible_chars * 2:
        return "*" * len(api_key)
    
    # Show first and last few characters, mask the middle
    visible_start = api_key[:visible_chars]
    visible_end = api_key[-visible_chars:]
    masked_length = len(api_key) - (visible_chars * 2)
    
    return f"{visible_start}{'*' * masked_length}{visible_end}" 