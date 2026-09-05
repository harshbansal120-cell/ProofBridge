/**
 * ProofBridge — ZK Proof Engine
 * 
 * Generates and verifies Groth16 proofs using snarkjs.
 * 
 * Usage:
 *   node scripts/prove.mjs <circuitName> <inputJsonPath> [outputDir]
 *   node scripts/prove.mjs --verify <circuitName> <proofPath> <publicPath>
 * 
 * This is the ONLY file that invokes snarkjs cryptographic operations.
 * It is called as a subprocess by the Python backend.
 * The backend NEVER generates circuits — only uses pre-registered ones.
 */

import * as snarkjs from 'snarkjs';
import fs from 'fs';
import path from 'path';
import crypto from 'crypto';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.join(__dirname, '..');
const CIRCUITS_DIR = path.join(ROOT, 'circuits');

/**
 * Compute SHA-256 hash of canonical input data,
 * truncated to fit BN128 scalar field (253 bits).
 */
function computeDatasetHash(data) {
  const canonical = JSON.stringify(data, Object.keys(data).sort());
  const fullHash = crypto.createHash('sha256').update(canonical).digest('hex');
  // Truncate to 253 bits (BN128 scalar field is ~254 bits)
  // Take first 63 hex chars (252 bits) to be safe
  const truncated = fullHash.substring(0, 63);
  return BigInt('0x' + truncated).toString();
}

/**
 * Generate a Groth16 proof
 */
async function generateProof(circuitName, inputData, wasmPath, zkeyPath) {

  if (!fs.existsSync(wasmPath)) {
    throw new Error(`Circuit WASM not found: ${wasmPath}`);
  }
  if (!fs.existsSync(zkeyPath)) {
    throw new Error(`Proving key not found: ${zkeyPath}`);
  }

  const startTime = Date.now();
  const { proof, publicSignals } = await snarkjs.groth16.fullProve(
    inputData,
    wasmPath,
    zkeyPath
  );
  const duration = Date.now() - startTime;

  return {
    proof,
    publicSignals,
    duration_ms: duration,
    circuit: circuitName,
    proving_system: 'groth16',
    curve: 'bn128'
  };
}

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

// === CLI Interface ===
async function main() {
  const args = process.argv.slice(2);

  if (args[0] === '--verify') {
    // Verification mode
    const circuitName = args[1];
    const proofPath = args[2];
    const publicPath = args[3];
    const vkeyPath = args[4];

    if (!circuitName || !proofPath || !publicPath || !vkeyPath) {
      console.error('Usage: node prove.mjs --verify <circuit> <proof.json> <public.json> <vkeyPath>');
      process.exit(1);
    }

    const proof = JSON.parse(fs.readFileSync(proofPath, 'utf-8'));
    const publicSignals = JSON.parse(fs.readFileSync(publicPath, 'utf-8'));

    const result = await verifyProof(circuitName, proof, publicSignals, vkeyPath);
    console.log(JSON.stringify(result));
    process.exit(result.valid ? 0 : 1);

  } else if (args[0] === '--prove') {
    // Proving mode
    const circuitName = args[1];
    const inputPath = args[2];
    const wasmPath = args[3];
    const zkeyPath = args[4];
    const outputDir = args[5] || '.';

    if (!circuitName || !inputPath || !wasmPath || !zkeyPath) {
      console.error('Usage: node prove.mjs --prove <circuit> <input.json> <wasmPath> <zkeyPath> [outputDir]');
      process.exit(1);
    }

    const inputData = JSON.parse(fs.readFileSync(inputPath, 'utf-8'));
    const result = await generateProof(circuitName, inputData, wasmPath, zkeyPath);

    // Write outputs
    const proofPath = path.join(outputDir, 'proof.json');
    const publicPath = path.join(outputDir, 'public.json');
    fs.writeFileSync(proofPath, JSON.stringify(result.proof, null, 2));
    fs.writeFileSync(publicPath, JSON.stringify(result.publicSignals, null, 2));

    console.log(JSON.stringify({
      status: 'success',
      proof_path: proofPath,
      public_path: publicPath,
      duration_ms: result.duration_ms,
      circuit: result.circuit,
      proving_system: result.proving_system,
      curve: result.curve,
      public_signals: result.publicSignals
    }));
    process.exit(0);

  } else if (args[0] === '--hash') {
    // Dataset hash mode
    const dataPath = args[1];
    if (!dataPath) {
      console.error('Usage: node prove.mjs --hash <data.json>');
      process.exit(1);
    }
    const data = JSON.parse(fs.readFileSync(dataPath, 'utf-8'));
    const hash = computeDatasetHash(data);
    console.log(JSON.stringify({ datasetHash: hash }));
    process.exit(0);

  } else {
    console.error('Usage:');
    console.error('  node prove.mjs --prove <circuit> <input.json> [outputDir]');
    console.error('  node prove.mjs --verify <circuit> <proof.json> <public.json>');
    console.error('  node prove.mjs --hash <data.json>');
    process.exit(1);
  }
}

main().catch(err => {
  console.error(JSON.stringify({ status: 'error', error: err.message }));
  process.exit(1);
});
