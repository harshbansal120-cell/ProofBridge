"""
ProofBridge — Attestation Verification Service

Validates incoming datasets against cryptographic attestations.
Strictly relies on pre-provisioned trusted public keys located in the TRUSTED_ISSUERS registry.
Does NOT generate attestations or create signatures.
"""

import logging
import json
import hashlib
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.exceptions import InvalidSignature

from app.config import TRUSTED_ISSUERS
from app.schemas.models import Attestation

logger = logging.getLogger(__name__)

class ProofBridgeVerifier:
    def __init__(self):
        # Load registry into memory
        self.registry = {}
        for issuer, config in TRUSTED_ISSUERS.items():
            path = Path(config["public_key_path"])
            if path.exists():
                with open(path, "rb") as f:
                    pubkey = serialization.load_pem_public_key(f.read())
                    if not isinstance(pubkey, ed25519.Ed25519PublicKey):
                        logger.warning(f"Issuer {issuer} key is not Ed25519!")
                        continue
                    self.registry[(issuer, config["key_id"])] = pubkey
            else:
                logger.warning(f"TRUST ANCHOR MISSING: Could not load public key for {issuer} at {path}")

    def verify_attestation(self, attestation: Attestation, dataset: list[dict]) -> bool:
        """
        Fails closed on any invalidity.
        Enforces canonical JSON matching.
        Looks up public key from independent TRUSTED_ISSUERS registry.
        """
        # 1. Look up trusted public key (Explicitly ignore attestation.public_key)
        pubkey = self.registry.get((attestation.issuer, attestation.key_id))
        if not pubkey:
            logger.error(f"UNKNOWN_ISSUER_OR_KEY: {attestation.issuer} / {attestation.key_id} is not in the trusted registry.")
            return False

        # 2. Re-verify the dataset hash against the exact dataset object
        # Must exactly match the processor's canonization rules
        canonical_json = json.dumps(dataset, sort_keys=True, separators=(",", ":"))
        actual_hash = hashlib.sha256(canonical_json.encode()).hexdigest()
        
        if actual_hash != attestation.dataset_hash:
            logger.error("DATASET_HASH_MISMATCH: The dataset does not match the authenticated hash.")
            return False
            
        # 3. Verify the signature
        message_obj = {
            "issuer": attestation.issuer,
            "dataset_id": attestation.dataset_id,
            "dataset_hash": attestation.dataset_hash,
            "issued_at": attestation.issued_at,
            "key_id": attestation.key_id
        }
        msg_canonical = json.dumps(message_obj, sort_keys=True, separators=(",", ":"))
        
        try:
            pubkey.verify(bytes.fromhex(attestation.signature), msg_canonical.encode())
            return True
        except InvalidSignature:
            logger.error("INVALID_SIGNATURE")
            return False
        except Exception as e:
            logger.error(f"ATTESTATION_VERIFICATION_ERROR: {str(e)}")
            return False

# Global Singleton
attestation_service = ProofBridgeVerifier()
