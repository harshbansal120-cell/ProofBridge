"""
ProofBridge — Gemini LLM Provider
"""
import json
import logging
from typing import Optional
from app.config import GEMINI_API_KEY, GEMINI_MODEL
from app.ai.interfaces import LLMProvider

logger = logging.getLogger(__name__)

class GeminiProvider(LLMProvider):
    """Google Gemini API provider."""

    def __init__(self):
        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY not set")
        from google import genai
        self.client = genai.Client(api_key=GEMINI_API_KEY)
        self.model = GEMINI_MODEL

    async def generate_json(self, system_prompt: str, user_prompt: str) -> dict:
        from google.genai import types
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=0.1,
                    response_mime_type="application/json",
                ),
            )
            raw = response.text
            return json.loads(raw)
        except json.JSONDecodeError:
            logger.error(f"Gemini API returned invalid JSON: {response.text}")
            raise Exception("Gemini returned invalid JSON.")
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            raise

    def provider_name(self) -> str:
        return "GEMINI"

    def model_name(self) -> str:
        return self.model
