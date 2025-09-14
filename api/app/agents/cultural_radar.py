from ..services.openai_client import get_completion
from ..services.scraper import scrape_site
import json

async def run_cultural_radar(brand: dict, competitors: list) -> dict:
    competitor_data = []
    for comp in competitors[:3]:
        scraped = await scrape_site(str(comp["url"]))
        competitor_data.append({"name": comp["name"], "data": scraped})
    
    prompt = f"""
    Create a Cultural Radar analysis for {brand["name"]} in {brand.get("category", "market")}.
    
    Competitor context: {json.dumps(competitor_data, indent=2)}
    
    Return JSON with this structure:
    {{
        "executive_summary": {{
            "top_cultural_trends": [
                {{"trend": "Authenticity Movement", "growth": "+45%", "lifecycle": "Scaling"}}
            ],
            "key_opportunities": ["List of 2-3 opportunities"],
            "competitive_gaps": ["List of gaps vs competitors"]
        }},
        "consumer_signals": [
            {{
                "signal": "Authenticity Demand",
                "volume": 1800,
                "change": "+28.6%",
                "platforms": ["TikTok", "Instagram"],
                "opportunity": "Launch transparency campaign"
            }}
        ],
        "recommendations": [
            {{
                "action": "Launch authenticity content series",
                "priority": "High",
                "effort": "Medium",
                "roi_potential": "High",
                "timeline": "0-30 days"
            }}
        ],
        "confidence": "78%"
    }}
    """
    
    return await get_completion(prompt)
