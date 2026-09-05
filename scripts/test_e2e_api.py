import sys
from pathlib import Path
backend_dir = str(Path(__file__).parent.parent / "backend")
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from fastapi.testclient import TestClient
from app.main import app, requests_store
from app.schemas.models import ProofStatus, VerificationStatus

def run_e2e():
    print("=== Fresh Clean E2E Security Run ===\n")
    client = TestClient(app)

    # 1. Create Request A
    print("[1] Creating Request A...")
    res_a = client.post("/api/verification-requests", json={
        "request_text": "Verify processing volume is above 10 Lakh INR",
        "evidence_ids": ["processor_ledger"]
    })
    req_a = res_a.json()
    id_a = req_a["id"]
    nonce_a = requests_store[id_a]["nonce"]
    print(f"  -> {id_a} | Nonce: {nonce_a}")

    # 2. Analyze Request A
    print("[2] Analyzing Request A (LLM Planning)...")
    res_analyze_a = client.post(f"/api/verification-requests/{id_a}/analyze")
    assert res_analyze_a.status_code == 200

    # 3. Generate Request A's proof
    print("[3] Generating Proof A...")
    res_proof_a = client.post(f"/api/verification-requests/{id_a}/generate-proof")
    if res_proof_a.status_code != 200:
        print(f"  ❌ Error generating proof: {res_proof_a.text}")
        sys.exit(1)
    proof_a = res_proof_a.json()
    print(f"  -> Proof Generation Status: {proof_a['status']}")

    # 4. Verify Request A
    print("[4] Verifying Request A...")
    res_ver_a = client.post(f"/api/verification-requests/{id_a}/verify-proof")
    ver_a = res_ver_a.json()
    print(f"  -> Verification Status: {ver_a['verification_result']['status']}")
    assert ver_a['verification_result']['status'] == "PROOF_VERIFIED"
    print("  ✅ Legitimate Request A passed verification.")

    # 5. Create Request B
    print("\n[5] Creating Request B (Target for Replay)...")
    res_b = client.post("/api/verification-requests", json={
        "request_text": "Verify processing volume is above 10 Lakh INR",
        "evidence_ids": ["processor_ledger"]
    })
    req_b = res_b.json()
    id_b = req_b["id"]
    nonce_b = requests_store[id_b]["nonce"]
    print(f"  -> {id_b} | Nonce: {nonce_b}")

    print("[6] Analyzing Request B...")
    client.post(f"/api/verification-requests/{id_b}/analyze")
    client.post(f"/api/verification-requests/{id_b}/generate-proof")

    # 6. Attempt to submit Proof A against Request B
    print("[7] SPOOFING: Submitting Proof A payload for Request B...")
    # Inject Proof A into global state as if the prover submitted it for Request B
    requests_store[id_b]["proof_artifacts"] = requests_store[id_a]["proof_artifacts"]

    # Verify Request B
    print("[8] Verifying Request B...")
    res_ver_b = client.post(f"/api/verification-requests/{id_b}/verify-proof")
    ver_b = res_ver_b.json()
    status_b = ver_b['verification_result']['status']
    print(f"  -> Verification Status: {status_b}")
    assert status_b == "PROOF_INVALID"

    # Confirm Processor UI state is FAILED for Request B
    final_req_b = client.get(f"/api/verification-requests/{id_b}").json()
    if final_req_b["status"] == "FAILED":
        print("  ✅ Replay Attack successfully REJECTED. Security boundaries held.")
    else:
        print("  ❌ VULNERABILITY: Replay Attack bypassed protections!")
        sys.exit(1)

if __name__ == "__main__":
    run_e2e()
