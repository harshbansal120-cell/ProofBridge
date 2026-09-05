"""
ProofBridge — Deterministic Demo Provider
"""
import json
import logging
from app.ai.interfaces import LLMProvider

logger = logging.getLogger(__name__)

class DemoProvider(LLMProvider):
    """
    Deterministic demo provider — returns pre-computed JSON.
    Used exclusively as an offline test fixture.
    """

    async def generate_json(self, system_prompt: str, user_prompt: str) -> dict:
        lower = user_prompt.lower()
        role_hint = system_prompt.lower()
        
        # 1. Intent Model
        if "extract intent" in role_hint or "extract a formal intent" in role_hint:
            if "average" in lower or "avg" in lower:
                return {
                    "request_type": "FINANCIAL_THRESHOLD_VERIFICATION",
                    "subject": "merchant",
                    "metric": "average_order_value",
                    "period": {"type": "QUARTER", "scope": "PREVIOUS_QUARTER"},
                    "operator": "LESS_THAN",
                    "threshold": {"value": 50000, "unit": "INR", "source": "USER_REQUEST"},
                    "confidence": 0.95,
                    "ambiguities": []
                }
            elif "age" in lower or "registered" in lower:
                return {
                    "request_type": "IDENTITY_VERIFICATION",
                    "subject": "business",
                    "metric": "registration_age",
                    "period": None,
                    "operator": "GREATER_THAN",
                    "threshold": {"value": 1, "unit": "years", "source": "USER_REQUEST"},
                    "confidence": 0.93,
                    "ambiguities": []
                }
            elif "refund" in lower or "explain" in lower:
                return {
                    "request_type": "EXPLANATION",
                    "subject": "merchant",
                    "metric": "refund_activity",
                    "period": {"type": "MONTH", "scope": "LAST"},
                    "operator": "MATCH",
                    "threshold": None,
                    "confidence": 0.88,
                    "ambiguities": ["Request asks for explanation, which requires human inspection."]
                }
            # Default to SUM
            return {
                "request_type": "FINANCIAL_THRESHOLD_VERIFICATION",
                "subject": "merchant",
                "metric": "processing_volume",
                "period": {"type": "MONTH", "scope": "PREVIOUS_QUARTER"},
                "operator": "GREATER_THAN",
                "threshold": {"value": 1000000, "unit": "INR", "source": "USER_REQUEST"},
                "confidence": 0.96,
                "ambiguities": [],
                "currency": "INR",
                "transaction_status": "SUCCESS",
                "period": "LAST_N_MONTHS",
                "period_value": 6,
                "merchant_scope": "MERCHANT-42"
            }
            
        # 2. Claim Model
        elif "claim dsl" in role_hint or "compile claim" in role_hint:
            if "average_order_value" in lower:
                return {
                    "claim_id": "C_DEMO_01",
                    "subject": "merchant",
                    "operation": "AVERAGE",
                    "dataset": "transactions",
                    "field": "amount",
                    "operator": "<",
                    "threshold": {"value": 50000, "unit": "INR", "source": "USER_REQUEST"},
                    "time_scope": {"type": "QUARTER", "scope": "PREVIOUS_QUARTER"},
                    "source_text": user_prompt[:100],
                    "confidence": 0.99,
                    "ambiguities": []
                }
            elif "registration_age" in lower:
                return {
                    "claim_id": "C_DEMO_01",
                    "subject": "business",
                    "operation": "AGE",
                    "dataset": "identity",
                    "field": "registration_date",
                    "operator": ">",
                    "threshold": {"value": 1, "unit": "years", "source": "USER_REQUEST"},
                    "time_scope": None,
                    "source_text": user_prompt[:100],
                    "confidence": 0.99,
                    "ambiguities": []
                }
            elif "refund" in lower or "match" in lower:
                return {
                    "claim_id": "C_DEMO_01",
                    "subject": "merchant",
                    "operation": "MATCH",
                    "dataset": "transactions",
                    "field": "refunds",
                    "operator": "==",
                    "threshold": None,
                    "time_scope": None,
                    "source_text": user_prompt[:100],
                    "confidence": 0.99,
                    "ambiguities": []
                }
            # Default to SUM
            return {
                "claim_id": "C001",
                "subject": "merchant",
                "operation": "SUM",
                "dataset": "transactions",
                "field": "amount",
                "operator": ">",
                "threshold": {"value": 1000000, "unit": "INR", "source_text": "10 lakh", "source": "USER_REQUEST"},
                "time_scope": {"type": "MONTH", "scope": "PREVIOUS_QUARTER"},
                "source_text": user_prompt[:100],
                "confidence": 0.98,
                "ambiguities": [],
                "currency": "INR",
                "transaction_status": "SUCCESS",
                "period": "LAST_N_MONTHS",
                "period_value": 6,
                "merchant_scope": "MERCHANT-42"
            }

        # 3. Evidence Model
        elif "evidence map" in role_hint:
            if "age" in lower or "registration_date" in lower:
                return {
                    "evidence_sources": [{
                        "type": "VERIFIED_CREDENTIAL",
                        "supports": ["business.registration_date"],
                        "trust_level": "GOVERNMENT_ATTESTED"
                    }]
                }
            return {
                "evidence_sources": [{
                    "type": "PROCESSOR_ATTESTED_LEDGER",
                    "supports": ["transactions.amount", "transactions.timestamp"],
                    "trust_level": "PROCESSOR_ATTESTED"
                }]
            }
            
        # 4. Privacy Model
        elif "privacy strateg" in role_hint:
            if "average" in lower:
                return {
                    "claim_id": "C_DEMO_01",
                    "strategy": "ZERO_KNOWLEDGE",
                    "reason": "Average can theoretically be proven using zero-knowledge circuits.",
                    "why_not_alternatives": {},
                    "privacy_gain": "Individual values are not disclosed.",
                    "zk_feasible": True
                }
            if "age" in lower:
                return {
                    "claim_id": "C_DEMO_01",
                    "strategy": "VERIFIABLE_CREDENTIAL",
                    "reason": "Age is best proven by cryptographic credential disclosure.",
                    "why_not_alternatives": {},
                    "privacy_gain": "Exact identity details other than age can be redacted.",
                    "zk_feasible": False
                }
            if "match" in lower or "explain" in lower:
                return {
                    "claim_id": "C_DEMO_01",
                    "strategy": "HUMAN_REVIEW",
                    "reason": "Contextual explanation cannot be formulated as a predicate.",
                    "why_not_alternatives": {},
                    "privacy_gain": "N/A",
                    "zk_feasible": False
                }
            # Default to SUM
            return {
                "claim_id": "C_DEMO_01",
                "strategy": "ZERO_KNOWLEDGE",
                "reason": "Requested threshold is mathematical over a financial aggregate.",
                "why_not_alternatives": {"SELECTIVE_DISCLOSURE": "Not necessary."},
                "privacy_gain": "Transactions hidden.",
                "zk_feasible": True
            }
            
        # 5. Critic Model
        elif "evaluate plan" in role_hint or "critic" in role_hint:
            return {
                "approved": True,
                "issues": [],
                "warnings": []
            }
            
        return {}

    def provider_name(self) -> str:
        return "DEMO_DETERMINISTIC"

    def model_name(self) -> str:
        return "fixture-v1"
