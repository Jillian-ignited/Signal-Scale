# api/app/agents/cultural_radar.py
import json
from datetime import datetime
from ..services.openai_client import get_completion

SYSTEM = {
    "role": "system",
    "content": (
        "You are Cultural Radar. Return STRICT JSON only. Keys: "
        "report_meta, executive_summary, momentum_scorecard, consumer_signals, "
        "competitive_overlay, prospects, action_grid, historical, confidence_footer. "
        "Use arrows (↑↔↓), ASCII heat bars, quantified volumes & WoW deltas. "
        "No markdown; JSON object only."
    ),
}

async def run_cultural_radar(payload: dict) -> dict:
    """
    Accepts a payload with keys: brand, competitors, window.
    Calls OpenAI and returns a parsed JSON dict. If the LLM returns invalid JSON,
    we wrap the raw string so the API still responds.
    """
    user = {"role": "user", "content": json.dumps(payload)}
    res = await get_completion([SYSTEM, user])

    # Extract the assistant content
    try:
        content = res["choices"][0]["message"]["content"]
    except Exception:
        # Defensive fallback
        return {
            "error": "OpenAI response missing content",
            "raw": res,
            "generated_at": datetime.utcnow().isoformat(),
        }

    # Try to parse JSON
    try:
        data = json.loads(content)
        # Ensure a minimal meta block
        data.setdefault("report_meta", {})
        data["report_meta"].update({
            "agent": "cultural_radar",
            "generated_at": datetime.utcnow().isoformat(),
        })
        return data
    except Exception:
        # Return raw if the model sent non-JSON (keeps UI from crashing)
        return {
            "error": "LLM did not return valid JSON",
            "raw": content,
            "generated_at": datetime.utcnow().isoformat(),
        }
