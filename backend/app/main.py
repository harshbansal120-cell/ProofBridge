"""
ProofBridge — FastAPI Application

API endpoints for the verification pipeline.
All security-critical operations pass through deterministic validation.
"""

import json
import logging
import time
import uuid
import secrets
from contextlib import asynccontextmanager
from datetime import datetime, timezone
import shutil
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware

from app.config import BACKEND_HOST, BACKEND_PORT, FRONTEND_URL, DEMO_DIR
from app.schemas.models import (
    VerificationRequestCreate,
    VerificationRequestResponse,
    AnalysisResponse,
    ProofGenerationResponse,
    ProofVerificationResponse,
    VerificationResult,
    CircuitInfo,
    DemoScenario,
    AuditEvent,
    AuditEventType,
    VerificationStatus,
    ProofStatus,
    PrivacyStrategyType,
    ClaimOperation,
    TrustLevel,
)

from app.ai.orchestrator import PipelineOrchestrator
from app.services.capability_service import CapabilityService
from app.services.circuit_registry import CircuitRegistryService
from app.services.attestation_service import attestation_service
from app.services.semantic_filter_service import SemanticFilterService
from app.services.evidence import EvidenceService
from app.services.zk_engine import ZKEngine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ─── In-memory storage (SQLite upgrade path available) ───
requests_store: dict[str, dict] = {}

# ─── Services ────────────────────────────────────────────
circuit_registry = CircuitRegistryService()
evidence_service = EvidenceService()
capability_service = CapabilityService(circuit_registry)
zk_engine = ZKEngine()
pipeline_orchestrator = PipelineOrchestrator(capability_service, circuit_registry, evidence_service)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("ProofBridge backend starting")
    from app.config import AI_MODE
    logger.info(f"AI Mode: {AI_MODE}")
    logger.info(f"Circuits: {[c.id for c in circuit_registry.get_all_circuits()]}")
    yield
    logger.info("ProofBridge backend shutting down")


