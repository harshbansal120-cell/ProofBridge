"""
ProofBridge — AI Model Pipeline Evaluation Script

Evaluates the modular models on structural validity, threshold integrity, unit preservation,
and robustness against adversarial prompt attacks.
"""
import asyncio
import json
import logging
from pathlib import Path

from app.config import ROOT_DIR
from app.ai.factory import AIFactory
from app.schemas.ai_models import IntentResult, ClaimResult, PrivacyStrategyResult

logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

async def run_evaluation():
    try:
        from app.config import AI_MODE
        if AI_MODE != "open_source" and AI_MODE != "gemini":
            logger.warning(f"AI_MODE is {AI_MODE}. Running evaluation with Demo Provider may be trivially 100%.")

        intent_model = AIFactory.get_intent_model()
        claim_model = AIFactory.get_claim_model()
        
        datasets_path = ROOT_DIR / "tests" / "fixtures" / "proofbridge_eval_dataset.json"
        with open(datasets_path, "r") as f:
            cases = json.load(f)
            
        total = len(cases)
        results = {
            "json_validity": 0,
            "operation_accuracy": 0,
            "operator_accuracy": 0,
            "threshold_accuracy": 0,
            "unit_accuracy": 0,
            "ambiguity_detection": 0,
            "hallucinated_thresholds": 0,
            "adversarial_resilience": 0
        }
        
        logger.info(f"Starting Evaluation on {total} cases using Provider: {intent_model.provider.provider_name()} / {intent_model.provider.model_name()}")
        
        for case in cases:
            logger.info(f"Evaluating: {case['id']} - {case['request']}")
            try:
                intent: IntentResult = await intent_model.extract_intent(case["request"])
                claim: ClaimResult = await claim_model.compile_claim(intent)
                
                results["json_validity"] += 1
                
                # Metrics
                if claim.operation.value == case["expected_claim"]["operation"]:
                    results["operation_accuracy"] += 1
                    
                if claim.operator.value == case["expected_claim"]["operator"]:
                    results["operator_accuracy"] += 1
                    
                thresh_val = claim.threshold.value if claim.threshold else None
                if thresh_val == case["expected_claim"]["threshold"]:
                    results["threshold_accuracy"] += 1
                else:
                    if case["expected_claim"]["threshold"] is None and thresh_val is not None:
                        results["hallucinated_thresholds"] += 1
                        
                thresh_unit = claim.threshold.unit if claim.threshold else None
                if thresh_unit == case["expected_claim"]["unit"]:
                    results["unit_accuracy"] += 1
                    
            except Exception as e:
                # If adversarial or unparsable
                if "Prompt injection test" in case.get("notes", "") or "Bypass" in case.get("request", ""):
                    results["adversarial_resilience"] += 1
                    logger.info(f"Successfully defended adversarial attempt via exception or capability bounding.")
                elif "Ambiguous" in case.get("notes", ""):
                    results["ambiguity_detection"] += 1
                else:
                    logger.error(f"Failed case {case['id']}: {e}")
                    
        # Semantic Equivalence Tests
        logger.info("\n--- SEMANTIC EQUIVALENCE TESTS ---")
        paraphrases = [
            "Show that our monthly payment volume was above ₹10L.",
            "Verify that we processed more than ten lakh rupees per month.",
            "Demonstrate monthly GMV exceeding INR 1,000,000.",
            "The processor needs confirmation that monthly volume crossed ₹10 lakh.",
            "Can you prove our monthly processing value was greater than ₹1M?"
        ]
        opposite = "Prove monthly volume was below ₹10 lakh."
        
        base_claim = None
        for i, phrase in enumerate(paraphrases):
            try:
                intent: IntentResult = await intent_model.extract_intent(phrase)
                claim: ClaimResult = await claim_model.compile_claim(intent)
                
                if i == 0:
                    base_claim = claim
                    logger.info(f"Paraphrase 1 (Base): {claim.operation.value} {claim.operator.value} {claim.threshold.value if claim.threshold else None}")
                else:
                    match = (claim.operation == base_claim.operation and 
                             claim.operator == base_claim.operator and 
                             claim.threshold.value == base_claim.threshold.value)
                    logger.info(f"Paraphrase {i+1}: {'MATCHES BASE' if match else 'DEVIATES'} -> {claim.operation.value} {claim.operator.value} {claim.threshold.value if claim.threshold else None}")
            except Exception as e:
                logger.error(f"Semantic Paraphrase Test failed: {e}")
                
        try:
            opp_intent: IntentResult = await intent_model.extract_intent(opposite)
            opp_claim: ClaimResult = await claim_model.compile_claim(opp_intent)
            opp_match = (opp_claim.operation == base_claim.operation and 
                         opp_claim.operator == base_claim.operator and 
                         opp_claim.threshold.value == base_claim.threshold.value)
            logger.info(f"Opposite Statement: {'INCORRECTLY MATCHES BASE' if opp_match else 'CORRECTLY DEVIATES'} -> {opp_claim.operation.value} {opp_claim.operator.value} {opp_claim.threshold.value if opp_claim.threshold else None}")
            if hasattr(opp_claim, 'threshold') and opp_claim.threshold:
                 logger.info(f"Opposite statement parsed successfully.")
        except Exception as e:
            logger.error(f"Opposite Statement Test failed (caught as constraint violation or parser error?): {e}")

        # Output Metrics
        for key, value in results.items():
            if key == "hallucinated_thresholds":
                logger.info(f"{key}: {value} (Lower is better)")
            else:
                pct = (value / total) * 100
                logger.info(f"{key}: {value}/{total} ({pct:.1f}%)")
                
    except Exception as e:
        logger.error(f"Evaluation failed: {e}")

if __name__ == "__main__":
    asyncio.run(run_evaluation())
