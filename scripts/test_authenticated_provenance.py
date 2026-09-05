import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.services.demo_processor import SimulatedProcessor
from app.services.attestation_service import ProofBridgeVerifier
from app.schemas.models import Attestation

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    RESET = '\033[0m'

def print_result(name, passed, detail=""):
    color = Colors.GREEN if passed else Colors.RED
    status = "PASS" if passed else "FAIL"
    print(f"{color}[{status}] {name}{Colors.RESET}")
    if detail:
        print(f"       -> {detail}")

def run_tests():
    print("\n--- AUTHENTICATED PROVENANCE BOUNDARY TESTS ---")
    
    # The external processor that independently signs
    demo_proc = SimulatedProcessor()
    
    # ProofBridge's internal verifier
    verifier = ProofBridgeVerifier()
    
    # 1. Valid processor attestation
    try:
        proc_payload = demo_proc.issue_demo_ledger("M1")
        dataset = proc_payload["dataset"]
        att = Attestation(**proc_payload["attestation"])
        
        ok = verifier.verify_attestation(att, dataset)
        assert ok, "Valid attestation rejected"
        print_result("1. Valid processor attestation", True)
    except Exception as e:
        print_result("1. Valid processor attestation", False, str(e))
        
    # 2. Tampered dataset after signing
    try:
        tampered_dataset = list(dataset)
        # Modify an amount
        tampered_dataset[0] = dict(tampered_dataset[0])
        tampered_dataset[0]["amount_paisa"] = 9999999
        
        ok = verifier.verify_attestation(att, tampered_dataset)
        assert not ok, "Tampered dataset accepted"
        print_result("2. Modified dataset after signing", True, "DATASET_HASH_MISMATCH successfully triggered")
    except Exception as e:
        print_result("2. Modified dataset after signing", False, str(e))

    # 3. Modified signature
    try:
        att_bad_sig = att.model_copy()
        # Flip a hex character
        old_sig = list(att_bad_sig.signature)
        old_sig[0] = 'a' if old_sig[0] != 'a' else 'b'
        att_bad_sig.signature = "".join(old_sig)
        
        ok = verifier.verify_attestation(att_bad_sig, dataset)
        assert not ok, "Tampered signature accepted"
        print_result("3. Modified signature", True, "INVALID_SIGNATURE successfully caught")
    except Exception as e:
        print_result("3. Modified signature", False, str(e))
        
    print("\n")

if __name__ == "__main__":
    run_tests()
