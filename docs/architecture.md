# System Architecture

## Threat Model & Security Boundaries
ProofBridge implements a strict semantic vs. cryptographic separation. 
AI models are notoriously non-deterministic, making them dangerous for generating security rules or code. We isolate their utility from risk execution:

### 1. LLM Semantic Boundary
- **Input:** Natural-language request and unauthenticated evidence schemas.
- **Role:** Understands intent, extracts fields (amounts, age, thresholds), maps to operations, and identifies privacy levels.
- **Output:** JSON Proof Specification. 
- **Security Scope:** The LLM's output is *never* directly executed. It acts completely independently of the cryptographic toolchains.

### 2. Deterministic Validation Layer
- This Python layer intercepts the Proof Specification.
- **Policy Enforcement:** Reconstructs constraints against preset thresholds and supported definitions. 
- **Registry Check:** Reads the `registry.json` and evaluates standard parameters. Refuses proof execution if the given semantic intent has no actively registered mathematical circuit.

### 3. ZK Proof Layer
- **Circom Engine:** Executes pre-compiled, deterministic BN128 circuits. 
- **Dataset Commitment:** Employs a Poseidon mathematical hash passed as a public input to the verifier, tightly bounding the proof to the exact transaction arrays proven. Data authenticity must separately be established by a credential metadata layer.

### 4. Zero-Knowledge Outputs
- The processor-facing API is intentionally air-gapped from privacy variables. Raw amounts, counts, and items never cross the response boundary; only the validity of the computed predicate and underlying data hashes are disclosed.
