import httpx
import json
import logging
from typing import Optional

from app.config import OPENROUTER_API_KEY, OPENROUTER_MODEL
from app.schemas.ai_models import PlannerResult
from app.ai.planner import AIPlanner

logger = logging.getLogger(__name__)

class OpenRouterProvider:
    def provider_name(self): return "openrouter"
    def model_name(self): return OPENROUTER_MODEL

class OpenRouterPlanner(AIPlanner):
    """
    Production Planner. Uses OpenRouter API.
    Enforces Strict Structured Output (JSON mode).
    """
    def __init__(self):
        if not OPENROUTER_API_KEY:
            raise Exception("REAL AI PLANNER UNAVAILABLE: OPENROUTER_API_KEY missing")
        if not OPENROUTER_MODEL:
            raise Exception("REAL AI PLANNER UNAVAILABLE: OPENROUTER_MODEL explicitly required in production")
            
        self.provider = OpenRouterProvider()
        self.client = httpx.AsyncClient(timeout=30.0)

    async def plan(self, request_text: str) -> PlannerResult:
        logger.info(f"Using OpenRouterPlanner with model {OPENROUTER_MODEL}")
        
        system_prompt = """
You are the ProofBridge AI Planner.
Your job is to parse a natural language request into a strict mathematical requirement.

CRITICAL RULES:
1. You must output ONLY a raw, complete JSON object conforming exactly to the PlannerResult schema.
2. If multiple criteria are requested, YOU MUST USE THE COMPOSITE SCHEMA. Do NOT silently drop predicates. Output: "type": "COMPOSITE", "operator": "AND", "predicates": [ { ... }, { ... } ]
3. NEVER attempt to define cryptographic execution settings, nonces, circuit paths, or anything outside your explicit schema. DO NOT invent support for features in the cryptographic layer.
4. Scale all constraints to base units correctly, but preserve the exact operator constraints provided by the user.

SCHEMA REQUIREMENTS:
The JSON MUST CONTAIN these top-level keys identically:
- "intent": {"request": "...", "ambiguities": [], "confidence": ...}
- "claim": {"type": "SINGLE" | "COMPOSITE", "operator": ..., "predicates": [], "operation": ..., "field": ..., "threshold": {"value": ..., "unit": ...}}
- "evidence_requirements": [{"type": "...", "required_fields": [], "provenance_required": true}]
- "privacy_objective": {"hide": []}
- "proof_strategy": {"preferred": "ZERO_KNOWLEDGE", "fallback": "SELECTIVE_DISCLOSURE"}

Provide ONLY the JSON output with absolutely no conversational text or markdown formatting.
        """.strip()

        payload = {
            "model": OPENROUTER_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Request: {request_text}"}
            ],
            "response_format": {"type": "json_object"},
            "max_tokens": 2048
        }

        try:
            response = await self.client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "Content-Type": "application/json"
                },
                json=payload
            )
            response.raise_for_status()
            data = response.json()
            
            # Safe extraction
            if "choices" not in data or not data["choices"]:
                raise Exception("Provider returned malformed completion response")
                
            response_text = data["choices"][0]["message"]["content"]
            
            # Clean up potential markdown formatting OpenRouter sends sometimes
            response_text = response_text.strip()
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
                
            response_text = response_text.strip()
            
            planner_result = PlannerResult.model_validate_json(response_text)
            return planner_result
            
        except httpx.HTTPStatusError as e:
            logger.error(f"OpenRouter HTTP Error: {e.response.status_code} - {e.response.text}")
            raise Exception("Provider HTTP Error")
        except httpx.RequestError as e:
            logger.error(f"OpenRouter Network Timeout/Error: {e}")
            raise Exception("Provider Request Error")
        except Exception as e:
            logger.error(f"OpenRouterPlanner Validation/Parsing Failed: {e}")
            raise Exception(f"Schema parsing error: {e}")
