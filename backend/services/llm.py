"""LLM preference parsing and explanation (spec FR-010, FR-011, FR-013, FR-014; research R7)."""
import json

import requests

from ..config import Config
from ..api import schemas

_TIMEOUT = 20
FALLBACK_PREFERENCE = {"alpha": 0.5, "avoid_classes": [], "interpreted": False}

_PREFERENCE_SYSTEM = (
    "You convert a driver's natural-language preference about road safety into JSON. "
    'Respond ONLY with JSON: {"alpha": number between 0 and 1 (1 = prioritize safety, '
    '0 = prioritize time), "avoidClasses": array of hazard classes to penalize, chosen '
    'from ["pothole","crack","damaged_patch","waterlogging","uneven_surface"]}.'
)

_EXPLAIN_SYSTEM = (
    "You explain a route recommendation in 1-2 plain sentences. Reference the trade-off "
    "between travel time and safety, and the hazards avoided. Do not invent facts."
)


def _chat(system, user, api_key=None, model=None, base_url=None, json_mode=False):
    api_key = api_key or Config.LLM_API_KEY
    model = model or Config.LLM_MODEL
    base_url = (base_url or Config.LLM_BASE_URL).rstrip("/")
    if not api_key:
        return None
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0,
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
    try:
        resp = requests.post(
            f"{base_url}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=payload,
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]
    except (requests.RequestException, KeyError, IndexError, ValueError):
        return None


def parse_preference(text, api_key=None, model=None, base_url=None):
    """Map free text to {alpha, avoid_classes, interpreted}. Falls back to balanced."""
    if not text or not text.strip():
        return dict(FALLBACK_PREFERENCE)
    content = _chat(_PREFERENCE_SYSTEM, text, api_key, model, base_url, json_mode=True)
    if not content:
        return dict(FALLBACK_PREFERENCE)
    try:
        parsed = json.loads(content)
    except (ValueError, TypeError):
        return dict(FALLBACK_PREFERENCE)
    if not isinstance(parsed, dict) or "alpha" not in parsed:
        return dict(FALLBACK_PREFERENCE)
    return {
        "alpha": schemas.clamp_alpha(parsed.get("alpha", 0.5)),
        "avoid_classes": schemas.valid_avoid_classes(parsed.get("avoidClasses", [])),
        "interpreted": True,
    }


def explain(recommended, alternatives, api_key=None, model=None, base_url=None):
    """Generate a plain-language justification. Degrades to generated=False."""
    payload = {
        "recommended": {
            "duration_min": round(recommended["duration_s"] / 60.0, 1),
            "safety_score": round(recommended["safety_score"], 1),
            "hazards": recommended.get("hazard_summary", {}),
        },
        "alternatives": [
            {
                "duration_min": round(a["duration_s"] / 60.0, 1),
                "safety_score": round(a["safety_score"], 1),
                "hazards": a.get("hazard_summary", {}),
            }
            for a in alternatives
        ],
    }
    user = (
        "Explain why this route was recommended. Data (JSON):\n"
        + json.dumps(payload)
    )
    content = _chat(_EXPLAIN_SYSTEM, user, api_key, model, base_url)
    if not content:
        return {"text": "", "generated": False}
    return {"text": content.strip(), "generated": True}
