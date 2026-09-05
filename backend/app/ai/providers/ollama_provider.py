"""
ProofBridge — Ollama LLM Provider
"""
import json
import logging
import httpx
from typing import Optional
from app.config import OLLAMA_BASE_URL
from app.ai.interfaces import LLMProvider

logger = logging.getLogger(__name__)

class OllamaProvider(LLMProvider):
    """Local inference provider wrapping Ollama."""
    
    def __init__(self, model_name: str):
        self._model = model_name
        self.base_url = OLLAMA_BASE_URL.rstrip('/')
        
    async def generate_json(self, system_prompt: str, user_prompt: str) -> dict:
        payload = {
            "model": self._model,
            "system": system_prompt,
            "prompt": user_prompt,
            "format": "json",
            "stream": False,
            "options": {
                "temperature": 0.1
            }
        }
        try:
            async with httpx.AsyncClient(timeout=45.0) as client:
                response = await client.post(f"{self.base_url}/api/generate", json=payload)
                
            if response.status_code != 200:
                body = response.text
                logger.error(f"Ollama returned HTTP {response.status_code}: {body}")
                raise Exception(f"OPEN_SOURCE_MODEL_UNAVAILABLE: {self._model} failed to respond.")
                
            data = response.json()
            if "response" not in data:
                raise Exception("Ollama unexpected response missing 'response' field.")
                
            # Parse the inner JSON response
            raw_json_str = data["response"]
            return json.loads(raw_json_str)
            
        except httpx.RequestError as e:
            logger.error(f"Failed to reach Ollama at {self.base_url}: {e}")
            raise Exception("OPEN_SOURCE_MODEL_UNAVAILABLE: Ollama is unreachable.")
        except json.JSONDecodeError as e:
            logger.error(f"Ollama returned invalid JSON. Raw block: {raw_json_str[:200]}")
            raise Exception("Ollama failed to return valid JSON.")

    def provider_name(self) -> str:
        return "OLLAMA"

    def model_name(self) -> str:
        return self._model
