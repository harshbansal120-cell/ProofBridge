"""
ProofBridge — AI Pydantic Schemas

Formal definitions for modular AI step outputs.
Includes deterministic semantic validation on thresholds and units.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict, model_validator
from app.schemas.models import ClaimOperation, ClaimOperator, PrivacyStrategyType

class ThresholdValue(BaseModel):
    value: Optional[float] = None
    unit: Optional[str] = None
    source_text: Optional[str] = None
    source: str = Field(default="USER_REQUEST")

class TimeScope(BaseModel):
    type: str = Field(description="e.g. MONTH, YEAR, QUARTER, None")
    scope: Optional[str] = Field(default=None, description="e.g. PREVIOUS_QUARTER")

class IntentResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_type: str = Field(description="e.g. FINANCIAL_THRESHOLD_VERIFICATION")
    subject: str = Field(description="e.g. merchant")
    metric: str
    period: Optional[TimeScope] = None
    operator: str = Field(description="GREATER_THAN, LESS_THAN, MATCH, etc.")
    threshold: Optional[ThresholdValue] = None
    evidence_category: Optional[str] = None
    confidence: float = Field(ge=0.0, le=1.0)
    ambiguities: List[str] = Field(default_factory=list)

class ClaimResult(BaseModel):
    """The central Claim DSL to which all intent interpretations must compile."""
    model_config = ConfigDict(extra="forbid")
    
    claim_id: str
    subject: str
    operation: ClaimOperation
    dataset: str
    field: str
    operator: ClaimOperator
    threshold: Optional[ThresholdValue] = None
    time_scope: Optional[TimeScope] = None
    currency: Optional[str] = None
    transaction_status: Optional[str] = None
    period: Optional[str] = None
    period_value: Optional[int] = None
    merchant_scope: Optional[str] = None
    source_text: str
    confidence: float = Field(ge=0.0, le=1.0)
    ambiguities: List[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_semantics(self) -> "ClaimResult":
        # Deterministic constraint: if operator is not MATCH/EXISTS, it must have a threshold.
        if self.operation not in [ClaimOperation.MATCH, ClaimOperation.EXISTS]:
            if not self.threshold or self.threshold.value is None:
                if not self.ambiguities:
                    # Semantic validation failure if not gracefully flagged as ambiguous
                    raise ValueError(f"Operation {self.operation.value} requires a numeric threshold unless marked ambiguous.")
                    
        # Deterministic limitation on currency normalization mappings:
        # LLM must not invent currencies not presented. However, we'll let the application capability service fail it gracefully. 
        # But if it specifies a unit, it must not be "PAISA" or similar pre-computed scaling.
        if self.threshold and self.threshold.unit:
            if str(self.threshold.unit).upper() in ["PAISA", "CENTS", "PENCE"]:
                raise ValueError("Model MUST NOT output scaled units like PAISA. Semantic units (INR, USD) must be preserved.")
        return self

class EvidenceSourceSupport(BaseModel):
    type: str
    supports: List[str]
    trust_level: str

class EvidencePlanResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    evidence_sources: List[EvidenceSourceSupport]

class PrivacyStrategyResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    claim_id: str
    strategy: PrivacyStrategyType
    reason: str
    why_not_alternatives: Dict[str, str] = Field(default_factory=dict)
    privacy_gain: str
    zk_feasible: bool = Field(default=False, description="Theoretical ZK feasibility.")
    
class CapabilityResult(BaseModel):
    """Output of deterministic capability service mapping."""
    claim_id: str
    zk_feasible: bool
    circuit_available: bool
    circuit_id: Optional[str] = None
    circuit_version: Optional[str] = None
    recommended_strategy: PrivacyStrategyType
    
class CriticResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    approved: bool
    issues: List[str]
    warnings: List[str]

# --- UNIFIED AI PLANNER SCHEMAS ---

class UnifiedIntent(BaseModel):
    request: str
    ambiguities: List[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)

class SinglePredicate(BaseModel):
    aggregation: str
    field: str
    comparison: str
    threshold: float
    unit: Optional[str] = None
    filter: Optional[str] = None
    currency: Optional[str] = None
    transaction_status: Optional[str] = None
    period: Optional[str] = None
    period_value: Optional[int] = None
    merchant_scope: Optional[str] = None

class UnifiedClaim(BaseModel):
    type: str = Field(default="SINGLE", description="SINGLE or COMPOSITE")
    operator: Optional[str] = Field(default=None, description="Logical operator for COMPOSITE (AND/OR) or comparison for SINGLE (>, <, ==)")
    predicates: Optional[List[SinglePredicate]] = Field(default_factory=list)
    
    # SINGLE fallback fields
    operation: Optional[ClaimOperation] = None
    field: Optional[str] = None
    threshold: Optional[ThresholdValue] = None
    currency: Optional[str] = None
    transaction_status: Optional[str] = None
    period: Optional[str] = None
    period_value: Optional[int] = None
    merchant_scope: Optional[str] = None

class UnifiedEvidenceRequirement(BaseModel):
    type: str = Field(description="e.g. TRANSACTION_LEDGER, IDENTITY_CREDENTIAL")
    required_fields: List[str]
    provenance_required: bool

class UnifiedPrivacyObjective(BaseModel):
    hide: List[str]

class UnifiedProofStrategy(BaseModel):
    preferred: PrivacyStrategyType
    fallback: PrivacyStrategyType

class PlannerResult(BaseModel):
    """The outcome of the unified AI Planner."""
    model_config = ConfigDict(extra="forbid")
    
    intent: UnifiedIntent
    claim: UnifiedClaim
    evidence_requirements: List[UnifiedEvidenceRequirement]
    privacy_objective: UnifiedPrivacyObjective
    proof_strategy: UnifiedProofStrategy

