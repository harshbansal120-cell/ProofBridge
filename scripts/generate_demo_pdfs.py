from fpdf import FPDF
from pathlib import Path
import random

demo_dir = Path(__file__).parent.parent / "backend/app/demo_evidence"
demo_dir.mkdir(parents=True, exist_ok=True)

def generate_ledger(filename, tx_count, sum_target_below=False):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    pdf.cell(200, 10, txt="Merchant Processing Ledger", ln=1, align='C')
    pdf.cell(200, 10, txt=f"Generated for ProofBridge Technical Demonstration", ln=1, align='C')
    
    pdf.ln(10)
    pdf.set_font("Helvetica", style="B", size=10)
    
    # Header
    pdf.cell(40, 10, "Transaction ID", border=1)
    pdf.cell(40, 10, "Date", border=1)
    pdf.cell(50, 10, "Amount", border=1)
    pdf.cell(40, 10, "Currency", border=1)
    pdf.ln()
    
    pdf.set_font("Helvetica", size=10)
    
    total = 0
    amounts = [80000, 95000, 110000, 125000, 65000, 100000, 50000]
    
    for i in range(tx_count):
        if sum_target_below:
            amt = random.randint(10000, 30000)
        else:
            amt = amounts[i % len(amounts)] + random.randint(0, 5000)
            
        pdf.cell(40, 10, f"TXN{i:04d}", border=1)
        pdf.cell(40, 10, f"2026-09-{random.randint(1, 30):02d}", border=1)
        pdf.cell(50, 10, str(amt), border=1)
        pdf.cell(40, 10, "INR", border=1)
        pdf.ln()
        total += amt
        
    pdf.ln(10)
    pdf.set_font("Helvetica", style="B", size=12)
    pdf.cell(200, 10, txt=f"Total Extracted Value: {total} INR", ln=1)
    
    outpath = demo_dir / filename
    pdf.output(outpath)
    print(f"Generated {outpath} (Total = {total})")

if __name__ == "__main__":
    # Max size is 16 rows
    generate_ledger("demo_merchant_ledger.pdf", 14, sum_target_below=False)
    generate_ledger("demo_merchant_ledger_below_threshold.pdf", 14, sum_target_below=True)
    generate_ledger("demo_merchant_ledger_oversize.pdf", 25, sum_target_below=False)
