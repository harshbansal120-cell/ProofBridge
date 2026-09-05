"""
ProofBridge — ZK Proof Engine

Invokes snarkjs via Node.js subprocess for proof generation and verification.
This is the deterministic cryptographic layer.

The Python backend NEVER generates or modifies circuits.
It only calls pre-registered, validated circuits through this engine.
"""

import json
import subprocess
import tempfile
import hashlib
import logging
from pathlib import Path
from typing import Optional

from app.config import CIRCUITS_DIR, SCRIPTS_DIR, NODE_EXECUTABLE, ROOT_DIR
from app.schemas.models import ProofStatus

logger = logging.getLogger(__name__)


class ZKEngine:
    """Executes ZK proof generation and verification via snarkjs."""

    def __init__(self):
        self.prove_script = SCRIPTS_DIR / "prove.mjs"
        if not self.prove_script.exists():
            raise FileNotFoundError(f"Proof script not found: {self.prove_script}")

    def compute_poseidon_hash(self, amounts: list[int]) -> str:
        """
        Compute Poseidon dataset hash using circomlibjs.
        """
        script_path = SCRIPTS_DIR / "compute_poseidon.mjs"
        # Pad to 16
        padded = amounts.copy()
        while len(padded) < 16:
            padded.append(0)
            
        padded_str = [str(x) for x in padded]
        cmd = [NODE_EXECUTABLE, str(script_path), json.dumps(padded_str)]
        res = subprocess.run(cmd, capture_output=True, text=True, cwd=str(ROOT_DIR))
        if res.returncode != 0:
            raise RuntimeError(f"Poseidon failed: {res.stderr}")
        return res.stdout.strip()

    async def generate_proof(
        self,
        circuit_id: str,
        paths: dict,
        amounts: list[int],
        threshold: int,
        nonce: str,
    ) -> dict:
        """
        Generate a Groth16 proof.
        """
        # Ensure exact padding
        padded = amounts.copy()
        while len(padded) < 16:
            padded.append(0)

        # Compute dataset commitment
        dataset_hash = self.compute_poseidon_hash(padded)

        # Prepare circuit input
        circuit_input = {
            "amounts": [str(a) for a in padded],
            "threshold": str(threshold),
            "datasetCommitment": dataset_hash,
            "requestNonce": str(nonce)
        }

        # Write input to temporary file
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, dir=str(ROOT_DIR)
        ) as f:
            json.dump(circuit_input, f)
            input_path = f.name

        # Create temp output directory
        output_dir = tempfile.mkdtemp(dir=str(ROOT_DIR))

        try:
            # Call snarkjs via Node.js subprocess
            cmd = [
                NODE_EXECUTABLE,
                str(self.prove_script),
                "--prove",
                circuit_id,
                input_path,
                paths["wasm"],
                paths["zkey"],
                output_dir,
            ]

            logger.info(f"Generating proof: circuit={circuit_id}")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=str(ROOT_DIR),
            )

            if result.returncode != 0:
                logger.error(f"Proof generation failed: {result.stderr}")
                return {
                    "status": ProofStatus.PROOF_GENERATION_FAILED,
                    "error": result.stderr[:500],
                }

            output = json.loads(result.stdout)

            # Read proof and public signals
            proof_path = Path(output_dir) / "proof.json"
            public_path = Path(output_dir) / "public.json"

            proof = json.loads(proof_path.read_text())
            public_signals = json.loads(public_path.read_text())

            return {
                "status": ProofStatus.PROOF_GENERATED,
                "proof": proof,
                "public_signals": public_signals,
                "duration_ms": output.get("duration_ms", 0),
                "circuit": circuit_id,
                "proving_system": "groth16",
                "curve": "bn128",
                "dataset_hash": dataset_hash,
            }

        except subprocess.TimeoutExpired:
            logger.error("Proof generation timed out")
            return {"status": ProofStatus.PROOF_GENERATION_FAILED, "error": "Timeout"}
        except Exception as e:
            logger.error(f"Proof generation error: {e}")
            raise e
        finally:
            # Cleanup temp files
            try:
                Path(input_path).unlink(missing_ok=True)
                for f in Path(output_dir).iterdir():
                    f.unlink()
                Path(output_dir).rmdir()
            except Exception:
                pass

    async def verify_proof(
        self,
        circuit_id: str,
        paths: dict,
        proof: dict,
        public_signals: list[str],
    ) -> dict:
        """
        Verify a Groth16 proof.
        
        This is the ONLY authority for cryptographic proof validity.
        No other component may claim PROOF_VALID.
        """
        # Write proof and public signals to temp files
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, dir=str(ROOT_DIR)
        ) as f:
            json.dump(proof, f)
            proof_path = f.name

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, dir=str(ROOT_DIR)
        ) as f:
            json.dump(public_signals, f)
            public_path = f.name

        try:
            cmd = [
                NODE_EXECUTABLE,
                str(self.prove_script),
                "--verify",
                circuit_id,
                proof_path,
                public_path,
                paths["verification_key"],
            ]

            logger.info(f"Verifying proof: circuit={circuit_id}")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=15,
                cwd=str(ROOT_DIR),
            )

            output = json.loads(result.stdout)

            if output.get("valid"):
                return {
                    "status": ProofStatus.PROOF_VERIFIED,
                    "valid": True,
                    "duration_ms": output.get("duration_ms", 0),
                    "circuit": circuit_id,
                }
            else:
                return {
                    "status": ProofStatus.PROOF_INVALID,
                    "valid": False,
                    "duration_ms": output.get("duration_ms", 0),
                }

        except Exception as e:
            logger.error(f"Proof verification error: {e}")
            return {
                "status": ProofStatus.PROOF_VERIFICATION_FAILED,
                "valid": False,
                "error": str(e),
            }
        finally:
            try:
                Path(proof_path).unlink(missing_ok=True)
                Path(public_path).unlink(missing_ok=True)
            except Exception:
                pass
