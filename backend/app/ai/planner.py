import abc
import json
import logging
from google import genai
from pydantic import ValidationError

from app.schemas.ai_models import PlannerResult
from app.ai.providers.gemini_provider import GeminiProvider
from app.ai.providers.ollama_provider import OllamaProvider

logger = logging.getLogger(__name__)

class AIPlanner(abc.ABC):
    @abc.abstractmethod
    async def plan(self, request_text: str) -> PlannerResult:
        pass


class GeminiPlanner(AIPlanner):
    def __init__(self, provider: GeminiProvider):
        self.provider = provider
        
    async def plan(self, request_text: str) -> PlannerResult:
        logger.info(f"Using GeminiPlanner: generating unified plan for request.")
        prompt = f"""
You are ProofBridge, an AI privacy proof planner.
Analyze the following natural-language verification request and generate a privacy-preserving execution plan.

USER REQUEST:
"{request_text}"

INSTRUCTIONS:
1. Identify the 'intent' and 'claim'. Extract the exact mathematical threshold (e.g. 1000000) and semantic unit (e.g. INR - do NOT convert to paisa).
2. Detail the 'evidence_requirements' necessary to prove the claim (e.g. TRANSACTION_LEDGER).
3. Specify a 'privacy_objective' by listing fields to hide.
4. Recommend a 'proof_strategy' (preferred: ZERO_KNOWLEDGE if feasible mathematically, fallback: SELECTIVE_DISCLOSURE).

Return your response strictly in the requested JSON structure.
"""
        response_text = await self.provider.generate_structured(
            prompt=prompt,
            response_schema=PlannerResult
        )
        # Parse Pydantic object
        from app.schemas.ai_models import PlannerResult
        return PlannerResult.model_validate_json(response_text)


class OllamaPlanner(AIPlanner):
    def __init__(self, provider: OllamaProvider):
        self.provider = provider
        
    async def plan(self, request_text: str) -> PlannerResult:
        logger.info(f"Using OllamaPlanner: generating unified plan for request.")
        
        # We enforce a strict JSON output matching PlannerResult
        schema_format = PlannerResult.model_json_schema()
        
        prompt = f"""
You are ProofBridge, an AI privacy proof planner.
Analyze the following natural-language verification request and generate a privacy-preserving execution plan.

USER REQUEST:
"{request_text}"

INSTRUCTIONS:
1. Identify the exact mathematical threshold (e.g. 1000000) and semantic unit (e.g. INR - do NOT convert to paisa).
2. Suggest the type of evidence required (e.g. TRANSACTION_LEDGER).
3. Identify fields to hide for privacy.
4. Preferred strategy should be ZERO_KNOWLEDGE if math-based constraint applies, else SELECTIVE_DISCLOSURE.

OUTPUT FORMAT:
Provide the output strictly as a JSON object matching this schema:
{json.dumps(schema_format, indent=2)}

Do NOT include markdown backticks or any other text. Output ONLY valid JSON.
"""
        response_text = await self.provider.generate_text(prompt=prompt)
        
        # Clean up possible markdown or extra text from raw open-source LLM
        response_text = response_text.strip()
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
            
        try:
            return PlannerResult.model_validate_json(response_text.strip())
        except ValidationError as e:
            logger.error(f"OllamaPlanner output validation failed: {e}")
            raise Exception("Ollama model failed to generate compliant structured PlannerResult schema.")


class MockDemoProvider:
    def provider_name(self): return "demo"
    def model_name(self): return "demo-v1"

class DemoPlanner(AIPlanner):
    def __init__(self):
        self.provider = MockDemoProvider()
        
    async def plan(self, request_text: str) -> PlannerResult:
        logger.info(f"Using DemoPlanner: generating deterministic plan for request.")
        return PlannerResult.model_validate({
          "intent": {
            "request": request_text,
            "ambiguities": [],
            "confidence": 0.99
          },
          "claim": {
            "operation": "SUM",
            "field": "amount",
            "operator": ">",
            "threshold": {
              "value": 1000000.0,
              "unit": "INR",
              "source": "USER_REQUEST"
            },
            "currency": "INR",
            "transaction_status": "SUCCESS",
            "period": "LAST_N_MONTHS",
            "period_value": 6,
            "merchant_scope": "MERCHANT-99" if "MERCHANT-99" in request_text else "MERCHANT-42"
          },
          "evidence_requirements": [
            {
              "type": "PROCESSOR_ATTESTED_LEDGER",
              "required_fields": ["amount"],
              "provenance_required": True
            }
          ],
          "privacy_objective": {
            "hide": ["amount", "customer_identity"]
          },
          "proof_strategy": {
            "preferred": "ZERO_KNOWLEDGE",
            "fallback": "SELECTIVE_DISCLOSURE"
          }
        })
