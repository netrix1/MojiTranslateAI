from app.core.config import settings
print(f"API Key present: {bool(settings.llm_api_key)}")
if settings.llm_api_key:
    print(f"Key preview: {settings.llm_api_key[:10]}...")
