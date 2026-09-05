"""
ProofBridge — Pydantic Schemas

Strict schemas for all data structures.
All LLM output is validated through these schemas.
"""

from __future__ import annotations
from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


# ─── Enums ───────────────────────────────────────────────

class ClaimOperation(str, Enum):
    SUM = "SUM"
    AVERAGE = "AVERAGE"
    COUNT = "COUNT"
    AGE = "AGE"
    MATCH = "MATCH"
    EXISTS = "EXISTS"


class ClaimOperator(str, Enum):
    GT = ">"
    GTE = ">="
    LT = "<"
    LTE = "<="
    EQ = "=="
    NEQ = "!="


class PrivacyStrategyType(str, Enum):
    ZERO_KNOWLEDGE = "ZERO_KNOWLEDGE"
    SELECTIVE_DISCLOSURE = "SELECTIVE_DISCLOSURE"
    REDACTION = "REDACTION"
    VERIFIABLE_CREDENTIAL = "VERIFIABLE_CREDENTIAL"
    HUMAN_REVIEW = "HUMAN_REVIEW"
    UNSUPPORTED = "UNSUPPORTED"


class TrustLevel(str, Enum):
    GOVERNMENT_ATTESTED = "GOVERNMENT_ATTESTED"
    BANK_ATTESTED = "BANK_ATTESTED"
    PROCESSOR_ATTESTED = "PROCESSOR_ATTESTED"
    SIGNED_CREDENTIAL = "SIGNED_CREDENTIAL"
    VERIFIED_CREDENTIAL = "VERIFIED_CREDENTIAL"
    AI_EXTRACTED = "AI_EXTRACTED"
    MERCHANT_UPLOADED = "MERCHANT_UPLOADED"
    USER_ENTERED = "USER_ENTERED"
    UNKNOWN = "UNKNOWN"


class ProofStatus(str, Enum):
    PROOF_NOT_STARTED = "PROOF_NOT_STARTED"
    PROOF_GENERATED = "PROOF_GENERATED"
    PROOF_VERIFIED = "PROOF_VERIFIED"
    PROOF_INVALID = "PROOF_INVALID"
    PROOF_GENERATION_FAILED = "PROOF_GENERATION_FAILED"
    PROOF_VERIFICATION_FAILED = "PROOF_VERIFICATION_FAILED"
    PROOF_UNSUPPORTED = "PROOF_UNSUPPORTED"
    PROOF_INPUT_INVALID = "PROOF_INPUT_INVALID"


class VerificationStatus(str, Enum):
    PENDING = "PENDING"
    ANALYZING = "ANALYZING"
    CLAIMS_EXTRACTED = "CLAIMS_EXTRACTED"
    EVIDENCE_MAPPED = "EVIDENCE_MAPPED"
    STRATEGY_SELECTED = "STRATEGY_SELECTED"
    PROOF_SPEC_GENERATED = "PROOF_SPEC_GENERATED"
    PROVING = "PROVING"
    VERIFIED = "VERIFIED"
    FAILED = "FAILED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    REFUSED = "REFUSED"


class AuditEventType(str, Enum):
    REQUEST_RECEIVED = "REQUEST_RECEIVED"
    CLAIMS_EXTRACTED = "CLAIMS_EXTRACTED"
    EVIDENCE_MAPPED = "EVIDENCE_MAPPED"
    PRIVACY_STRATEGY_SELECTED = "PRIVACY_STRATEGY_SELECTED"
    PROOF_SPEC_GENERATED = "PROOF_SPEC_GENERATED"
    PROOF_SPEC_VALIDATED = "PROOF_SPEC_VALIDATED"
    CIRCUIT_SELECTED = "CIRCUIT_SELECTED"
    PROOF_GENERATED = "PROOF_GENERATED"
    PROOF_VERIFIED = "PROOF_VERIFIED"
    VERIFICATION_RETURNED = "VERIFICATION_RETURNED"
    ERROR = "ERROR"


