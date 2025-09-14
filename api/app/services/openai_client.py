# api/app/services/openai_client.py
import json
import httpx
from ..settings import settings

OPENAI_URL = "https://api.openai.com/v1/chat/completions"

def _headers():
    return {
        "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }

async def get_completion(messages, model: str = "gpt-4o-mini", temperature: float = 0.2):
    """
    Thin async wrapper around OpenAI's chat completions.
    messages = [{"role":"system","content":"..."},{"role":"user","content":"..."}]
    Returns parsed JSON from OpenAI.
    """
    # Safe fallback if no key set — returns a mock payload so UI won't crash
    if not settings.OPENAI_API_KEY:
        return {
            "choices": [
                {"message": {"content": json.dumps({"mock": True, "note": "Set OPENAI_API_KEY to enable real outputs."})}}
            ]
        }

    payload = {"model": model, "temperature": temperature, "messages": messages}
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(OPENAI_URL, headers=_headers(), json=payload)
        r.raise_for_status()
        return r.json()

# Optional alias if other modules expect `chat(...)`
async def chat(messages, model: str = "gpt-4o-mini", temperature: float = 0.2):
    return await get_completion(messages, model=model, temperature=temperature)

