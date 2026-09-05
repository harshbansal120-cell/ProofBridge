"""
ProofBridge — Evidence Service

Manages evidence documents uploaded as PDFs.
Uses docling for untrusted data extraction.
"""

import json
import hashlib
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
from fastapi import HTTPException
import pandas as pd
import pdfplumber

from app.config import DEMO_DIR
from app.schemas.models import EvidenceSource, EvidenceField, TrustLevel, Attestation

logger = logging.getLogger(__name__)

# Track dynamic uploads locally for demo purposes
_UPLOADED_EVIDENCE_STORE: Dict[str, dict] = {}
_PROVENANCE_STORE: Dict[str, List[dict]] = {}
_ATTESTATION_STORE: Dict[str, Attestation] = {}

class EvidenceService:
    """Manages evidence sources and data extraction."""

    def __init__(self):
        pass

    def get_all_sources(self) -> list[EvidenceSource]:
        # Return generic sources representing types
        return [
            EvidenceSource(
                id="generic_ledger",
                name="Transaction Ledger",
                source_type=TrustLevel.MERCHANT_UPLOADED,
                issuer="Untrusted Merchant Upload",
                format="PDF",
                fields=[
                    EvidenceField(name="amount", type="integer", relevant=True, sensitivity="high"),
                    EvidenceField(name="date", type="date", relevant=False, sensitivity="normal"),
                ],
                attestation_status="unattested",
                note="Untrusted data requiring ZK validation to preserve underlying privacy"
            )
        ]

    def get_source(self, source_id: str) -> Optional[EvidenceSource]:
        src = self.get_all_sources()[0]
        src.id = source_id # bind to actual upload ID so generator can find the transactions
        
        attestation = self.get_attestation(source_id)
        if attestation:
            src.source_type = TrustLevel.PROCESSOR_ATTESTED
            src.issuer = attestation.issuer
            src.attestation_status = "authenticated"
            src.note = "Cryptographically signed dataset. Human-readable PDF remains available."
            
        return src

    def store_attested_dataset(self, source_id: str, dataset: list[dict], attestation: Attestation):
        """Stores a pre-attested dataset directly, bypassing extraction."""
        _UPLOADED_EVIDENCE_STORE[source_id] = {"transactions": dataset}
        _ATTESTATION_STORE[source_id] = attestation

    def process_pdf_upload(self, file_path: str, evidence_id: str):
        """Extract transactions using pdfplumber and enforce bounds."""
        logger.info(f"Extracting evidence from PDF: {file_path}")
        
        transactions = []
        provenances = []
        
        try:
            with pdfplumber.open(file_path) as pdf:
                for page_idx, page in enumerate(pdf.pages):
                    table = page.extract_table()
                    if table:
                        df = pd.DataFrame(table[1:], columns=table[0])
                        df = df.dropna(how='all')
                        
                        # Simple heuristic strictly constrained
                        # Look for columns that might contain 'amount'
                        amount_col = None
                        for col in df.columns:
                            if 'amount' in str(col).lower() or 'credit' in str(col).lower():
                                amount_col = col
                                break
                                
                        if amount_col:
                            for row_idx, row in df.iterrows():
                                val = row[amount_col]
                                try:
                                    # Clean currency strings
                                    clean_val = str(val).replace(',', '').replace('₹', '').replace(' INR', '').strip()
                                    c_val = float(clean_val)
                                    
                                    transactions.append({
                                        "amount_raw": c_val,
                                        "amount_paisa": int(c_val * 100) # strict normalize for circuit
                                    })
                                    
                                    provenances.append({
                                        "value": int(c_val * 100),
                                        "currency": "INR",
                                        "source": {
                                            "document": Path(file_path).name,
                                            "table": 1,
                                            "row": row_idx,
                                            "column": str(amount_col)
                                        }
                                    })
                                except:
                                    pass
        except Exception as e:
            logger.error(f"pdfplumber error: {e}")
            raise HTTPException(status_code=400, detail="Failed to extract data from document.")
        
        if not transactions:
            raise HTTPException(status_code=400, detail="Could not detect transactional amounts in the document.")
            
        # ZK BOUNDS ENFORCEMENT
        # This explicit check ensures we don't silently truncate the user's data 
        # and pretend we proved 1000 rows when we only proved 16.
        if len(transactions) > 16:
            raise HTTPException(
                status_code=400, 
                detail=f"The current ProofBridge capacity is limited to 16 transactions. The document provided {len(transactions)} amounts."
            )
            
        _UPLOADED_EVIDENCE_STORE[evidence_id] = {"transactions": transactions}
        _PROVENANCE_STORE[evidence_id] = provenances
        
        return len(transactions)

    def load_evidence_data(self, source_id: str) -> Optional[dict]:
        """Load raw evidence data for proof generation."""
        # For demo purposes, we will return the dynamic one 
        if source_id in _UPLOADED_EVIDENCE_STORE:
            return _UPLOADED_EVIDENCE_STORE[source_id]
            
        # Fallback to local files if any (synthetic generator)
        ledger_path = DEMO_DIR / "evidence" / f"{source_id}.json"
        if ledger_path.exists():
            with open(ledger_path, "r") as f:
                return json.load(f)
                
        return None

    def get_provenance(self, source_id: str) -> List[dict]:
        return _PROVENANCE_STORE.get(source_id, [])
        
    def get_attestation(self, source_id: str) -> Optional[Attestation]:
        return _ATTESTATION_STORE.get(source_id)
        
    def attach_demo_attestation(self, source_id: str):
        """Builds and attaches a demo processor attestation to existing raw parsed data."""
        data = self.load_evidence_data(source_id)
        if not data:
            raise ValueError("No parsed dataset found to attest.")
            
        # We sign the parsed array exactly as it enters the system
        from app.services.attestation_service import attestation_service
        dataset = data.get("transactions", [])
        attestation = attestation_service.sign_dataset(source_id, dataset)
        _ATTESTATION_STORE[source_id] = attestation
        return attestation

    def compute_dataset_commitment(self, data: dict) -> str:
        canonical = json.dumps(data, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode()).hexdigest()

    def extract_amounts_for_circuit(self, parsed_data: dict, max_slots: int = 16) -> List[int]:
        """
        Extracts just the target numerical array for Poseidon/Groth16.
        Strictly raises an error if the array size exceeds the max capacity of the trusted setup.
        """
        dataset = parsed_data.get("transactions", [])
        if len(dataset) > max_slots:
            raise ValueError(f"UNSUPPORTED_DATASET_SIZE: Expected max {max_slots} eligible records.")
            
        amounts = []
        for row in dataset:
            amt = row.get("amount_paisa")
            if amt is not None:
                amounts.append(int(amt))
        
        while len(amounts) < max_slots:
            amounts.append(0)
            
        return amounts[:max_slots]

    def get_privacy_analysis(self, source_id: str) -> dict:
        data = self.load_evidence_data(source_id)
        total_records = 0
        if data and "transactions" in data:
            total_records = len(data["transactions"])

        return {
            "total_records": total_records,
            "sensitive_fields": 6,
            "field_disclosures_avoided": total_records * 6,
            "note": "Illustrative disclosure estimate preserving PII.",
        }
