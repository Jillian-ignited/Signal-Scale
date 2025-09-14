import httpx
import json
from ..settings import settings

async def get_completion(prompt: str, model: str = "gpt-4o-mini") -> dict:
    if not settings.OPENAI_API_KEY:
        return {
            "analysis": {
                "status": "mock_response",
                "message": "Set OPENAI_API_KEY for real AI analysis",
                "executive_summary": {
                    "key_opportunities": [
                        "Mobile experience optimization (+35% conversion potential)",
                        "Content marketing strategy development",
                        "Community building initiatives"
                    ],
                    "competitive_gaps": [
                        "Social media engagement vs competitors",
                        "Mobile-first design implementation"
                    ]
                },
                "recommendations": [
                    {
                        "action": "Implement mobile-first design strategy",
                        "priority": "High",
                        "effort": "Medium",
                        "roi_potential": "High",
                        "timeline": "30-60 days"
                    }
                ]
            }
        }
    
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {settings.OPENAI_API_KEY}"
                },
                json={
                    "model": model,
                    "max_tokens": 2000,
                    "temperature": 0.7,
                    "messages": [{"role": "user", "content": prompt}]
                }
            )
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                return {"analysis": {"raw_response": content}}
                
    except Exception as e:
        return {"analysis": {"error": str(e), "status": "api_error"}}