class CircuitStatus(str, Enum):
    ACTIVE = "ACTIVE"
    PLANNED = "PLANNED"
    DEPRECATED = "DEPRECATED"
    DISABLED = "DISABLED"


# ─── Core Schemas ────────────────────────────────────────

class Attestation(BaseModel):
    """A deterministic cryptographically bound provenance."""
    model_config = ConfigDict(extra="forbid")
    
    issuer: str
    dataset_id: str
    dataset_hash: str
    issued_at: str
    valid_from: Optional[str] = None
    valid_to: Optional[str] = None
    signature: str
    public_key: str
    key_id: str
    algorithm: str

class Claim(BaseModel):
    """An extracted verification claim with full provenance."""
    model_config = ConfigDict(extra="forbid")

    id: str = Field(description="Unique claim identifier, e.g. C001")
    description: str = Field(description="Human-readable claim description")
    source_text: str = Field(description="Exact text from the request that produced this claim")
    operation: ClaimOperation
    field: str = Field(description="Data field the operation applies to, e.g. 'transactions.amount'")
    operator: ClaimOperator
    threshold: Optional[float] = Field(default=None, description="Numeric threshold. None if ambiguous.")
    unit: Optional[str] = Field(default=None, description="Unit of the threshold, e.g. 'INR', 'years'")
    confidence: float = Field(ge=0.0, le=1.0, description="AI extraction confidence (NOT cryptographic assurance)")
    ambiguity: Optional[str] = Field(default=None, description="Description of any ambiguity detected")
    is_supported: bool = Field(default=True, description="Whether this claim can be proven with available circuits")
    currency: Optional[str] = None
    transaction_status: Optional[str] = None
    period: Optional[str] = None
    period_value: Optional[int] = None
    merchant_scope: Optional[str] = None


