#!/bin/bash
set -e

# ProofBridge — Artifact Regeneration Script
# Use this script when the circom environment is available to regenerate artifacts.

CIRCUIT_DIR="circuits/sum_greater_than"
PTAU_FILE="circuits/pot12_final.ptau"

echo "Compiling circuit v1.2.0..."
circom $CIRCUIT_DIR/circuit.circom --r1cs --wasm --sym --c -o $CIRCUIT_DIR

echo "Generating zkey..."
# We generate a Groth16 zkey for the circuit
# NOTE: In production a proper Phase 2 contribution is required.
npx snarkjs groth16 setup $CIRCUIT_DIR/circuit.r1cs $PTAU_FILE $CIRCUIT_DIR/circuit_0000.zkey
npx snarkjs zkey contribute $CIRCUIT_DIR/circuit_0000.zkey $CIRCUIT_DIR/circuit.zkey --name="First Contribution" -v -e="random text"
rm $CIRCUIT_DIR/circuit_0000.zkey

echo "Exporting verification key..."
npx snarkjs zkey export verificationkey $CIRCUIT_DIR/circuit.zkey $CIRCUIT_DIR/verification_key.json

echo "Generating hashes for registry.json..."
echo "r1cs_sha256: $(sha256sum $CIRCUIT_DIR/circuit.r1cs | awk '{print toupper($1)}') "
echo "wasm_sha256: $(sha256sum $CIRCUIT_DIR/circuit_js/circuit.wasm | awk '{print toupper($1)}')"
echo "zkey_sha256: $(sha256sum $CIRCUIT_DIR/circuit.zkey | awk '{print toupper($1)}')"
echo "verification_key_sha256: $(sha256sum $CIRCUIT_DIR/verification_key.json | awk '{print toupper($1)}')"

echo "✅ Artifacts generated. Update registry.json with these hashes."
