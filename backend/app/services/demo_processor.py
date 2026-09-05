"""
Simulated External Processor Identity
This completely bypasses ProofBridge's internal pipeline. 
It represents a Demo Processor that independently signs canoncal ledgers.
"""
import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization

from app.config import ROOT_DIR
from app.schemas.models import Attestation

class SimulatedProcessor:
    def __init__(self):
        priv_path = ROOT_DIR / "backend" / ".demo_processor_private_key.pem"
        if not priv_path.exists():
            raise RuntimeError(f"Missing processor private key at {priv_path}. Run scripts/provision_processor_identity.py")
            
        with open(priv_path, "rb") as f:
            self._private_key = serialization.load_pem_private_key(f.read(), password=None)

    def issue_demo_ledger(self, merchant_id: str) -> dict:
        """
        Creates a simulated processor ledger for a given merchant.
        Returns the canonical JSON dataset and the resulting Ed25519 attestation.
        """
        # Create visually and technically convincing dataset
        now = datetime.now(timezone.utc)
        
        # 12 eligible rows (SUCCESS, INR, matching merchant_id, within 6 months)
        dataset = [
            {"transaction_id": f"TXN-E-{i}", "merchant_id": merchant_id, "timestamp": now.isoformat(), 
             "amount_paisa": 10000000 + (i*100000), "currency": "INR", "status": "SUCCESS", "transaction_type": "PAYMENT"}
            for i in range(12)
        ]
        
        # Add some noise: wrong merchant
        dataset += [
            {"transaction_id": f"TXN-WM-{i}", "merchant_id": "OTHER-99", "timestamp": now.isoformat(), 
             "amount_paisa": 50000, "currency": "INR", "status": "SUCCESS", "transaction_type": "PAYMENT"}
            for i in range(5)
        ]
        
        # Add some noise: failed transactions
        dataset += [
            {"transaction_id": f"TXN-F-{i}", "merchant_id": merchant_id, "timestamp": now.isoformat(), 
             "amount_paisa": 250000, "currency": "INR", "status": "FAILED", "transaction_type": "PAYMENT"}
            for i in range(3)
        ]
        
        # Add some noise: USD transactions
        dataset += [
            {"transaction_id": f"TXN-U-{i}", "merchant_id": merchant_id, "timestamp": now.isoformat(), 
             "amount_paisa": 5000, "currency": "USD", "status": "SUCCESS", "transaction_type": "PAYMENT"}
            for i in range(2)
        ]
        
        # Add some noise: outside 6 months
        old_time = "2020-01-01T12:00:00Z"
        dataset += [
            {"transaction_id": f"TXN-O-{i}", "merchant_id": merchant_id, "timestamp": old_time, 
             "amount_paisa": 999999, "currency": "INR", "status": "SUCCESS", "transaction_type": "PAYMENT"}
            for i in range(4)
        ]

        # Ensure consistent ordering for canonical hashing
        dataset.sort(key=lambda x: x["transaction_id"])
        
        # 1. Canonical Normalization
        canonical_json = json.dumps(dataset, sort_keys=True, separators=(",", ":"))
        dataset_hash = hashlib.sha256(canonical_json.encode()).hexdigest()
        
        issued_at = now.isoformat()
        issuer = "DEMO_PROCESSOR"
        key_id = "demo-processor-ed25519-v1"
        dataset_id = f"proc-ledger-{merchant_id}-{int(now.timestamp())}"
        
        # 2. Construct message to sign
        message_obj = {
            "issuer": issuer,
            "dataset_id": dataset_id,
            "dataset_hash": dataset_hash,
            "issued_at": issued_at,
            "key_id": key_id
        }
        msg_canonical = json.dumps(message_obj, sort_keys=True, separators=(",", ":"))
        
        # 3. Sign
        sig_bytes = self._private_key.sign(msg_canonical.encode())
        signature_hex = sig_bytes.hex()
        
        attestation = Attestation(
            issuer=issuer,
            dataset_id=dataset_id,
            dataset_hash=dataset_hash,
            issued_at=issued_at,
            signature=signature_hex,
            public_key="OMITTED_BY_ISSUER_PROXY", # The trust anchor lives in configuration registry
            key_id=key_id,
            algorithm="Ed25519"
        )
        
        return {
            "dataset": dataset,
            "attestation": attestation.model_dump()
        }

# Global external simulation
demo_processor = SimulatedProcessor()
