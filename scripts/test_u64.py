import asyncio, sys, logging, json
from pathlib import Path
sys.path.insert(0, str(Path("backend").resolve()))
from app.services.zk_engine import ZKEngine
from app.services.circuit_registry import CircuitRegistryService

logging.basicConfig(level=logging.INFO)

async def run():
    registry = CircuitRegistryService()
    circuit_id = "sum_greater_than"
    version = "1.2.0"
    paths = registry.get_circuit_paths(circuit_id, version)
    if not paths:
        print("Failed to get paths for circuit")
        sys.exit(1)

    zk = ZKEngine()
    max_u64 = (1 << 64) - 1
    amounts = [max_u64] + [0]*15
    
    threshold = 1000
    nonce = "123"
    
    res = await zk.generate_proof(circuit_id, paths, amounts, threshold, nonce)
    print("Generate Output:", json.dumps(res, indent=2))
    
    if res.get("status") == "PROOF_GENERATED":
        proof = res["proof"]
        public_signals = res["public_signals"]
        v_res = await zk.verify_proof(circuit_id, paths, proof, public_signals)
        print("Verify Output:", json.dumps(v_res, indent=2))
        if not v_res.get("valid"):
            sys.exit(1)
    else:
        sys.exit(1)

asyncio.run(run())
