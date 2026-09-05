"""
ProofBridge — AI Specialized Models (Qwen default logic)

Implements ModelRoles mapping an LLMProvider to Pydantic schemas.
"""
import logging
from typing import List, Dict, Any
from app.ai.interfaces import (
    IntentModel, ClaimModel, EvidenceModel, PrivacyModel, CriticModel,
    LLMProvider
)
from app.schemas.ai_models import (
    IntentResult, ClaimResult, EvidencePlanResult, PrivacyStrategyResult, CriticResult
)
from pydantic import ValidationError

logger = logging.getLogger(__name__)

class GenericIntentModel(IntentModel):
    def __init__(self, provider: LLMProvider):
        self.provider = provider
        
    async def extract_intent(self, request_text: str) -> IntentResult:
        system = """You are ProofBridge Intent Model.
Extract verification intent into strict JSON.
Fields:
- request_type (e.g. FINANCIAL_THRESHOLD_VERIFICATION)
- subject
- metric
- period (type, scope)
- operator (GREATER_THAN, LESS_THAN, MATCH, EXISTS, etc.)
- threshold (value, unit, source_text, source="USER_REQUEST")
- evidence_category
- confidence (0.0 to 1.0)
- ambiguities (list of strings)

DO NOT invent thresholds or change units.
If a threshold is ambiguous or missing for a mathematical operation, add it to 'ambiguities'.
"""
        raw = await self.provider.generate_json(system, request_text)
        try:
            return IntentResult(**raw)
        except ValidationError as e:
            logger.error(f"Intent validation failed: {str(e)}")
            raise

class GenericClaimModel(ClaimModel):
    def __init__(self, provider: LLMProvider):
        self.provider = provider
        
    async def compile_claim(self, intent: IntentResult) -> ClaimResult:
        system = """You are ProofBridge Claim Compiler.
Convert the intent into ProofBridge Claim DSL JSON.
Fields:
- claim_id (e.g., C001)
- subject
- operation (SUM, AVERAGE, COUNT, AGE, MATCH, EXISTS)
- dataset (e.g., transactions)
- field (e.g., amount)
- operator (>, >=, <, <=, ==, !=)
- threshold (value, unit, source_text, source) 
  IMPORTANT: NEVER invent 'PAISA' or circuit scaled values. Preserve source.
- time_scope (type, scope)
- source_text
- confidence (0.0 to 1.0)
- ambiguities (list of strings)
"""
        user_prompt = f"Intent:\n{intent.model_dump_json()}"
        raw = await self.provider.generate_json(system, user_prompt)
        try:
            return ClaimResult(**raw)
        except ValidationError as e:
            logger.error(f"Claim validation failed: {str(e)}")
            raise

class GenericEvidenceModel(EvidenceModel):
    def __init__(self, provider: LLMProvider):
        self.provider = provider
        
    async def map_evidence(self, claim: ClaimResult, evidence_metadata: list[dict]) -> EvidencePlanResult:
        system = """You are ProofBridge Evidence Mapper.
Map the formal claim to available evidence categories.
You DO NOT verify authenticity. You map semantic fit.
Extract to JSON:
{
  "evidence_sources": [
    {
      "type": "CATEGORY (e.g., PROCESSOR_ATTESTED_LEDGER, VERIFIED_CREDENTIAL)",
      "supports": ["array of fields"],
      "trust_level": "REQUIRED_TRUST (e.g. HIGH, PROCESSOR_ATTESTED)"
    }
  ]
}
AVAILABLE METADATA:
""" + "\n".join([str(m) for m in evidence_metadata])
        
        user_prompt = f"Claim:\n{claim.model_dump_json()}"
        raw = await self.provider.generate_json(system, user_prompt)
        try:
            return EvidencePlanResult(**raw)
        except ValidationError as e:
            logger.error(f"Evidence mapping validation failed: {str(e)}")
            raise

class GenericPrivacyModel(PrivacyModel):
    def __init__(self, provider: LLMProvider):
        self.provider = provider
        
    async def plan_privacy(self, claim: ClaimResult, evidence_plan: EvidencePlanResult, capabilities: list[dict]) -> PrivacyStrategyResult:
        system = """You are ProofBridge Privacy Planner.
Select the minimum-disclosure strategy.
Allowed strategies: ZERO_KNOWLEDGE, SELECTIVE_DISCLOSURE, VERIFIABLE_CREDENTIAL, REDACTION, HUMAN_REVIEW, UNSUPPORTED.
IMPORTANT: You may recommend ZERO_KNOWLEDGE if feasible mathematically, but be mindful of the capabilities provided.

JSON Output:
- claim_id
- strategy
- reason
- why_not_alternatives (dictionary)
- privacy_gain
- zk_feasible (boolean: is it theoretically a ZK math predicate?)
"""
        user_prompt = f"Claim:\n{claim.model_dump_json()}\nEvidence Plan:\n{evidence_plan.model_dump_json()}\nCapabilities (From Backend):\n{capabilities}"
        raw = await self.provider.generate_json(system, user_prompt)
        try:
            return PrivacyStrategyResult(**raw)
        except ValidationError as e:
            logger.error(f"Privacy validation failed: {str(e)}")
            raise

class GenericCriticModel(CriticModel):
    def __init__(self, provider: LLMProvider):
        self.provider = provider
        
    async def evaluate_plan(self, request: str, claim: ClaimResult, privacy: PrivacyStrategyResult) -> CriticResult:
        system = """You are ProofBridge Critic. Evaluate the AI's plan.
Check:
- Was a threshold invented?
- Was the currency/unit changed?
- Did they hallucinate a predicate?

JSON Output:
- approved (boolean)
- issues (list)
- warnings (list)
"""
        user_prompt = f"Original Request: {request}\nClaim:\n{claim.model_dump_json()}\nPrivacy:\n{privacy.model_dump_json()}"
        raw = await self.provider.generate_json(system, user_prompt)
        try:
            return CriticResult(**raw)
        except ValidationError as e:
            logger.error(f"Critic validation failed: {str(e)}")
            raise
