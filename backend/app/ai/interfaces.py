"""
ProofBridge — AI Interface Abstractions
"""
from abc import ABC, abstractmethod
from typing import Optional, Protocol, Dict, Any, List

class LLMProvider(Protocol):
    """Abstract LLM provider interface."""
    
    @abstractmethod
    async def generate_json(self, system_prompt: str, user_prompt: str) -> dict:
        """Generate a structured JSON response."""
        ...

    @abstractmethod
    def provider_name(self) -> str:
        """Name of the provider (e.g., OLLAMA, GEMINI)."""
        ...
        
    @abstractmethod
    def model_name(self) -> str:
        """Name of the model being used."""
        ...


class IntentResult(Protocol):
    # Defined in ai_models schema
    pass
    
class ClaimResult(Protocol):
    pass

class EvidencePlanResult(Protocol):
    pass
    
class PrivacyPlanResult(Protocol):
    pass


class ModelRole(Protocol):
    """Base protocol for a specialized AI agent."""
    pass


class IntentModel(ModelRole):
    @abstractmethod
    async def extract_intent(self, request_text: str) -> IntentResult:
        ...

class ClaimModel(ModelRole):
    @abstractmethod
    async def compile_claim(self, intent: IntentResult) -> ClaimResult:
        ...

class EvidenceModel(ModelRole):
    @abstractmethod
    async def map_evidence(self, claim: ClaimResult, evidence_metadata: list[dict]) -> EvidencePlanResult:
        ...

class PrivacyModel(ModelRole):
    @abstractmethod
    async def plan_privacy(self, claim: ClaimResult, evidence_plan: EvidencePlanResult, capabilities: list[dict]) -> PrivacyPlanResult:
        ...

class CriticModel(ModelRole):
    @abstractmethod
    async def evaluate_plan(self, request: str, claim: ClaimResult, privacy: PrivacyPlanResult) -> dict:
        ...
