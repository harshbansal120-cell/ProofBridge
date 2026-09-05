"""
ProofBridge — API End-to-End Test

Tests the full API flow from verification request to proof verification.
"""

import httpx
import json
import asyncio
import sys

API_URL = "http://127.0.0.1:18080/api"

async def test_api_pipeline():
    print("============================================")
    print("  ProofBridge — API E2E Pipeline Test")
    print("============================================\n")

    async with httpx.AsyncClient(timeout=30.0) as client:
        # 1. Health check
        r = await client.get(f"{API_URL}/health")
        print(f"Health: {r.status_code}")
        
        # 2. Create Verification Request
        print("\n1. Creating verification request...")
        req_data = {
            "request_text": "Please provide your last 6 months of transaction history and demonstrate that your monthly processing volume exceeds \u20b910 lakh.",
            "evidence_ids": ["processor_ledger"]
        }
        r = await client.post(f"{API_URL}/verification-requests", json=req_data)
        if r.status_code != 200:
            print(f"Failed to create request: {r.text}")
            sys.exit(1)
        
        vr = r.json()
        request_id = vr["id"]
        print(f"✓ Request created: {request_id}")
        
        # 3. Analyze Request
        print("\n2. Analyzing request...")
        r = await client.post(f"{API_URL}/verification-requests/{request_id}/analyze")
        if r.status_code != 200:
            print(f"Failed to analyze request: {r.text}")
            sys.exit(1)
        
        analysis = r.json()
        print(f"✓ Analysis complete in {analysis['pipeline_duration_ms']}ms")
        
        if not analysis["proof_specifications"]:
            print("❌ No proof spec generated!")
            sys.exit(1)
            
        spec = analysis["proof_specifications"][0]
        print(f"✓ Strategy: {spec['method']}")
        print(f"✓ Circuit selected: {spec['circuit']} v{spec['circuit_version']}")
        print(f"✓ Field: {spec['statement']['field']} {spec['statement']['operator']} {spec['statement']['threshold']}")
        
        # 4. Generate Proof
        print("\n3. Generating ZK proof...")
        r = await client.post(f"{API_URL}/verification-requests/{request_id}/generate-proof")
        if r.status_code != 200:
            print(f"Failed to generate proof: {r.text}")
            sys.exit(1)
            
        proof_res = r.json()
        print(f"✓ Proof generated in {proof_res['proving_time_ms']}ms")
        print(f"✓ Dataset commitment: {proof_res['evidence_commitment'][:15]}...")
        
        # 5. Verify Proof
        print("\n4. Verifying ZK proof (Verifier)...")
        r = await client.post(f"{API_URL}/verification-requests/{request_id}/verify-proof")
        if r.status_code != 200:
            print(f"Failed to verify proof: {r.text}")
            sys.exit(1)
            
        verify_res = r.json()
        res = verify_res["verification_result"]
        print(f"✓ Proof verified in {res['verification_time_ms']}ms")
        print(f"✓ Status: {res['status']}")
        print(f"✓ Claim: {res['claim_description']}")
        print(f"✓ Disclosed amounts: {res['data_disclosed']['transaction_amounts']}")
        
        # 6. Check Audit Trail
        r = await client.get(f"{API_URL}/verification-requests/{request_id}/audit")
        audit = r.json()
        print(f"\n✓ Audit trail events recorded: {len(audit)}")
        
        if res["status"] != "PROOF_VALID":
            print("\n❌ Pipeline failed to produce PROOF_VALID status.")
            sys.exit(1)
            
        print("\n============================================")
        print("  API E2E TESTS PASSED                      ")
        print("============================================")

if __name__ == "__main__":
    asyncio.run(test_api_pipeline())
