"""
ProofBridge — Semantic Filter Service

Replaces LLM filtering with strict deterministic rules.
Takes the parsed authenticated canonical dataset and an instantiated Claim DSL, 
filtering out all rows that do not meet the constraints.
"""

from typing import Tuple, Dict, Any, List
from datetime import datetime, timezone
from dateutil.relativedelta import relativedelta
from app.schemas.models import Claim

class SemanticFilterService:

    @classmethod
    def apply_filters(cls, dataset: List[Dict[str, Any]], claim: Claim) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        rows_received = len(dataset)
        rows_eligible = 0
        exclusion_reasons = {
            "WRONG_CURRENCY": 0,
            "WRONG_STATUS": 0,
            "OUT_OF_PERIOD": 0,
            "WRONG_MERCHANT": 0,
            "MISSING_FIELDS": 0
        }
        
        filtered_dataset = []
        
        # Calculate time boundaries if a period is specified
        cutoff_date = None
        if claim.period == "LAST_N_MONTHS" and claim.period_value:
            cutoff_date = datetime.now(timezone.utc) - relativedelta(months=claim.period_value)
            
        for row in dataset:
            excluded = False
            
            # --- Currency Filter ---
            if claim.currency:
                if row.get("currency") != claim.currency:
                    exclusion_reasons["WRONG_CURRENCY"] += 1
                    excluded = True
                    continue
                    
            # --- Status Filter ---
            if claim.transaction_status:
                row_status = row.get("status") or row.get("transaction_status")
                if not row_status or str(row_status).upper() != str(claim.transaction_status).upper():
                    exclusion_reasons["WRONG_STATUS"] += 1
                    excluded = True
                    continue
                    
            # --- Merchant Scope Filter ---
            if claim.merchant_scope:
                # E.g. explicitly require merchant_id match
                if row.get("merchant_id") != claim.merchant_scope:
                    exclusion_reasons["WRONG_MERCHANT"] += 1
                    excluded = True
                    continue
            
            # --- Period Filter ---
            if cutoff_date:
                # We expect rows to have a "timestamp" or "date" field in ISO string
                ts_str = row.get("timestamp") or row.get("date")
                if not ts_str:
                    exclusion_reasons["MISSING_FIELDS"] += 1
                    excluded = True
                    continue
                    
                try:
                    # Clean simple dates
                    if "T" not in ts_str:
                        ts_str = ts_str + "T00:00:00Z"
                    if not ts_str.endswith("Z"):
                        ts_str = ts_str.replace("+00:00", "") + "Z"
                        
                    row_date = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
                    if row_date < cutoff_date:
                        exclusion_reasons["OUT_OF_PERIOD"] += 1
                        excluded = True
                        continue
                except Exception:
                    exclusion_reasons["MISSING_FIELDS"] += 1
                    excluded = True
                    continue

            # Ensure amount exists
            if row.get("amount_paisa") is None:
                exclusion_reasons["MISSING_FIELDS"] += 1
                excluded = True
                continue

            if not excluded:
                filtered_dataset.append(row)
                rows_eligible += 1
                
        # To avoid revealing raw underlying data unconditionally in logs/UI, cap exclusion reasons reporting
        ex_reasons_filtered = {k: v for k,v in exclusion_reasons.items() if v > 0}
        
        return filtered_dataset, {
            "status": "VALID",
            "rows_received": rows_received,
            "rows_eligible": rows_eligible,
            "rows_excluded": rows_received - rows_eligible,
            "exclusion_reasons": ex_reasons_filtered
        }
