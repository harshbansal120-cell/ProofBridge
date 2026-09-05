import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.services.semantic_filter_service import SemanticFilterService
from app.schemas.models import Claim, ClaimOperation, ClaimOperator

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    RESET = '\033[0m'

def print_result(name, passed, detail=""):
    color = Colors.GREEN if passed else Colors.RED
    status = "PASS" if passed else "FAIL"
    print(f"{color}[{status}] {name}{Colors.RESET}")
    if detail:
        print(f"       -> {detail}")

def run_tests():
    print("\n--- SEMANTIC FILTERING BOUNDARY TESTS ---")
    
    dataset = [
        {"merchant_id": "M1", "amount_paisa": 100000, "currency": "INR", "status": "SUCCESS", "timestamp": "2024-01-15T12:00:00Z"},
        {"merchant_id": "M1", "amount_paisa": 200000, "currency": "INR", "status": "FAILED", "timestamp": "2024-01-20T12:00:00Z"},
        {"merchant_id": "M2", "amount_paisa": 150000, "currency": "INR", "status": "SUCCESS", "timestamp": "2024-02-15T12:00:00Z"},
        {"merchant_id": "M1", "amount_paisa": 300000, "currency": "USD", "status": "SUCCESS", "timestamp": "2024-02-20T12:00:00Z"},
        {"merchant_id": "M1", "amount_paisa": 500000, "currency": "INR", "status": "SUCCESS", "timestamp": "2019-01-15T12:00:00Z"}, # Old
    ]
    
    # 1. Broad match
    c1 = Claim(
        id="c1", description="test", source_text="test",
        operation=ClaimOperation.SUM, field="amount", operator=ClaimOperator.GT, threshold=10,
        currency="INR", transaction_status="SUCCESS", merchant_scope="M1", confidence=1.0
    )
    
    try:
        filtered, stats = SemanticFilterService.apply_filters(dataset, c1)
        assert stats["rows_eligible"] == 2, f"Expected 2, got {stats['rows_eligible']}"
        assert filtered[0]["amount_paisa"] == 100000
        print_result("1. Currency, Status, and Merchant Filtering", True, "Successfully isolated 2 matching generic rows")
    except Exception as e:
        print_result("1. Currency, Status, and Merchant Filtering", False, str(e))
        
    # 2. Strict Period
    c2 = Claim(
        id="c2", description="test", source_text="test",
        operation=ClaimOperation.SUM, field="amount", operator=ClaimOperator.GT, threshold=10,
        currency="INR", transaction_status="SUCCESS", merchant_scope="M1", period="LAST_N_MONTHS", period_value=48, confidence=1.0
    )
    try:
        filtered, stats = SemanticFilterService.apply_filters(dataset, c2)
        # 500k row from 2019 should be dropped. Only 100k left.
        assert stats["rows_eligible"] == 1, f"Expected 1, got {stats['rows_eligible']}"
        assert filtered[0]["amount_paisa"] == 100000
        assert stats["exclusion_reasons"].get("OUT_OF_PERIOD", 0) >= 1
        print_result("2. Period Boundary Constraint", True, "Successfully dropped old 2019 row")
    except Exception as e:
        print_result("2. Period Boundary Constraint", False, str(e))
        
    print("\n")

if __name__ == "__main__":
    run_tests()
