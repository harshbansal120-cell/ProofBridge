"""
ProofBridge — Deterministic Capability Service

Maps a structured Claim to system capabilities (ZK feasibility, circuit availability).
Decouples LLM-assumed capabilities from factual reality.
"""
from typing import Optional
from app.schemas.models import ClaimOperation, ClaimOperator, PrivacyStrategyType
from app.schemas.ai_models import CapabilityResult
from app.services.circuit_registry import CircuitRegistryService

class CapabilityService:
    def __init__(self, circuit_registry: CircuitRegistryService):
        self.circuit_registry = circuit_registry
        
    def assess_capability(self, claim_id: str, operation: ClaimOperation, operator: ClaimOperator) -> CapabilityResult:
        """
        Assess if the operation is theoretically ZK feasible and if an active circuit exists.
        """
        # 1. Theoretical ZK feasibility
        # Numerical comparisons/aggregations are typically ZK feasible.
        zk_feasible_operations = [
            ClaimOperation.SUM,
            ClaimOperation.AVERAGE,
            ClaimOperation.COUNT,
            ClaimOperation.AGE
        ]
        
        is_zk_feasible = operation in zk_feasible_operations
        
        # 2. Extract active circuit
        circuit = self.circuit_registry.resolve_circuit_for_claim(operation, operator)
        is_circuit_active = (circuit is not None)
        
        # 3. Determine recommended fallback constraint
        if is_circuit_active:
            strategy = PrivacyStrategyType.ZERO_KNOWLEDGE
        elif is_zk_feasible:
            # We don't have the circuit yet, but it's numerical. 
            # Could be SELECTIVE_DISCLOSURE or HUMAN_REVIEW depending on evidence length. By default:
            strategy = PrivacyStrategyType.SELECTIVE_DISCLOSURE
        else:
            # e.g., MATCH, EXISTS, subjective explanation
            strategy = PrivacyStrategyType.HUMAN_REVIEW
            
        return CapabilityResult(
            claim_id=claim_id,
            zk_feasible=is_zk_feasible,
            circuit_available=is_circuit_active,
            circuit_id=circuit["id"] if is_circuit_active else None,
            circuit_version=circuit["version"] if is_circuit_active else None,
            recommended_strategy=strategy
        )
