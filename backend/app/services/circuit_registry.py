"""
ProofBridge — Circuit Registry Service

Deterministic validation of circuit lookups.
The LLM may propose a circuit name.
This service validates it exists, is enabled, and matches the request.
"""

import json
import hashlib
from pathlib import Path
from typing import Optional

from app.config import CIRCUITS_DIR
from app.schemas.models import (
    ClaimOperation, ClaimOperator, CircuitInfo, CircuitStatus
)


# Operation mapping from claim operations to circuit operations
OPERATION_MAP = {
    ClaimOperation.SUM: "SUM",
    ClaimOperation.AVERAGE: "AVERAGE",
    ClaimOperation.COUNT: "COUNT",
    ClaimOperation.AGE: "AGE",
}

OPERATOR_MAP = {
    ClaimOperator.GT: ">",
    ClaimOperator.GTE: ">=",
    ClaimOperator.LT: "<",
    ClaimOperator.LTE: "<=",
    ClaimOperator.EQ: "==",
    ClaimOperator.NEQ: "!=",
}


class CircuitRegistryService:
    """Manages the circuit registry — the single source of truth for allowed circuits."""

    def __init__(self):
        self._registry: dict = {}
        self._load_registry()

    def _load_registry(self):
        registry_path = CIRCUITS_DIR / "registry.json"
        if registry_path.exists():
            with open(registry_path, "r") as f:
                self._registry = json.load(f)
        else:
            raise FileNotFoundError(f"Circuit registry not found: {registry_path}")

    def get_all_circuits(self) -> list[CircuitInfo]:
        """List all circuits in the registry."""
        circuits = []
        for c in self._registry.get("circuits", []):
            circuits.append(CircuitInfo(
                id=c["id"],
                version=c["version"],
                status=CircuitStatus(c["status"]),
                description=c["description"],
                predicate=c["predicate"],
                operation=c["operation"],
                operator=c["operator"],
                max_inputs=c.get("max_inputs"),
                constraints=c.get("constraints"),
            ))
        return circuits

    def lookup_circuit(
        self,
        circuit_id: str,
        version: str,
        operation: Optional[ClaimOperation] = None,
        operator: Optional[ClaimOperator] = None,
    ) -> Optional[dict]:
        """
        Look up a circuit by ID and EXACT version, and validate compatibility.
        Returns the full circuit definition or None.
        """
        for c in self._registry.get("circuits", []):
            if c["id"] != circuit_id:
                continue

            # Must have exact version match
            if c["version"] != version:
                continue

            # Must be ACTIVE
            if c.get("status") != "ACTIVE":
                return None

            # Validate operation matches if provided
            if operation and c.get("operation") != OPERATION_MAP.get(operation):
                return None

            # Validate operator matches if provided
            if operator and c.get("operator") != OPERATOR_MAP.get(operator):
                return None

            return c

        return None

    def resolve_circuit_for_claim(
        self,
        operation: ClaimOperation,
        operator: ClaimOperator,
    ) -> Optional[dict]:
        """
        Find a matching ACTIVE circuit for the given operation and operator.
        This is the deterministic resolution path — the LLM does NOT choose the binary.
        """
        op_str = OPERATION_MAP.get(operation)
        op_operator = OPERATOR_MAP.get(operator)

        for c in self._registry.get("circuits", []):
            if c.get("status") != "ACTIVE":
                continue
            if c.get("operation") == op_str and c.get("operator") == op_operator:
                return c

        return None

    def verify_artifact_integrity(self, circuit_id: str) -> dict[str, bool]:
        """Verify SHA-256 hashes of circuit artifacts."""
        circuit = None
        for c in self._registry.get("circuits", []):
            if c["id"] == circuit_id:
                circuit = c
                break

        if not circuit or not circuit.get("artifacts"):
            return {"error": True}

        results = {}
        artifacts = circuit["artifacts"]

        for artifact_key in ["r1cs", "wasm", "zkey", "verification_key"]:
            file_path = artifacts.get(artifact_key)
            expected_hash = artifacts.get(f"{artifact_key}_sha256")

            if not file_path or not expected_hash:
                continue

            full_path = CIRCUITS_DIR / file_path
            if not full_path.exists():
                results[artifact_key] = False
                continue

            actual_hash = hashlib.sha256(full_path.read_bytes()).hexdigest().upper()
            results[artifact_key] = actual_hash == expected_hash.upper()

        return results

    def get_circuit_paths(self, circuit_id: str, version: str) -> Optional[dict]:
        """Get absolute paths to circuit artifacts."""
        circuit = self.lookup_circuit(circuit_id, version)
        if not circuit or not circuit.get("artifacts"):
            return None

        artifacts = circuit["artifacts"]
        return {
            "wasm": str(CIRCUITS_DIR / artifacts["wasm"]),
            "zkey": str(CIRCUITS_DIR / artifacts["zkey"]),
            "verification_key": str(CIRCUITS_DIR / artifacts["verification_key"]),
            "r1cs": str(CIRCUITS_DIR / artifacts["r1cs"]),
        }
