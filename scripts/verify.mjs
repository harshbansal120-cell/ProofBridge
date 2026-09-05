/**
 * ProofBridge — ZK Verification Script
 * 
 * Standalone verifier that uses the same snarkjs mechanism as the backend.
 * Provides a clean `npm run verify` developer experience.
 * 
 * Usage:
 *   node scripts/verify.mjs [circuitName] [proof.json] [public.json]
 */

import * as snarkjs from 'snarkjs';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.join(__dirname, '..');
const CIRCUITS_DIR = path.join(ROOT, 'circuits');

/**
 * Verify a Groth16 proof
 */
async function verifyProof(circuitName, proof, publicSignals, vkeyPath) {
  if (!fs.existsSync(vkeyPath)) {
    throw new Error(`Verification key not found: ${vkeyPath}`);
  }

  const vkey = JSON.parse(fs.readFileSync(vkeyPath, 'utf-8'));
  const startTime = Date.now();
  const isValid = await snarkjs.groth16.verify(vkey, publicSignals, proof);
  const duration = Date.now() - startTime;

  return {
    valid: isValid,
    duration_ms: duration,
    circuit: circuitName,
    proving_system: 'groth16',
    curve: 'bn128'
  };
}

async function main() {
  const args = process.argv.slice(2);
  
  // Default to the main demo circuit and its test output if no args provided
  const circuitName = args[0] || 'sum_greater_than';
  const circuitDir = path.join(CIRCUITS_DIR, circuitName);
  
  const proofPath = args[1] || path.join(circuitDir, 'test_proof.json');
  const publicPath = args[2] || path.join(circuitDir, 'test_public.json');
  const vkeyPath = path.join(circuitDir, 'verification_key.json');

  if (!fs.existsSync(proofPath)) {
    console.error(`Proof file not found: ${proofPath}. Run 'npm run prove' or 'node scripts/test_pipeline.mjs' first.`);
    process.exit(1);
  }
  
  if (!fs.existsSync(publicPath)) {
    console.error(`Public signals file not found: ${publicPath}`);
    process.exit(1);
  }

  const proof = JSON.parse(fs.readFileSync(proofPath, 'utf-8'));
  const publicSignals = JSON.parse(fs.readFileSync(publicPath, 'utf-8'));

  console.log(`🔍 Verifying proof for circuit: ${circuitName}...`);
  console.log(`   Proof: ${proofPath}`);
  console.log(`   Public signals: ${publicPath}\n`);

  const result = await verifyProof(circuitName, proof, publicSignals, vkeyPath);
  
  console.log(JSON.stringify(result, null, 2));

  if (result.valid) {
    console.log('\n✅ PROOF VALID');
    process.exit(0);
  } else {
    console.log('\n❌ PROOF INVALID');
    process.exit(1);
  }
}

main().catch(err => {
  console.error(JSON.stringify({ status: 'error', error: err.message }));
  process.exit(1);
});
