from ..services.openai_client import get_completion
from ..services.scraper import scrape_site
import json

async def run_dtc_audit(brand: dict, competitors: list) -> dict:
    brand_data = await scrape_site(str(brand["url"]))
    competitor_data = []
    
    for comp in competitors[:3]:
        scraped = await scrape_site(str(comp["url"]))
        competitor_data.append({"name": comp["name"], "data": scraped})
    
    prompt = f"""
    Conduct DTC audit for {brand["name"]}.
    
    Brand data: {json.dumps(brand_data, indent=2)}
    Competitors: {json.dumps(competitor_data, indent=2)}
    
    Return JSON with this structure:
    {{
        "performance_overview": {{
            "overall_grade": "B+ (7.8/10)",
            "primary_strengths": ["Mobile experience", "Product pages"],
            "critical_weaknesses": ["Social proof", "Checkout flow"],
            "improvement_potential": "+35% revenue with optimizations"
        }},
        "category_scores": [
            {{
                "category": "User Experience",
                "current_score": "8.0/10",
                "performance": "Above Average",
                "improvement_areas": ["Mobile menu", "Search functionality"]
            }}
        ],
        "optimization_recommendations": [
            {{
                "recommendation": "Add customer review system with photos",
                "priority": "High",
                "effort": "Medium",
                "timeline": "4-6 weeks",
                "expected_impact": "+25% conversion rate"
            }}
        ],
        "competitive_gaps": [
            {{
                "competitor": "{competitors[0]['name'] if competitors else 'Leader'}",
                "what_they_do_better": "Advanced personalization",
                "how_to_close_gap": "Implement recommendation engine"
            }}
        ]
    }}
    """
    
    return await get_completion(prompt)
