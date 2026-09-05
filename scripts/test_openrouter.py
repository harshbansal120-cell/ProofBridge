import asyncio
import os
import sys
from dotenv import load_dotenv

load_dotenv(dotenv_path="d:/Downloads/ProofBridge/backend/.env")

sys.path.append(r"d:\Downloads\ProofBridge\backend")
from app.config import OPENROUTER_API_KEY, OPENROUTER_MODEL, AI_MODE
from app.ai.factory import AIFactory

async def main():
    print(f"AI_MODE={AI_MODE}")
    print(f"OPENROUTER_API_KEY={'SET' if OPENROUTER_API_KEY else 'NOT SET'}")
    print(f"OPENROUTER_MODEL={OPENROUTER_MODEL}")
    print("")

    if not OPENROUTER_API_KEY:
        print("API key is still NOT SET!")
        return

    try:
        planner = AIFactory.get_planner("production")
        provider_name = planner.__class__.__name__
        is_demo = provider_name == "DemoPlanner"

        print("Provider: OpenRouter")
        print(f"Model: {OPENROUTER_MODEL}")
        print(f"Planner: {provider_name}")
        print(f"DemoPlanner invoked: {'YES' if is_demo else 'NO'}")
        print("")

        request_text = "Prove that our successful transaction processing volume exceeded ₹10 lakh this month without revealing any individual transaction details."
        
        result = await planner.plan(request_text)

        print("PlannerResult:")
        
        cl = result.claim
        ctype = cl.type if hasattr(cl, "type") else "SINGLE"
        
        thresh = cl.threshold.value if cl.threshold else None
        unit = cl.threshold.unit if cl.threshold else None

        print(f"  claim_type: {ctype}")
        print(f"  aggregation: {cl.operation.value if hasattr(cl.operation, 'value') else cl.operation}")
        print(f"  field: {cl.field}")
        print(f"  operator: {cl.operator.value if hasattr(cl.operator, 'value') else cl.operator}")
        print(f"  threshold: {thresh}")
        print(f"  unit: {unit}")

    except Exception as e:
        print(f"Error during execution: {e}")

if __name__ == "__main__":
    asyncio.run(main())
