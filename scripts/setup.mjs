/**
 * ProofBridge — Trusted Setup Script
 * 
 * Performs Powers of Tau ceremony and circuit-specific setup
 * for Groth16 proving system on BN128 curve.
 * 
 * This generates:
 *   - pot12_final.ptau  (Powers of Tau)
 *   - circuit.zkey      (proving key)
 *   - verification_key.json (verification key)
 */

import { execSync } from 'child_process';
import { existsSync } from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.join(__dirname, '..');
const CIRCUITS_DIR = path.join(ROOT, 'circuits');

function run(cmd, cwd = ROOT) {
  console.log(`> ${cmd}`);
  execSync(cmd, { cwd, stdio: 'inherit' });
}

async function setupCircuit(circuitName) {
  const dir = path.join(CIRCUITS_DIR, circuitName);
  const r1cs = path.join(dir, 'circuit.r1cs');
  const ptau = path.join(CIRCUITS_DIR, 'pot12_final.ptau');
  
  if (!existsSync(r1cs)) {
    console.error(`ERROR: ${r1cs} not found. Compile the circuit first.`);
    process.exit(1);
  }

  // Step 1: Powers of Tau (shared across circuits)
  if (!existsSync(ptau)) {
    console.log('\n=== Powers of Tau Ceremony ===');
    const pot12_0 = path.join(CIRCUITS_DIR, 'pot12_0000.ptau');
    const pot12_1 = path.join(CIRCUITS_DIR, 'pot12_0001.ptau');

    run(`npx snarkjs powersoftau new bn128 12 "${pot12_0}" -v`);
    // Contribute with deterministic entropy for reproducibility
    run(`npx snarkjs powersoftau contribute "${pot12_0}" "${pot12_1}" --name="ProofBridge Demo Setup" -v -e="proofbridge-demo-entropy-not-for-production"`);
    run(`npx snarkjs powersoftau prepare phase2 "${pot12_1}" "${ptau}" -v`);
    
    // Clean intermediate files
    try {
      const fs = await import('fs');
      fs.unlinkSync(pot12_0);
      fs.unlinkSync(pot12_1);
    } catch (e) { /* ignore cleanup errors */ }
    
    console.log('Powers of Tau ceremony complete.');
  } else {
    console.log('Powers of Tau file already exists, skipping.');
  }

  // Step 2: Circuit-specific setup
  console.log(`\n=== Setup for ${circuitName} ===`);
  const zkey0 = path.join(dir, 'circuit_0000.zkey');
  const zkey = path.join(dir, 'circuit.zkey');
  const vkey = path.join(dir, 'verification_key.json');

  run(`npx snarkjs groth16 setup "${r1cs}" "${ptau}" "${zkey0}"`);
  run(`npx snarkjs zkey contribute "${zkey0}" "${zkey}" --name="ProofBridge ${circuitName}" -v -e="proofbridge-${circuitName}-entropy-not-for-production"`);
  run(`npx snarkjs zkey export verificationkey "${zkey}" "${vkey}"`);

  // Clean intermediate zkey
  try {
    const fs = await import('fs');
    fs.unlinkSync(zkey0);
  } catch (e) { /* ignore */ }

  console.log(`\n✓ Setup complete for ${circuitName}`);
  console.log(`  Proving key: ${zkey}`);
  console.log(`  Verification key: ${vkey}`);
}

// Run setup for specified circuit or default
const circuitName = process.argv[2] || 'sum_greater_than';
setupCircuit(circuitName).catch(err => {
  console.error('Setup failed:', err);
  process.exit(1);
});
