import os
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("--- [CONFIG] Local .env detected and loaded ---")
except ImportError:
    print("--- [CONFIG] dotenv library not found, using system environment ---")

def get_env_var(key, default=""):
    """Helper to get a key, strip quotes/spaces, and handle defaults."""
    val = os.getenv(key, default)
    if val:
        return val.strip().strip("'").strip('"')
    return val

# Load keys
OPENROUTER_API_KEY = get_env_var("OPENROUTER_API_KEY")
HF_TOKEN = get_env_var("HF_TOKEN")
OPENROUTER_MODEL = get_env_var("OPENROUTER_MODEL", "meta-llama/llama-3-8b-instruct")

# DEBUG: Safe logging (only first 10 characters)
if OPENROUTER_API_KEY:
    print(f"--- [CONFIG] OpenRouter Key Active: {OPENROUTER_API_KEY[:10]}... ---")
else:
    print("--- [ERROR] OPENROUTER_API_KEY is missing! ---")