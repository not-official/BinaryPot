# ai_cache.py

# A simple dictionary to hold our memory
# Key = Command string (e.g., "uname -a")
# Value = The AI's response
_response_cache = {}

def get_cached_response(cmdline: str):
    """
    Checks if we have seen this command before.
    Returns the response if found, or None if not.
    """
    return _response_cache.get(cmdline)

def set_cached_response(cmdline: str, response: str):
    """
    Saves a new response to memory.
    """
    _response_cache[cmdline] = response
    print(f"[AICache] Saved response for: '{cmdline}'")