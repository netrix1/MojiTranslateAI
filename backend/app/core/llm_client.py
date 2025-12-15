from openai import OpenAI
import os
from app.core.config import settings

def get_llm_client():
    """
    Returns an OpenAI compatible client.
    Configured via settings (loaded from .env):
    """
    api_key = settings.llm_api_key or os.getenv("LLM_API_KEY")
    base_url = settings.llm_base_url or os.getenv("LLM_BASE_URL")
    
    if not api_key:
        # Check if maybe base_url allows anonymous (like Ollama sometimes?)
        # But usually client needs something.
        if base_url:
             api_key = "dummy"
        else:
             return None

    return OpenAI(
        api_key=api_key,
        base_url=base_url if base_url else None
    )

def translate_text(text: str, context: str = "") -> str:
    """
    Translates text to Portuguese (Brazil) using the configured LLM.
    """
    client = get_llm_client()
    if not client:
        return f"[MOCK] {text}"
        
    model = os.getenv("LLM_MODEL", "gpt-3.5-turbo")
    
    system_prompt = """You are a professional manga translator. Translate the following text from Japanese/English to Portuguese (Brazil).
    Maintain the tone and nuance. Output ONLY the translation, no explanations.
    If the text is a sound effect (SFX), try to adapt it or leave it if untranslatable, but prefer Portuguese onomatopoeia.
    """
    
    if context:
        system_prompt += f"\nContext: {context}"

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text}
            ],
            temperature=0.3,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"LLM Error: {e}")
        return f"[ERR] {text}"
