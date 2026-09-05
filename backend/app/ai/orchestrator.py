"""
ProofBridge — AI Pipeline Orchestrator

Sequences discrete AI roles via unified AIPlanner, handles capability validation, 
and compiles deterministic ZK specs.
"""
import time
import logging
import uuid
from typing import Dict, Any, List

from app.config import AI_MODE
from app.ai.factory import AIFactory
from app.schemas.ai_models import CapabilityResult
from app.services.capability_service import CapabilityService
from app.services.circuit_registry import CircuitRegistryService
from app.services.evidence import EvidenceService
from app.schemas.models import (
    Claim, EvidenceMapping, PrivacyStrategy, ProofSpecification, ProofStatement,
    PrivacyStrategyType, ClaimOperation, ClaimOperator
)
from app.schemas.ai_models import PlannerResult

logger = logging.getLogger(__name__)

class PipelineOrchestrator:
    def __init__(self, capability_service: CapabilityService, circuit_registry: CircuitRegistryService, evidence_service: EvidenceService):
        self.capability_service = capability_service
        self.circuit_registry = circuit_registry
        self.evidence_service = evidence_service

    async def analyze(self, request_text: str, evidence_ids: list[str]) -> dict:
        start = time.time()
        
        mode = AI_MODE
        ai_metadata = {
            "mode": mode,
            "models": [],
            "ensemble": mode == "ensemble",
            "conflict": False
        }

        # 1. Ensemble Compare
        primary_plan: PlannerResult = None
        
        if mode == "ensemble":
            logger.info("Running ENSEMBLE mode independent interpretation...")
            try:
                gemini_planner = AIFactory.get_planner("gemini")
                os_planner = AIFactory.get_planner("open_source")
                
                g_plan = await gemini_planner.plan(request_text)
                o_plan = await os_planner.plan(request_text)
                
                g_op = getattr(g_plan.claim, "operation", "")
                o_op = getattr(o_plan.claim, "operation", "")
                g_thresh = getattr(g_plan.claim.threshold, "value", None) if g_plan.claim.threshold else None
                o_thresh = getattr(o_plan.claim.threshold, "value", None) if o_plan.claim.threshold else None
                
                if g_op != o_op or g_thresh != o_thresh:
                    ai_metadata["conflict"] = True
                    ai_metadata["conflict_reason"] = f"Gemini: {g_op} {g_thresh} vs OS: {o_op} {o_thresh}"
                    primary_plan = g_plan
                else:
                    primary_plan = g_plan
                
                ai_metadata["models"].append({"role": "PLANNER", "provider": "gemini", "model": gemini_planner.provider.model_name()})
                ai_metadata["models"].append({"role": "PLANNER", "provider": "open_source", "model": os_planner.provider.model_name()})
                
            except Exception as e:
                logger.error(f"Ensemble failed: {e}")
                raise Exception("OPEN_SOURCE_MODEL_UNAVAILABLE" if "OPEN_SOURCE" in str(e) else str(e))
        else:
            try:
                planner = AIFactory.get_planner(mode)
                ai_metadata["models"].append({"role": "PLANNER", "provider": planner.provider.provider_name(), "model": planner.provider.model_name()})
                primary_plan = await planner.plan(request_text)
            except Exception as e:
                logger.error(f"Planner failed: {e}")
                return self._empty_result(start, ai_metadata, f"Error: {str(e)}")

        if ai_metadata.get("conflict"):
            return self._empty_result(start, ai_metadata, "AI_INTERPRETATION_CONFLICT")

        try:
            # Deterministic Gate: Capability Service
            claim_id = f"clm_{uuid.uuid4().hex[:8]}"
            is_composite = getattr(primary_plan.claim, "type", "SINGLE") == "COMPOSITE"
            
            if is_composite:
                logger.warning("COMPOSITE claim detected. Enforcing anti-downgrade rule: failing closed as UNSUPPORTED_CLAIM.")
                capability = CapabilityResult(
                    claim_id=claim_id,
                    zk_feasible=False,
                    circuit_available=False,
                    recommended_strategy=PrivacyStrategyType.UNSUPPORTED
                )
            else:
                capability = self.capability_service.assess_capability(
                    claim_id, 
                    primary_plan.claim.operation, 
                    primary_plan.claim.operator
                )

            # Check if LLM broke capability constraint
            strat = primary_plan.proof_strategy.preferred
            reason = "Planner successfully matched capability"
            
            if strat == PrivacyStrategyType.ZERO_KNOWLEDGE and not capability.circuit_available:
                logger.warning("PrivacyModel hallucinatory override: Forced ZK without active circuit. Overriding to capability recommendation.")
                strat = capability.recommended_strategy
                reason = "Deterministic safeguard: No active circuit exists for this predicate."

            # Map generated evidence requirements to what actually was uploaded/available
            final_mapped_evidences = []
            if evidence_ids:
                for eid in evidence_ids:
                    src = self.evidence_service.get_source(eid)
                    if src:
                        final_mapped_evidences.append(src)
                        
            if is_composite:
                desc = f"COMPOSITE PREDICATE (Anti-Downgrade Enforced)"
                op = ClaimOperation.MATCH # safe placeholder
                fld = "MULTIPLE_FIELDS"
                oper = ClaimOperator.EQ
                thresh = None
                unt = None
            else:
                desc = f"{primary_plan.claim.operation.value} on {primary_plan.claim.field} {primary_plan.claim.operator} {primary_plan.claim.threshold.value if primary_plan.claim.threshold else 'none'}"
                op = primary_plan.claim.operation
                fld = primary_plan.claim.field
                oper = primary_plan.claim.operator
                thresh = primary_plan.claim.threshold.value if primary_plan.claim.threshold else None
                unt = primary_plan.claim.threshold.unit if primary_plan.claim.threshold else None

            out_claims = [Claim(
                id=claim_id,
                description=desc,
                source_text=primary_plan.intent.request,
                operation=op,
                field=fld,
                operator=oper,
                threshold=thresh,
                unit=unt,
                confidence=primary_plan.intent.confidence,
                ambiguity=", ".join(primary_plan.intent.ambiguities) if primary_plan.intent.ambiguities else None,
                is_supported=capability.circuit_available,
                currency=primary_plan.claim.currency,
                transaction_status=primary_plan.claim.transaction_status,
                period=primary_plan.claim.period,
                period_value=primary_plan.claim.period_value,
                merchant_scope=primary_plan.claim.merchant_scope
            )]

            out_evidences = []
            if final_mapped_evidences:
                actual_src = final_mapped_evidences[0]
                out_evidences.append(EvidenceMapping(
                    claim_id=claim_id,
                    evidence_id=actual_src.id,
                    relevant_fields=primary_plan.evidence_requirements[0].required_fields if primary_plan.evidence_requirements else [],
                    support_type="DIRECT_SUPPORT",
                    explanation=f"Planner mapped: {actual_src.name}",
                    trust_sufficient=True
                ))

            out_strategies = [PrivacyStrategy(
                claim_id=claim_id,
                strategy=strat,
                reason=reason,
                why_not_alternatives={},
                privacy_gain="Minimizes explicit values",
                feasibility_score=0.9,
                feasibility_breakdown={
                    "zk_feasible_math": capability.zk_feasible,
                    "circuit_available": capability.circuit_available
                }
            )]

            out_specs = []
            if strat == PrivacyStrategyType.ZERO_KNOWLEDGE and capability.circuit_available:
                raw_val = primary_plan.claim.threshold.value
                unit = primary_plan.claim.threshold.unit
                c_val = int(raw_val) if raw_val is not None else 0
                if unit and unit.upper() == "INR":
                    c_val = int(raw_val * 100)
                    
                spec = ProofSpecification(
                    proof_id=f"P_{claim_id}",
                    claim_id=claim_id,
                    method=PrivacyStrategyType.ZERO_KNOWLEDGE,
                    circuit=capability.circuit_id,
                    circuit_version=capability.circuit_version,
                    statement=ProofStatement(
                        operation=primary_plan.claim.operation,
                        field=primary_plan.claim.field,
                        operator=primary_plan.claim.operator,
                        threshold=raw_val,
                        source_unit=unit,
                        circuit_scaled_value=c_val,
                        currency=primary_plan.claim.currency,
                        transaction_status=primary_plan.claim.transaction_status,
                        period=primary_plan.claim.period,
                        period_value=primary_plan.claim.period_value,
                        merchant_scope=primary_plan.claim.merchant_scope
                    ),
                    private_inputs=[primary_plan.claim.field],
                    public_inputs=["threshold", "request_nonce", "dataset_commitment"],
                    public_outputs=["claimResult"],
                    evidence_source=out_evidences[0].evidence_id if out_evidences else ""
                )
                out_specs.append(spec)

            return {
                "claims": out_claims,
                "evidence_mappings": out_evidences,
                "privacy_strategies": out_strategies,
                "proof_specifications": out_specs,
                "pipeline_duration_ms": int((time.time() - start) * 1000),
                "ai": ai_metadata
            }

        except Exception as e:
            logger.error(f"Deterministic execution error: {e}")
            return self._empty_result(start, ai_metadata, f"Error: {str(e)}")

    def _empty_result(self, start: float, ai_metadata: dict, error_msg: str):
        ai_metadata["error"] = error_msg
        return {
            "claims": [],
            "evidence_mappings": [],
            "privacy_strategies": [],
            "proof_specifications": [],
            "pipeline_duration_ms": int((time.time() - start) * 1000),
            "ai": ai_metadata
        }
