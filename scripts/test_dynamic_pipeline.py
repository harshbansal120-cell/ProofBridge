import asyncio
import json
from httpx import AsyncClient

API_URL = "http://localhost:18080/api"

async def test_pipeline():
    print("==============================================")
    print("Testing Dynamic AI Analysis Pipeline")
    print("==============================================\n")
    
    test_cases = [
        {
            "name": "ZK Supported - Sum Greater Than",
            "request_text": "Prove that our monthly processing volume exceeded ₹10 lakh.",
            "expect_operation": "SUM",
            "expect_strategy": "ZERO_KNOWLEDGE",
            "expect_zk_executable": True
        },
        {
            "name": "ZK Unsupported Circuit - Average Less Than",
            "request_text": "Prove that our average transaction value was below ₹50,000.",
            "expect_operation": "AVERAGE",
            "expect_strategy": "ZERO_KNOWLEDGE",
            "expect_zk_executable": False
        },
        {
            "name": "Credential Requirement - Age Verification",
            "request_text": "Prove that the business has been registered for more than 2 years.",
            "expect_operation": "AGE",
            "expect_strategy": "VERIFIABLE_CREDENTIAL",
            "expect_zk_executable": False
        },
        {
            "name": "Selective Disclosure - Explain Refunds",
            "request_text": "Provide the five largest transactions and explain why each was refunded.",
            "expect_operation": "MATCH",
            "expect_strategy": "SELECTIVE_DISCLOSURE",
            "expect_zk_executable": False
        },
        {
            "name": "Ambiguous - Subjective Query",
            "request_text": "Prove that the merchant is trustworthy.",
            "expect_operation": "MATCH",
            "expect_strategy": "HUMAN_REVIEW",
            "expect_zk_executable": False
        }
    ]

    async with AsyncClient() as client:
        # Get LLM Provider Mode
        health = await client.get(f"{API_URL}/health")
        h_data = health.json()
        print(f"Backend Provider: {h_data['llm_provider']}")
        
        for idx, case in enumerate(test_cases, 1):
            print(f"\n[{idx}] Testing: {case['name']}")
            print(f"Input: \"{case['request_text']}\"")
            
            # Create Request
            create = await client.post(f"{API_URL}/verification-requests", json={
                "request_text": case["request_text"],
                "evidence_ids": ["processor_ledger", "identity_credential"]
            })
            req_id = create.json()["id"]
            
            # Analyze
            analysis = await client.post(f"{API_URL}/verification-requests/{req_id}/analyze")
            data = analysis.json()
            
            # Extract Results
            operation = data["claims"][0]["operation"] if data["claims"] else None
            strategy = data["privacy_strategies"][0]["strategy"] if data["privacy_strategies"] else None
            
            is_executable = False
            for s in data["proof_specifications"]:
                if s["method"] == "ZERO_KNOWLEDGE" and s["circuit"]:
                    is_executable = True
                    break
                    
            print(f"  Result Operation: {operation}")
            print(f"  Result Strategy : {strategy}")
            print(f"  Circuit Runnable: {is_executable}")
            
            assert operation == case["expect_operation"], f"Expected {case['expect_operation']} but got {operation}"
            assert strategy == case["expect_strategy"], f"Expected {case['expect_strategy']} but got {strategy}"
            assert is_executable == case["expect_zk_executable"], f"Expected runnable={case['expect_zk_executable']}, got {is_executable}"
            
            print("  ✅ Passed")
            
if __name__ == "__main__":
    asyncio.run(test_pipeline())
