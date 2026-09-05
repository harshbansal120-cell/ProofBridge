"""
ProofBridge — AI Factory
"""
import logging
from app.config import (
    AI_MODE, 
    PROOFBRIDGE_INTENT_MODEL, 
    PROOFBRIDGE_CLAIM_MODEL,
    PROOFBRIDGE_EVIDENCE_MODEL,
    PROOFBRIDGE_PRIVACY_MODEL,
    PROOFBRIDGE_CRITIC_MODEL
)
from app.ai.interfaces import LLMProvider
from app.ai.providers.demo_provider import DemoProvider
from app.ai.providers.gemini_provider import GeminiProvider
from app.ai.providers.ollama_provider import OllamaProvider
from app.ai.models_qwen import (
    GenericIntentModel, GenericClaimModel, GenericEvidenceModel, 
    GenericPrivacyModel, GenericCriticModel
)
from app.ai.planner import AIPlanner, GeminiPlanner, OllamaPlanner, DemoPlanner
from app.ai.providers.openrouter_provider import OpenRouterPlanner

logger = logging.getLogger(__name__)

def get_provider(mode: str, model_name: str = "") -> LLMProvider:
    if mode == "demo":
        return DemoProvider()
    elif mode == "gemini":
        try:
            return GeminiProvider()
        except Exception as e:
            logger.error(f"Failed to load Gemini: {e}")
            raise
    elif mode == "open_source":
        return OllamaProvider(model_name)
    else:
        raise ValueError(f"Unknown AI_MODE: {mode}")

class AIFactory:
    @staticmethod
    def get_intent_model(mode: str = AI_MODE) -> GenericIntentModel:
        return GenericIntentModel(get_provider(mode, PROOFBRIDGE_INTENT_MODEL))

    @staticmethod
    def get_claim_model(mode: str = AI_MODE) -> GenericClaimModel:
        return GenericClaimModel(get_provider(mode, PROOFBRIDGE_CLAIM_MODEL))

    @staticmethod
    def get_evidence_model(mode: str = AI_MODE) -> GenericEvidenceModel:
        return GenericEvidenceModel(get_provider(mode, PROOFBRIDGE_EVIDENCE_MODEL))

    @staticmethod
    def get_privacy_model(mode: str = AI_MODE) -> GenericPrivacyModel:
        return GenericPrivacyModel(get_provider(mode, PROOFBRIDGE_PRIVACY_MODEL))

    @staticmethod
    def get_critic_model(mode: str = AI_MODE) -> GenericCriticModel:
        return GenericCriticModel(get_provider(mode, PROOFBRIDGE_CRITIC_MODEL))

    @staticmethod
    def get_planner(mode: str = AI_MODE) -> AIPlanner:
        if mode == "production":
            return OpenRouterPlanner()
        elif mode == "demo":
            return DemoPlanner()
        elif mode == "gemini":
            return GeminiPlanner(get_provider(mode))
        elif mode == "open_source" or mode == "ensemble":
            # For ensemble we will orchestrate them both in orchestrator
            # But defaults to ollama for generic open source
            provider = get_provider("open_source", PROOFBRIDGE_INTENT_MODEL)
            # Make sure OllamaPlanner is initialized properly
            return OllamaPlanner(provider)
        else:
            return GeminiPlanner(get_provider("gemini"))
