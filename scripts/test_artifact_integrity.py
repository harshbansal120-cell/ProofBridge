#!/usr/bin/env python3
import json
import hashlib
from pathlib import Path
import sys

def verify_artifacts():
    print("========================================")
    print("PROOFBRIDGE ARTIFACT INTEGRITY CHECK")
    print("========================================")
    
    root_dir = Path(__file__).resolve().parent.parent
    registry_path = root_dir / "circuits" / "registry.json"
    
    if not registry_path.exists():
        print(f"ERROR: Registry not found at {registry_path}")
        sys.exit(1)
        
    with open(registry_path, "r", encoding="utf-8") as f:
        registry = json.load(f)
        
    circuits = registry.get("circuits", [])
    has_errors = False
    
    for c in circuits:
        if c.get("status") not in ["ACTIVE", "DEPRECATED"]:
            continue
            
        c_id = c.get("id")
        c_ver = c.get("version")
        status = c.get("status")
        print(f"\nChecking: {c_id} (v{c_ver}) [{status}]")
        
        artifacts = c.get("artifacts", {})
        if not artifacts:
            print("  - No artifacts found in registry.")
            continue
            
        # The expected hashes might be stored either in a separate "hashes" object
        # or flat as "r1cs_sha256" in the "artifacts" object based on old vs new schemas.
        # We will check both.
        expected_hashes = c.get("hashes", {})
        
        # Mapping artifact keys to actual file paths and their hashes
        # E.g. "r1cs": "sum_greater_than/circuit.r1cs"
        keys = ["r1cs", "wasm", "zkey", "verification_key", "vkey"]
        
        for k in keys:
            if k not in artifacts:
                continue
                
            rel_path = artifacts[k]
            abs_path = root_dir / "circuits" / rel_path
            
            # Find expected hash
            expected_hash = expected_hashes.get(k)
            if not expected_hash:
                expected_hash = artifacts.get(f"{k}_sha256")
                
            if not expected_hash:
                print(f"  ? Warning: Missing expected hash mapped for {k}.")
                continue
                
            if not abs_path.exists():
                print(f"  [FAIL] Missing file: {rel_path}")
                has_errors = True
                continue
                
            with open(abs_path, "rb") as af:
                computed_hash = hashlib.sha256(af.read()).hexdigest().lower()
                
            expected_hash = expected_hash.lower()
            if computed_hash == expected_hash:
                print(f"  [PASS] {k} -> {computed_hash[:16]}...")
            else:
                print(f"  [FAIL] {k} hash mismatch!")
                print(f"         Expected: {expected_hash}")
                print(f"         Computed: {computed_hash}")
                has_errors = True
                
    print("\n========================================")
    if has_errors:
        print("INTEGRITY CHECK FAILED. Untrusted artifacts detected.")
        sys.exit(1)
    else:
        print("INTEGRITY CHECK PASSED. All loaded artifacts match registry.")
        sys.exit(0)

if __name__ == "__main__":
    verify_artifacts()
