import asyncio
import copy
import logging
import sys
import hashlib
from pathlib import Path
import json

backend_dir = str(Path(__file__).parent.parent / "backend")
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.services.zk_engine import ZKEngine
from app.services.circuit_registry import CircuitRegistryService
from app.schemas.models import ProofStatus, VerificationStatus, ProofSpecification, ProofStatement, PrivacyStrategyType
import app.main as main_mod

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

async def run_tests():
    zk = ZKEngine()
    registry = CircuitRegistryService()
    
    circuit_id = "sum_greater_than"
    version = "1.2.0"
    
    paths = registry.get_circuit_paths(circuit_id, version)
    if not paths:
        logger.error(f"Cannot find paths for {circuit_id} v{version}")
        sys.exit(1)

    logger.info("========================================")
    logger.info("PROOFBRIDGE CRYPTOGRAPHIC BOUNDARY TESTS")
    logger.info("========================================\n")
    logger.info("==================================================")
    logger.info("5. PROVE THE TEST IS USING THE PRODUCTION ARTIFACTS")
    logger.info("==================================================")
    logger.info(f"absolute WASM path: {paths['wasm']}")
    logger.info(f"absolute ZKEY path: {paths['zkey']}")
    logger.info(f"absolute verification key path: {paths['verification_key']}")

    for k, p in paths.items():
        if k in ["wasm", "zkey", "verification_key"]:
            ph = hashlib.sha256(Path(p).read_bytes()).hexdigest()
            logger.info(f"SHA-256 [{k}]: {ph}")

    req_nonce_a = "123456789123456789"
    req_nonce_b = "987654321987654321"

    def check(name, test_cond, expected="REJECT"):
        if test_cond:
            logger.info(f"[PASS] {name}")
        else:
            logger.error(f"[FAIL] {name}")
            sys.exit(1)

    try:
        # TEST A: STRICT GREATER THAN (Regression Test)
        logger.info("\n[Test A] STRICT EQUALITY (SUM == threshold)")
        amounts_eq = [62500] * 16
        threshold_eq = 1000000
        proof_eq = await zk.generate_proof(circuit_id, paths, amounts_eq, threshold_eq, req_nonce_a)
        check("SUM == threshold → actual proof generation FAIL", proof_eq["status"] == ProofStatus.PROOF_GENERATION_FAILED)

        # TEST B: GREATER THAN VALID
        logger.info("\n[Test B] GREATER THAN VALID (SUM > threshold)")
        amounts_valid = [62501] * 16
        proof_valid = await zk.generate_proof(circuit_id, paths, amounts_valid, threshold_eq, req_nonce_a)
        check("SUM > threshold → actual proof generation PASS", proof_valid["status"] == ProofStatus.PROOF_GENERATED)
        
        ver_valid = await zk.verify_proof(circuit_id, paths, proof_valid["proof"], proof_valid["public_signals"])
        check("SUM > threshold → actual verifier PASS", ver_valid["valid"], expected="ACCEPT")

        # TEST C: BELOW THRESHOLD
        logger.info("\n[Test C] BELOW THRESHOLD (SUM < threshold)")
        amounts_below = [62499] * 16
        proof_below = await zk.generate_proof(circuit_id, paths, amounts_below, threshold_eq, req_nonce_a)
        check("SUM < threshold → actual proof generation FAIL", proof_below["status"] == ProofStatus.PROOF_GENERATION_FAILED)

        # UINT64 OVERFLOW ATTACK
        logger.info("\n[Test E] UINT64 OVERFLOW ATTACK")
        overflow_uint64 = 1 << 64
        amounts_overflow = [overflow_uint64] + [0]*15
        proof_overflow = await zk.generate_proof(circuit_id, paths, amounts_overflow, threshold_eq, req_nonce_a)
        check("UINT64 overflow → FAIL", proof_overflow["status"] == ProofStatus.PROOF_GENERATION_FAILED)

        # ALTERED COMMITMENT
        logger.info("\n[Test H] ALTERED COMMITMENT")
        tampered_signals = copy.deepcopy(proof_valid["public_signals"])
        tampered_signals[2] = "999999999999999999999999" 
        ver_comm = await zk.verify_proof(circuit_id, paths, proof_valid["proof"], tampered_signals)
        check("altered commitment → verifier FAIL", not ver_comm["valid"])

        # ALTERED THRESHOLD
        logger.info("\n[Test I] ALTERED THRESHOLD")
        tampered_signals = copy.deepcopy(proof_valid["public_signals"])
        tampered_signals[1] = "500000" 
        ver_thresh = await zk.verify_proof(circuit_id, paths, proof_valid["proof"], tampered_signals)
        check("altered threshold → verifier FAIL", not ver_thresh["valid"])

        # ALTERED NONCE
        logger.info("\n[Test J] ALTERED NONCE")
        tampered_signals = copy.deepcopy(proof_valid["public_signals"])
        tampered_signals[3] = req_nonce_b
        ver_nonce = await zk.verify_proof(circuit_id, paths, proof_valid["proof"], tampered_signals)
        check("altered nonce → verifier FAIL", not ver_nonce["valid"])

        # >16 DATASET via APP BOUNDARIES
        logger.info("\n[Test K] DATASET LENGTH >16 REJECTED BY BACKEND")
        from app.main import generate_proof as generate_proof_route
        from fastapi import HTTPException
        
        main_mod.circuit_registry = registry
        
        mock_req_id = "mock_req_1"
        main_mod.requests_store[mock_req_id] = {
            "nonce": req_nonce_a,
            "status": VerificationStatus.PENDING,
            "audit_trail": [],
            "proof_specifications": [
                ProofSpecification(
                    proof_id="mock_proof",
                    claim_id="mock_claim",
                    method=PrivacyStrategyType.ZERO_KNOWLEDGE,
                    circuit="sum_greater_than",
                    circuit_version="1.2.0",
                    statement=ProofStatement(
                        operation="SUM",
                        field="amounts",
                        operator=">",
                        threshold=100,
                        circuit_scaled_value=100
                    ),
                    private_inputs=[], public_inputs=[], public_outputs=[], evidence_source="mock_ev"
                )
            ]
        }
        
        main_mod.evidence_service.load_evidence_data = lambda src: {"transactions": [{"amount": 100}] * 17}
        main_mod.evidence_service.extract_amounts_for_circuit = lambda ev, m: [t["amount"] for t in ev["transactions"]]
        
        try:
            await generate_proof_route(mock_req_id)
            check(">16 inputs → backend rejects", False)
        except HTTPException as e:
            check(">16 inputs → backend rejects", e.status_code == 400)

        # CROSS-REQUEST REPLAY
        logger.info("\n[Test L] CROSS-REQUEST REPLAY")
        mock_req_2_id = "mock_req_2"

        main_mod.requests_store[mock_req_2_id] = {
            "nonce": req_nonce_b, # Request B with different nonce
            "status": VerificationStatus.PROVING,
            "claims": [],
            "evidence_mappings": [],
            "privacy_strategies": [],
            "verification_results": [],
            "audit_trail": [],
            "proof_artifacts": {
                "proof": proof_valid["proof"],
                "public_signals": proof_valid["public_signals"]
            },
            "proof_specifications": [
                ProofSpecification(
                    proof_id="mock_proof_2",
                    claim_id="mock_claim_2",
                    method=PrivacyStrategyType.ZERO_KNOWLEDGE,
                    circuit=circuit_id,
                    circuit_version=version,
                    statement=ProofStatement(
                        operation="SUM", field="amounts", operator=">", threshold=100, circuit_scaled_value=100
                    ),
                    private_inputs=[], public_inputs=[], public_outputs=[], evidence_source="mock_ev"
                )
            ]
        }

        from app.main import verify_proof as verify_proof_route
        res = await verify_proof_route(mock_req_2_id)
        # Assuming the status gets updated on VerificationResult
        check("cross-request replay → actual verification rejects", res.verification_result.status == ProofStatus.PROOF_INVALID)

        # WRONG CIRCUIT VERSION
        logger.info("\n[Test M] WRONG CIRCUIT VERSION")
        bad_version = registry.lookup_circuit("sum_greater_than", "1.1.0", "SUM", ">")
        check("deprecated version → registry rejects", bad_version is None)

        # UNREGISTERED CIRCUIT
        logger.info("\n[Test N] UNREGISTERED CIRCUIT")
        unreg = registry.lookup_circuit("malicious_circuit_v1", "1.0", "SUM", ">")
        check("unregistered circuit → registry rejects", unreg is None)

        # INTEGRITY HASH (Test Artifacts)
        logger.info("\n[Test O] INTEGRITY HASH")
        inte_results = registry.verify_artifact_integrity(circuit_id)
        if inte_results.get("error"):
            check("artifact hashes → match registry", False)
        else:
            check("artifact hashes → match registry", all(inte_results.values()))

    except Exception as e:
        logger.error(f"Error during tests: {e}")
        raise e

if __name__ == "__main__":
    asyncio.run(run_tests())
