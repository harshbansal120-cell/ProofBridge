import asyncio
import os
import time
from dotenv import load_dotenv

# Load from .env if present
load_dotenv(dotenv_path="../.env")

# Direct imports from backend to test the provider resolution
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))
from app.config import GEMINI_API_KEY, GEMINI_MODEL
from app.ai.factory import AIFactory

async def test_real_llm_path():
    print("==============================================")
    print("Testing Production AI Path (Gemini Provider)")
    print("==============================================\n")
    
    # 1/7. Check API Key configuration explicitly
    if not GEMINI_API_KEY:
        print("🚨 NO API KEY CONFIGURED 🚨")
        print("GEMINI_API_KEY is missing from environment or .env file.")
        print("ProofBridge cannot execute the live AI path without a valid key.")
        print("DemoProvider is currently serving requests as the fallback.")
        print("To run this test, please configure GEMINI_API_KEY.")
        sys.exit(1)
        
    print(f"✅ Provider: Gemini (Production)")
    print(f"✅ Model: {GEMINI_MODEL}")
    
    print("\nInitializing Gemini Intent Model directly...")
    try:
        provider = AIFactory.get_intent_model('gemini')
    except Exception as e:
        print(f"Failed to initialize Gemini Intent Model: {e}")
        sys.exit(1)

    # 4. Three novel requests not in DemoProvider
    test_cases = [
        {
            "id": "REQ_NOVEL_1",
            "prompt": "Prove that our monthly processing volume exceeded ₹7.5 lakh."
        },
        {
            "id": "REQ_NOVEL_2",
            "prompt": "Verify that the average order value during Q3 was below ₹32,500."
        },
        {
            "id": "REQ_NOVEL_3",
            "prompt": "Show that the merchant has been registered for more than 3 years."
        },
        {
            "id": "REQ_NOVEL_4",
            "prompt": "We need to establish that our refund activity wasn't unusually high during the previous quarter without giving the processor our complete transaction history."
        },
        {
            "id": "REQ_NOVEL_5",
            "prompt": "Prove that we're a reliable merchant."
        }
    ]

    import json
    # A simplified version of the system prompt to just get structured extraction for the test
    system_prompt = """
You are ProofBridge AI. Extract a verification claim from the text.
Output ONLY strict JSON matching this structure:
{
  "claims": [{"operation": "SUM|AVERAGE|AGE|MATCH", "field": "...", "threshold": 123, "unit": "..."}]
}
If subjective, use operation: MATCH, threshold: null.
"""

    for case in test_cases:
        print(f"\n--- Testing Request ID: {case['id']} ---")
        print(f"Request: \"{case['prompt']}\"")
        
        start_time = time.time()
        try:
            # 2. Confirm actual API call using the intent role abstraction
            result = await provider.extract_intent(case["prompt"])
            latency = time.time() - start_time
            
            # 3. Log required fields
            print(f"Status: Success")
            print(f"Latency: {latency:.2f}s")
            
            # 5. Confirm structured outputs
            print(f"Structured Output: {result.model_dump_json(indent=2)}")
            
        except Exception as e:
            latency = time.time() - start_time
            print(f"Status: Failed")
            print(f"Latency: {latency:.2f}s")
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_real_llm_path())