class EvidenceField(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    type: str
    relevant: bool = Field(description="Whether this field is needed for the claim")
    sensitivity: str = Field(default="normal", description="low/normal/high/critical")


class EvidenceSource(BaseModel):
    """Available evidence source with provenance metadata."""
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    source_type: TrustLevel
    issuer: str
    format: str = Field(description="e.g. JSON, PDF, CSV")
    fields: list[EvidenceField]
    attestation_status: str = Field(default="synthetic-demo")
    content_hash: Optional[str] = Field(default=None, description="SHA-256 of canonical content")
    note: Optional[str] = None


class EvidenceMapping(BaseModel):
    """Maps a claim to supporting evidence."""
    model_config = ConfigDict(extra="forbid")

    claim_id: str
    evidence_id: str
    relevant_fields: list[str]
    irrelevant_fields: list[str] = Field(default_factory=list)
    support_type: str = Field(description="DIRECT_SUPPORT, PARTIAL_SUPPORT, INDIRECT")
    explanation: str = Field(description="Why this evidence supports the claim")
    trust_sufficient: bool


class PrivacyStrategy(BaseModel):
    """Selected privacy-preserving strategy."""
    model_config = ConfigDict(extra="forbid")

    claim_id: str
    strategy: PrivacyStrategyType
    reason: str = Field(description="Why this strategy was selected")
    why_not_alternatives: dict[str, str] = Field(
        default_factory=dict,
        description="Why alternative strategies were not selected"
    )
    privacy_gain: str = Field(description="What information remains private")
    feasibility_score: float = Field(ge=0.0, le=1.0)
    feasibility_breakdown: dict[str, bool] = Field(default_factory=dict)


class ProofStatement(BaseModel):
    model_config = ConfigDict(extra="forbid")

    operation: ClaimOperation
    field: str
    operator: ClaimOperator
    threshold: float
    source_unit: Optional[str] = Field(default=None, description="e.g. INR, years")
    circuit_scaled_value: Optional[int] = Field(default=None, description="Deterministic backend scaled value for circuit (e.g. paisa)")
    currency: Optional[str] = None
    transaction_status: Optional[str] = None
    period: Optional[str] = None
    period_value: Optional[int] = None
    merchant_scope: Optional[str] = None


class ProofSpecification(BaseModel):
    """Structured proof specification — intermediate representation, NOT executable code."""
    model_config = ConfigDict(extra="forbid")

    proof_id: str
    claim_id: str
    method: PrivacyStrategyType
    circuit: Optional[str] = Field(default=None, description="Circuit ID from registry")
    circuit_version: Optional[str] = None
    statement: ProofStatement
    private_inputs: list[str]
    public_inputs: list[str]
    public_outputs: list[str]
    evidence_source: str
    evidence_commitment: Optional[str] = Field(default=None, description="Poseidon hash of evidence data")
    request_nonce: Optional[str] = Field(default=None, description="Cryptographically random session nonce")


class ProofArtifact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    proof_json: dict
    public_signals: list[str]
    proving_time_ms: int
    circuit: str
    proving_system: str = "groth16"
    curve: str = "bn128"


class VerificationResult(BaseModel):
    """Final verification result — privacy-preserving output for the processor."""
    model_config = ConfigDict(extra="forbid")

    request_id: str
    claim_id: str
    claim_description: str
    status: ProofStatus
    proof_id: Optional[str] = None
    circuit: Optional[str] = None
    circuit_version: Optional[str] = None
    proving_system: Optional[str] = None
    evidence_commitment: Optional[str] = None
    evidence_provenance: Optional[str] = None
    verification_time_ms: Optional[int] = None
    timestamp: str
    data_disclosed: dict[str, int] = Field(
        default_factory=lambda: {
            "transaction_amounts": 0,
            "customer_identities": 0,
            "raw_records": 0
        }
    )
    privacy_strategy: PrivacyStrategyType
    evidence_authentication: Optional[dict] = Field(default=None, description="Detailed authentication info")
    semantic_validation: Optional[dict] = Field(default=None, description="Detailed filtering stats")
    # NEVER include private witness data here


class AuditEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    timestamp: str
    request_id: str
    event_type: AuditEventType
    actor: str = Field(description="system, ai, user, verifier")
    metadata: dict = Field(default_factory=dict)
    # MUST NOT store private witness data


# ─── API Request/Response Schemas ────────────────────────

class VerificationRequestCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_text: str = Field(min_length=10, max_length=2000)
    evidence_ids: list[str] = Field(default_factory=list)
    nonce: Optional[str] = Field(default=None, description="Server-generated nonce")


class VerificationRequestResponse(BaseModel):
    id: str
    request_text: str
    status: VerificationStatus
    claims: list[Claim] = Field(default_factory=list)
    evidence_mappings: list[EvidenceMapping] = Field(default_factory=list)
    privacy_strategies: list[PrivacyStrategy] = Field(default_factory=list)
    proof_specifications: list[ProofSpecification] = Field(default_factory=list)
    verification_results: list[VerificationResult] = Field(default_factory=list)
    audit_trail: list[AuditEvent] = Field(default_factory=list)
    created_at: str
    updated_at: str
    ai: dict = Field(default_factory=dict)


class AnalysisResponse(BaseModel):
    request_id: str
    claims: list[Claim]
    evidence_mappings: list[EvidenceMapping]
    privacy_strategies: list[PrivacyStrategy]
    proof_specifications: list[ProofSpecification]
    pipeline_duration_ms: int
    ai: dict = Field(default_factory=dict)


class ProofGenerationResponse(BaseModel):
    request_id: str
    proof_id: str
    status: ProofStatus
    circuit: Optional[str] = None
    proving_time_ms: Optional[int] = None
    evidence_commitment: Optional[str] = None


class ProofVerificationResponse(BaseModel):
    request_id: str
    verification_result: VerificationResult


class CircuitInfo(BaseModel):
    id: str
    version: str
    status: CircuitStatus
    description: str
    predicate: str
    operation: str
    operator: str
    max_inputs: Optional[int] = None
    constraints: Optional[dict] = None


class DemoScenario(BaseModel):
    id: str
    title: str
    description: str
    request_text: str
    expected_strategy: PrivacyStrategyType
    expected_operation: Optional[ClaimOperation] = None
