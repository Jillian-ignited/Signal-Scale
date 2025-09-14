from ..services.openai_client import get_completion
from ..services.scraper import scrape_site
import json

async def run_competitive_playbook(brand: dict, competitors: list) -> dict:
    competitor_data = []
    for comp in competitors:
        scraped = await scrape_site(str(comp["url"]))
        competitor_data.append({"name": comp["name"], "data": scraped})
    
    prompt = f"""
    Create a Competitive Playbook for {brand["name"]} vs competitors.
    
    Competitive landscape: {json.dumps(competitor_data, indent=2)}
    
    Return JSON with this structure:
    {{
        "competitive_position": {{
            "overall_score": "7.2/10",
            "market_rank": "#4 of {len(competitors) + 1} analyzed",
            "key_differentiators": ["List strengths"],
            "vulnerability_areas": ["List weaknesses"]
        }},
        "competitor_analysis": [
            {{
                "name": "{competitors[0]['name'] if competitors else 'Competitor'}",
                "strengths": ["Their advantages"],
                "weaknesses": ["Their gaps"],
                "threat_level": "High",
                "opportunities_to_counter": ["How to compete"]
            }}
        ],
        "strategic_moves": [
            {{
                "initiative": "Community-First Strategy",
                "rationale": "Why this move",
                "timeline": "Q4 2024",
                "investment": "Medium",
                "expected_impact": "Brand loyalty +40%"
            }}
        ],
        "quick_wins": [
            {{
                "action": "Implement customer reviews",
                "effort": "Low",
                "impact": "High",
                "timeline": "2-4 weeks"
            }}
        ]
    }}
    """
    
    return await get_completion(prompt)