app = FastAPI(
    title="ProofBridge API",
    description="AI Privacy Proof Planner — Prove what matters. Reveal nothing more.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL, "http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _add_audit(request_id: str, event_type: AuditEventType, actor: str = "system", metadata: dict = None):
    if request_id not in requests_store:
        return
    event = AuditEvent(
        id=f"AE-{uuid.uuid4().hex[:8]}",
        timestamp=_now(),
        request_id=request_id,
        event_type=event_type,
        actor=actor,
        metadata=metadata or {},
    )
    requests_store[request_id]["audit_trail"].append(event)


# ─── Health ──────────────────────────────────────────────

@app.get("/api/health")
async def health():
    from app.config import AI_MODE
    return {
        "status": "healthy",
        "version": "1.0.0",
        "ai_mode": AI_MODE,
        "circuits": len(circuit_registry.get_all_circuits()),
        "timestamp": _now(),
    }


# ─── Verification Requests ──────────────────────────────

@app.post("/api/verification-requests", response_model=VerificationRequestResponse)
async def create_verification_request(req: VerificationRequestCreate):
    request_id = f"VR-{uuid.uuid4().hex[:8]}"
    now = _now()

    nonce = str(secrets.randbelow(2**252))

    record = {
        "id": request_id,
        "request_text": req.request_text,
        "evidence_ids": req.evidence_ids,
        "nonce": nonce,
        "status": VerificationStatus.PENDING,
        "claims": [],
        "evidence_mappings": [],
        "privacy_strategies": [],
        "proof_specifications": [],
        "verification_results": [],
        "audit_trail": [],
        "proof_artifacts": {},
        "created_at": now,
        "updated_at": now,
        "ai": {}
    }
    requests_store[request_id] = record

    _add_audit(request_id, AuditEventType.REQUEST_RECEIVED, metadata={
        "request_text_length": len(req.request_text),
        "evidence_ids": req.evidence_ids,
    })

    return _to_response(record)


@app.get("/api/verification-requests/{request_id}", response_model=VerificationRequestResponse)
async def get_verification_request(request_id: str):
    if request_id not in requests_store:
        raise HTTPException(status_code=404, detail="Request not found")
    return _to_response(requests_store[request_id])


@app.get("/api/verification-requests", response_model=list[VerificationRequestResponse])
async def list_verification_requests():
    return [_to_response(r) for r in requests_store.values()]


# ─── Analysis ────────────────────────────────────────────

@app.post("/api/verification-requests/{request_id}/analyze", response_model=AnalysisResponse)
async def analyze_request(request_id: str):
    if request_id not in requests_store:
        raise HTTPException(status_code=404, detail="Request not found")

    record = requests_store[request_id]
    record["status"] = VerificationStatus.ANALYZING
    record["updated_at"] = _now()

    # Run modular AI analysis pipeline
    try:
        result = await pipeline_orchestrator.analyze(
            record["request_text"],
            record.get("evidence_ids", []),
        )
    except Exception as e:
        if "OPEN_SOURCE_MODEL_UNAVAILABLE" in str(e):
            raise HTTPException(status_code=503, detail="OPEN_SOURCE_MODEL_UNAVAILABLE")
        raise HTTPException(status_code=500, detail=str(e))

    # Deterministic Unit Normalization & Nonce assignment
    for spec in result["proof_specifications"]:
        spec.request_nonce = record.get("nonce")
        if spec.statement.threshold is not None:
            if spec.statement.source_unit == "INR":
                spec.statement.circuit_scaled_value = int(spec.statement.threshold * 100)
            elif spec.statement.source_unit == "paisa":
                spec.statement.circuit_scaled_value = int(spec.statement.threshold)
            else:
                spec.statement.circuit_scaled_value = int(spec.statement.threshold)
                
    # Store results
    record["claims"] = result["claims"]
    record["evidence_mappings"] = result["evidence_mappings"]
    record["privacy_strategies"] = result["privacy_strategies"]
    record["proof_specifications"] = result["proof_specifications"]
    record["ai"] = result.get("ai", {})

    # Determine status
    if result["proof_specifications"]:
        record["status"] = VerificationStatus.PROOF_SPEC_GENERATED
    elif any(s.strategy == PrivacyStrategyType.HUMAN_REVIEW for s in result["privacy_strategies"]):
        record["status"] = VerificationStatus.REVIEW_REQUIRED
    elif any(s.strategy == PrivacyStrategyType.UNSUPPORTED for s in result["privacy_strategies"]):
        record["status"] = VerificationStatus.REFUSED
    elif any(s.strategy == PrivacyStrategyType.SELECTIVE_DISCLOSURE for s in result["privacy_strategies"]):
        record["status"] = VerificationStatus.STRATEGY_SELECTED
    else:
        record["status"] = VerificationStatus.CLAIMS_EXTRACTED

    record["updated_at"] = _now()

    _add_audit(request_id, AuditEventType.CLAIMS_EXTRACTED, actor="ai", metadata={
        "num_claims": len(result["claims"]),
        "num_proof_specs": len(result["proof_specifications"]),
        "pipeline_duration_ms": result["pipeline_duration_ms"],
    })

    return AnalysisResponse(
        request_id=request_id,
        claims=result["claims"],
        evidence_mappings=result["evidence_mappings"],
        privacy_strategies=result["privacy_strategies"],
        proof_specifications=result["proof_specifications"],
        pipeline_duration_ms=result["pipeline_duration_ms"],
        ai=result.get("ai", {})
    )


# ─── Proof Generation ───────────────────────────────────

@app.post("/api/verification-requests/{request_id}/generate-proof", response_model=ProofGenerationResponse)
async def generate_proof(request_id: str):
    if request_id not in requests_store:
        raise HTTPException(status_code=404, detail="Request not found")

    record = requests_store[request_id]

    # Find ZK proof specification
    zk_specs = [s for s in record["proof_specifications"]
                if s.method == PrivacyStrategyType.ZERO_KNOWLEDGE and s.circuit]

    if not zk_specs:
        raise HTTPException(status_code=400, detail="No ZK proof specification available")

    spec = zk_specs[0]

    # Deterministic validation — verify circuit exists and is active
    circuit = circuit_registry.lookup_circuit(
        spec.circuit,
        spec.circuit_version,
        operation=spec.statement.operation,
        operator=spec.statement.operator,
    )
    if not circuit:
        raise HTTPException(status_code=400, detail=f"Circuit '{spec.circuit}' not found or incompatible")

    _add_audit(request_id, AuditEventType.CIRCUIT_SELECTED, metadata={
        "circuit": spec.circuit,
        "version": circuit.get("version"),
    })

    # Load evidence (the raw array of parsed row dicts)
    evidence_data = evidence_service.load_evidence_data(spec.evidence_source)
    if not evidence_data:
        raise HTTPException(status_code=400, detail=f"Evidence '{spec.evidence_source}' not found")
        
    dataset = evidence_data.get("transactions", [])
    
    # ---------------------------------------------------------
    # BOUNDARY 1: DEMO ATTESTATION VERIFICATION
    # ---------------------------------------------------------
    es_obj = evidence_service.get_source(spec.evidence_source)
    
    attestation = evidence_service.get_attestation(spec.evidence_source)
    if es_obj and es_obj.source_type == TrustLevel.PROCESSOR_ATTESTED:
        if not attestation:
            raise HTTPException(status_code=400, detail="Evidence claims PROCESSOR_ATTESTED but no attestation found.")
        
        # Verify the signature binding over the EXACT parsed dataset
        is_valid = attestation_service.verify_attestation(attestation, dataset)
        if not is_valid:
            raise HTTPException(status_code=400, detail="INVALID_SIGNATURE or DATASET_HASH_MISMATCH: Authenticity check failed.")
    elif es_obj and es_obj.source_type == TrustLevel.MERCHANT_UPLOADED:
        raise HTTPException(status_code=400, detail="UNAUTHENTICATED_EVIDENCE: Cannot generate strong cryptographic proof from untrusted merchant uploads.")
        
    # ---------------------------------------------------------
    # BOUNDARY 2: DETERMINISTIC SEMANTIC FILTERING
    # ---------------------------------------------------------
    # This filters the authenticated dataset to extract only eligible rows
    claim_dsl = next((c for c in record["claims"] if c.id == spec.claim_id), None)
    if not claim_dsl:
        raise HTTPException(status_code=400, detail="Claim DSL not found")
        
    filtered_dataset, filter_stats = SemanticFilterService.apply_filters(dataset, claim_dsl)
    record["semantic_validation"] = filter_stats
    
    # Verify we still have data
    if not filtered_dataset:
        raise HTTPException(status_code=400, detail="SEMANTIC_FILTER_EMPTY: No transactions satisfied the claim criteria.")
        
    max_in = circuit.get("max_inputs", 16)
    if len(filtered_dataset) > max_in:
        raise HTTPException(status_code=400, detail=f"UNSUPPORTED_DATASET_SIZE: Expected max {max_in} eligible records.")
        
    # ---------------------------------------------------------
    # PREPARE WITNESS FOR ZK
    # ---------------------------------------------------------
    # Extract amounts for circuit from the FILTERED dataset
    filtered_evidence_data = {"transactions": filtered_dataset}
    amounts = evidence_service.extract_amounts_for_circuit(filtered_evidence_data, max_in)

    # Fetch deterministic scaled threshold (do not use raw threshold anymore)
    if spec.statement.circuit_scaled_value is None:
        raise HTTPException(status_code=400, detail="Missing circuit_scaled_value from deterministic normalization")
    threshold_paisa = spec.statement.circuit_scaled_value

    # Compute evidence commitment using Poseidon over the private array!
    commitment = zk_engine.compute_poseidon_hash(amounts)
    spec.evidence_commitment = commitment

    record["status"] = VerificationStatus.PROVING
    record["updated_at"] = _now()

    paths = circuit_registry.get_circuit_paths(spec.circuit, spec.circuit_version)
    if not paths:
        raise HTTPException(status_code=400, detail="Circuit artifacts not found.")

    proof_result = await zk_engine.generate_proof(
        circuit_id=spec.circuit,
        paths=paths,
        amounts=amounts,
        threshold=threshold_paisa,
        nonce=record["nonce"]
    )

    if proof_result["status"] == ProofStatus.PROOF_GENERATION_FAILED:
        record["status"] = VerificationStatus.FAILED
        record["updated_at"] = _now()
        _add_audit(request_id, AuditEventType.ERROR, metadata={
            "error": proof_result.get("error", "Unknown"),
        })
        return ProofGenerationResponse(
            request_id=request_id,
            proof_id=spec.proof_id,
            status=ProofStatus.PROOF_GENERATION_FAILED,
        )

    # Store proof artifacts (NOT the private witness)
    record["proof_artifacts"] = {
        "proof": proof_result["proof"],
        "public_signals": proof_result["public_signals"],
        "dataset_hash": proof_result.get("dataset_hash"),
    }
    
    auth_meta = None
    if attestation:
        auth_meta = {
            "status": "AUTHENTICATED",
            "issuer": attestation.issuer,
            "dataset_id": attestation.dataset_id,
            "signature": bool(attestation.signature)
        }
    record["evidence_authentication"] = auth_meta

    _add_audit(request_id, AuditEventType.PROOF_GENERATED, metadata={
        "circuit": spec.circuit,
        "proving_time_ms": proof_result["duration_ms"],
        "proving_system": "groth16",
        "curve": "bn128",
        # Do NOT log private witness data
    })

    return ProofGenerationResponse(
        request_id=request_id,
        proof_id=spec.proof_id,
        status=ProofStatus.PROOF_GENERATED,
        circuit=spec.circuit,
        proving_time_ms=proof_result["duration_ms"],
        evidence_commitment=commitment,
    )


# ─── Proof Verification ─────────────────────────────────

@app.post("/api/verification-requests/{request_id}/verify-proof", response_model=ProofVerificationResponse)
async def verify_proof(request_id: str):
    if request_id not in requests_store:
        raise HTTPException(status_code=404, detail="Request not found")

    record = requests_store[request_id]
    artifacts = record.get("proof_artifacts", {})

    if not artifacts.get("proof") or not artifacts.get("public_signals"):
        raise HTTPException(status_code=400, detail="No proof to verify. Generate a proof first.")

    zk_specs = [s for s in record["proof_specifications"]
                if s.method == PrivacyStrategyType.ZERO_KNOWLEDGE and s.circuit]

    if not zk_specs:
        raise HTTPException(status_code=400, detail="No ZK proof specification")

    spec = zk_specs[0]

    # Cryptographic request binding verification!
    # Explicitly check that the verifier's public_signals contains the exact nonce for this explicit request database session.
    is_nonce_bound = str(record["nonce"]) in artifacts["public_signals"]
    if not is_nonce_bound:
        logger.error(f"REPLAY ATTACK DETECTED: Proof nonce does not match session {record['nonce']}")
        verification = {"status": ProofStatus.PROOF_INVALID, "duration_ms": 0, "valid": False}
    else:
        paths = circuit_registry.get_circuit_paths(spec.circuit, spec.circuit_version)
        if not paths:
            raise HTTPException(status_code=400, detail="Circuit artifacts not found.")
            
        # Verify using the ACTUAL cryptographic verifier
        verification = await zk_engine.verify_proof(
            circuit_id=spec.circuit,
            paths=paths,
            proof=artifacts["proof"],
            public_signals=artifacts["public_signals"],
        )

    # Build verification result
    claim_desc = ""
    if record["claims"]:
        claim_desc = record["claims"][0].description

    result = VerificationResult(
        request_id=request_id,
        claim_id=spec.claim_id,
        claim_description=claim_desc,
        status=verification["status"],
        proof_id=spec.proof_id,
        circuit=spec.circuit,
        circuit_version=spec.circuit_version,
        proving_system="groth16",
        evidence_commitment=spec.evidence_commitment,
        evidence_provenance=evidence_service.get_source(spec.evidence_source).source_type.value if evidence_service.get_source(spec.evidence_source) else "UNKNOWN",
        verification_time_ms=verification.get("duration_ms"),
        timestamp=_now(),
        data_disclosed={
            "transaction_amounts": 0,
            "customer_identities": 0,
            "raw_records": 0,
        },
        privacy_strategy=PrivacyStrategyType.ZERO_KNOWLEDGE,
        evidence_authentication=record.get("evidence_authentication"),
        semantic_validation=record.get("semantic_validation")
    )

    record["verification_results"] = [result]

    if verification["status"] == ProofStatus.PROOF_VERIFIED:
        record["status"] = VerificationStatus.VERIFIED
    else:
        record["status"] = VerificationStatus.FAILED

    record["updated_at"] = _now()

    _add_audit(request_id, AuditEventType.PROOF_VERIFIED, metadata={
        "status": verification["status"].value,
        "verification_time_ms": verification.get("duration_ms"),
        "valid": verification.get("valid", False),
    })

    return ProofVerificationResponse(
        request_id=request_id,
        verification_result=result,
    )

# ─── Spoof Endpoint for Demo Replay Attack ─────────────────

@app.post("/api/verification-requests/{request_id}/spoof-proof")
async def spoof_proof(request_id: str, source_id: str):
    """
    DEMO ONLY: Simulates an attacker uploading a captured proof from an older request.
    This allows the UI to trigger a real verification failure against the backend verifier.
    """
    if request_id not in requests_store:
        raise HTTPException(status_code=404, detail="Target request not found")
    if source_id not in requests_store:
        raise HTTPException(status_code=404, detail="Source request not found")
        
    requests_store[request_id]["proof_artifacts"] = requests_store[source_id]["proof_artifacts"]
    return {"status": "SPOOF_INJECTED"}


@app.get("/api/verification-requests/{request_id}/receipt", response_model=VerificationResult)
async def get_verification_receipt(request_id: str):
    req = requests_store.get(request_id)
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")

    if not req.get("verification_results"):
        raise HTTPException(status_code=400, detail="Verification has not been completed")

    # Serve the last verification result exactly as built by the deterministic verifier.
    # It NEVER exposes private records/witnesses by schema design.
    return req["verification_results"][-1]


# ─── Audit Trail ────────────────────────────────────────

@app.get("/api/verification-requests/{request_id}/audit")
async def get_audit_trail(request_id: str):
    if request_id not in requests_store:
        raise HTTPException(status_code=404, detail="Request not found")
    return requests_store[request_id].get("audit_trail", [])


# ─── Circuits ────────────────────────────────────────────

@app.get("/api/circuits", response_model=list[CircuitInfo])
async def list_circuits():
    return circuit_registry.get_all_circuits()


@app.get("/api/circuits/{circuit_id}/integrity")
async def check_circuit_integrity(circuit_id: str):
    results = circuit_registry.verify_artifact_integrity(circuit_id)
    return {
        "circuit_id": circuit_id,
        "integrity": results,
        "all_valid": all(results.values()),
    }


# ─── Evidence ────────────────────────────────────────────

@app.post("/api/evidence-sources/upload")
async def upload_evidence(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf") or file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF documents are supported for ledger uploads.")
        
    # Security: limit file size strictly to ~2MB (enforced in frontend and read layer ideally)
    data = await file.read()
    if len(data) > 2 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large. Maximum size is 2MB.")
        
    evidence_id = f"evd_{uuid.uuid4().hex[:8]}"
    upload_dir = DEMO_DIR / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_path = upload_dir / f"{evidence_id}.pdf"
    
    with open(file_path, "wb") as f:
        f.write(data)
        
    # Untrusted data processing
    try:
        record_count = evidence_service.process_pdf_upload(str(file_path), evidence_id)
        return {"evidence_id": evidence_id, "status": "processed", "record_count": record_count}
    except Exception as e:
        # Fail closed on extraction errors
        logger.error(f"Evidence extraction failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/evidence-sources")
async def list_evidence_sources():
    sources = evidence_service.get_all_sources()
    return [s.model_dump() for s in sources]


@app.get("/api/evidence-sources/{source_id}/privacy-analysis")
async def evidence_privacy_analysis(source_id: str):
    analysis = evidence_service.get_privacy_analysis(source_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="Evidence source not found")
    return analysis

from app.services.demo_processor import demo_processor
from pydantic import BaseModel
from app.schemas.models import Attestation

class AttestedLedgerPayload(BaseModel):
    dataset: list[dict]
    attestation: Attestation

@app.get("/api/demo/processor/issue-attestation/{merchant_id}")
async def fetch_demo_processor_ledger(merchant_id: str):
    """
    Demo Processor Simulator. Independently creates and signs canoncal ledgers.
    """
    try:
        data = demo_processor.issue_demo_ledger(merchant_id)
        return data
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/evidence-sources/upload-attested")
async def upload_attested_evidence(payload: AttestedLedgerPayload):
    """
    Directly uploads an attested JSON ledger, skipping PDF extraction.
    """
    try:
        from app.schemas.models import TrustLevel, EvidenceSource
        import uuid
        
        source_id = f"evd_{uuid.uuid4().hex[:8]}"
        
        # We store the raw dataset
        evidence_service.store_attested_dataset(source_id, payload.dataset, payload.attestation)
        
        source = EvidenceSource(
            id=source_id,
            name=f"{payload.attestation.dataset_id}.json",
            format="JSON",
            fields=[],
            source_type=TrustLevel.PROCESSOR_ATTESTED,
            issuer=payload.attestation.issuer,
            attestation_status="authenticated",
            note="JSON payload attested by independent processor."
        )
        return source.model_dump()
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ─── Demo Scenarios ──────────────────────────────────────

@app.get("/api/demo/scenarios", response_model=list[DemoScenario])
async def list_demo_scenarios():
    return [
        DemoScenario(
            id="sc_volume",
            title="SaaS Revenue Volume",
            description="Prove that total processing volume over the last 6 months exceeded ₹10,00,000 without revealing individual transactions.",
            request_text="Did our total successful INR processing volume in the last 6 months exceed 1M INR?",
            expected_strategy=PrivacyStrategyType.ZERO_KNOWLEDGE,
            expected_operation=ClaimOperation.SUM,
        ),
        DemoScenario(
            id="scenario_2",
            title="Average Transaction Value",
            description="Prove that average transaction value is below ₹50,000.",
            request_text="Provide your average transaction value and demonstrate that it is below ₹50,000.",
            expected_strategy=PrivacyStrategyType.ZERO_KNOWLEDGE,
            expected_operation=ClaimOperation.AVERAGE,
        ),
        DemoScenario(
            id="scenario_3",
            title="Age Verification",
            description="Prove that the proprietor is over 18 years old.",
            request_text="Please prove the proprietor is over 18.",
            expected_strategy=PrivacyStrategyType.VERIFIABLE_CREDENTIAL,
            expected_operation=ClaimOperation.AGE,
        ),
        DemoScenario(
            id="scenario_4",
            title="Refund Investigation (Non-ZK)",
            description="Provide transaction-specific evidence — ZK is NOT suitable.",
            request_text="Provide the five largest transactions and explain why each was refunded.",
            expected_strategy=PrivacyStrategyType.SELECTIVE_DISCLOSURE,
            expected_operation=ClaimOperation.MATCH,
        ),
        DemoScenario(
            id="scenario_5",
            title="Subjective Assessment (Unsupported)",
            description="'Trustworthy' is subjective — requires human review.",
            request_text="Prove that the merchant is trustworthy.",
            expected_strategy=PrivacyStrategyType.HUMAN_REVIEW,
        ),
    ]


# ─── Helper ──────────────────────────────────────────────

def _to_response(record: dict) -> VerificationRequestResponse:
    return VerificationRequestResponse(
        id=record["id"],
        request_text=record["request_text"],
        status=record["status"],
        claims=record["claims"],
        evidence_mappings=record["evidence_mappings"],
        privacy_strategies=record["privacy_strategies"],
        proof_specifications=record["proof_specifications"],
        verification_results=record["verification_results"],
        audit_trail=record["audit_trail"],
        created_at=record["created_at"],
        updated_at=record["updated_at"],
        ai=record.get("ai", {})
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=BACKEND_HOST, port=BACKEND_PORT)
