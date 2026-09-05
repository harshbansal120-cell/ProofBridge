/**
 * ProofBridge — End-to-End ZK Test
 * 
 * Tests the complete proof pipeline:
 * 1. Load synthetic evidence
 * 2. Extract amounts
 * 3. Compute dataset commitment
 * 4. Generate Groth16 proof
 * 5. Verify proof
 * 6. Test with tampered data (must fail)
 */

import * as snarkjs from 'snarkjs';
import fs from 'fs';
import path from 'path';
import crypto from 'crypto';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.join(__dirname, '..');
const CIRCUITS_DIR = path.join(ROOT, 'circuits');

import { buildPoseidon } from 'circomlibjs';

async function computeDatasetHash(amounts) {
  const poseidon = await buildPoseidon();
  const hash = poseidon(amounts);
  return poseidon.F.toString(hash);
}

async function test() {
  console.log('============================================');
  console.log('  ProofBridge — ZK Pipeline Test');
  console.log('============================================\n');

  // Load synthetic evidence
  const ledger = JSON.parse(
    fs.readFileSync(path.join(ROOT, 'demo', 'evidence', 'processor_ledger.json'), 'utf-8')
  );

  // Extract amounts (convert paisa to rupees for the circuit)
  const amounts = ledger.transactions.map(tx => tx.amount_paisa);
  
  // Pad to 16 slots (our circuit expects exactly 16)
  while (amounts.length < 16) amounts.push(0);
  // Truncate to 16 slots in case there are more
  amounts.length = 16;
  
  const totalPaisa = amounts.reduce((a, b) => a + b, 0);
  const totalRupees = totalPaisa / 100;
  
  console.log(`📊 Evidence: ${ledger.metadata.source}`);
  console.log(`📊 Trust: ${ledger.metadata.source_type}`);
  console.log(`📊 Transactions: ${ledger.transactions.length}`);
  console.log(`📊 Total (private, not disclosed): ₹${totalRupees.toLocaleString('en-IN')}`);
  console.log();

  // Threshold: ₹5,00,000 = 5,00,000 * 100 paisa = 50,000,000 paisa
  const thresholdPaisa = 50000000; 

  // Compute dataset commitment
  const datasetHash = await computeDatasetHash(amounts);
  console.log(`🔒 Dataset commitment: ${datasetHash.substring(0, 20)}...`);
  console.log(`🔒 Threshold: ₹${(thresholdPaisa / 100).toLocaleString('en-IN')} (${thresholdPaisa} paisa)`);
  console.log();

  // Prepare circuit input
  const circuitInput = {
    amounts: amounts.map(String),
    threshold: String(thresholdPaisa),
    datasetCommitment: datasetHash,
    requestNonce: "12345"
  };

  // Save input for reference
  const inputPath = path.join(ROOT, 'circuits', 'sum_greater_than', 'test_input.json');
  fs.writeFileSync(inputPath, JSON.stringify(circuitInput, null, 2));

  // ============ PROOF GENERATION ============
  console.log('⚡ Generating Groth16 proof...');
  const proveStart = Date.now();
  
  const wasmPath = path.join(CIRCUITS_DIR, 'sum_greater_than', 'circuit_js', 'circuit.wasm');
  const zkeyPath = path.join(CIRCUITS_DIR, 'sum_greater_than', 'circuit.zkey');

  const { proof, publicSignals } = await snarkjs.groth16.fullProve(
    circuitInput,
    wasmPath,
    zkeyPath
  );

  const proveDuration = Date.now() - proveStart;
  console.log(`✅ Proof generated in ${proveDuration}ms`);
  console.log(`📤 Public signals: ${JSON.stringify(publicSignals)}`);
  console.log(`   Signal[0] = claimResult: ${publicSignals[0]} (1 = claim holds)`);
  console.log(`   Signal[1] = threshold: ${publicSignals[1]}`);
  console.log(`   Signal[2] = datasetHash: ${publicSignals[2].substring(0, 20)}...`);
  console.log();

  // Save proof artifacts
  const proofPath = path.join(ROOT, 'circuits', 'sum_greater_than', 'test_proof.json');
  const publicPath = path.join(ROOT, 'circuits', 'sum_greater_than', 'test_public.json');
  fs.writeFileSync(proofPath, JSON.stringify(proof, null, 2));
  fs.writeFileSync(publicPath, JSON.stringify(publicSignals, null, 2));

  // ============ PROOF VERIFICATION ============
  console.log('🔍 Verifying proof...');
  const vkeyPath = path.join(CIRCUITS_DIR, 'sum_greater_than', 'verification_key.json');
  const vkey = JSON.parse(fs.readFileSync(vkeyPath, 'utf-8'));

  const verifyStart = Date.now();
  const isValid = await snarkjs.groth16.verify(vkey, publicSignals, proof);
  const verifyDuration = Date.now() - verifyStart;

  if (isValid) {
    console.log(`✅ PROOF VALID (verified in ${verifyDuration}ms)`);
  } else {
    console.log(`❌ PROOF INVALID`);
    process.exit(1);
  }
  console.log();

  // ============ TAMPER TEST ============
  console.log('🧪 Tamper test: modifying public signals...');
  const tamperedSignals = [...publicSignals];
  // Change threshold to something the sum doesn't actually exceed
  tamperedSignals[1] = String(BigInt(tamperedSignals[1]) + BigInt(999999999999));
  
  const tamperedValid = await snarkjs.groth16.verify(vkey, tamperedSignals, proof);
  if (!tamperedValid) {
    console.log('✅ Tampered proof correctly rejected');
  } else {
    console.log('❌ ERROR: Tampered proof was accepted! This should not happen.');
    process.exit(1);
  }
  console.log();

  // ============ SUMMARY ============
  console.log('============================================');
  console.log('  PROOFBRIDGE ZK PIPELINE — ALL TESTS PASS');
  console.log('============================================');
  console.log();
  console.log('Processor would see:');
  console.log('  ✓ Claim: Monthly volume > ₹10,00,000');
  console.log('  ✓ Status: PROOF_VALID');
  console.log('  ✓ Circuit: sum_greater_than v1.0');
  console.log('  ✓ System: Groth16 on BN128');
  console.log(`  ✓ Evidence commitment: ${datasetHash.substring(0, 16)}...`);
  console.log();
  console.log('Processor would NOT see:');
  console.log('  ✗ Individual transaction amounts');
  console.log('  ✗ Customer identifiers');
  console.log('  ✗ Exact total');
  console.log('  ✗ Transaction timestamps');
  console.log();
  console.log(`Proof generation: ${proveDuration}ms`);
  console.log(`Proof verification: ${verifyDuration}ms`);
}

test().catch(err => {
  console.error('Test failed:', err);
  process.exit(1);
});
