pragma circom 2.0.0;

include "../../node_modules/circomlib/circuits/poseidon.circom";
include "../../node_modules/circomlib/circuits/comparators.circom";
include "../../node_modules/circomlib/circuits/bitify.circom";

/*
 * ProofBridge — SUM_GREATER_THAN Circuit (v1.2.0)
 *
 * Proves: SUM(amounts[0..N-1]) > threshold
 *
 * Private inputs (witness):
 *   - amounts[N]: array of transaction amounts (integers, scaled circuit units)
 *
 * Public inputs:
 *   - threshold: the value the sum must exceed
 *   - datasetCommitment: Poseidon hash of the canonical dataset
 *   - requestNonce: Random nonce uniquely binding this proof to a specific session
 *
 * Public outputs:
 *   - claimResult: 1 if SUM > threshold, 0 otherwise
 *
 * Note: N is fixed at compile time (16 natively supported by single Poseidon hash).
 * Updates v1.2: Enforces strict > inequality. Validates 64-bit range per tx to prevent aggregate sum
 * overflow (aggregate bounded to 68 bits).
 */

template SumGreaterThan(N) {
    // Input sizes strictly bounded to 16 for demo due to single Poseidon leaf limitations
    assert(N <= 16);

    // Private inputs
    signal input amounts[N];

    // Public inputs
    signal input threshold;
    signal input datasetCommitment;
    signal input requestNonce;

    // Public output
    signal output claimResult;

    // 1. DATASET BINDING - Cryptographically enforce the witness against the public commitment
    component poseidon = Poseidon(N);
    for (var i = 0; i < N; i++) {
        poseidon.inputs[i] <== amounts[i];
    }
    datasetCommitment === poseidon.out;

    // 2. REQUEST BINDING (REPLAY MITIGATION)
    // The requestNonce is a public input, so the prover cannot fake the Groth16 proof 
    // for a different session. We constrain it to ensure the compiler doesn't optimize it out.
    signal requestNonceSquared;
    requestNonceSquared <== requestNonce * requestNonce;

    // 3. SECURE PREDICATE LOGIC
    // 3a. Range check inputs: each amount must be a 64-bit uint to prevent sum overflow
    component num2bits_amt[N];
    for (var i = 0; i < N; i++) {
        num2bits_amt[i] = Num2Bits(64);
        num2bits_amt[i].in <== amounts[i];
    }
    
    // 3b. Range check threshold (allowed up to 68 bits because sum of 16 uint64s can be 68 bits)
    component num2bits_thr = Num2Bits(68);
    num2bits_thr.in <== threshold;

    // 3c. Compute sum
    signal sums[N + 1];
    sums[0] <== 0;
    for (var i = 0; i < N; i++) {
        sums[i + 1] <== sums[i] + amounts[i];
    }
    signal totalSum;
    totalSum <== sums[N];

    // 4. STRICT INEQUALITY VERIFICATION
    // We use GreaterThan(68) because the maximum value of totalSum is 16 * (2^64 - 1) < 2^68.
    component gt = GreaterThan(68);
    gt.in[0] <== totalSum;
    gt.in[1] <== threshold;
    gt.out === 1;

    // If we reach here, totalSum > threshold holds.
    claimResult <== 1;
}

// Instantiate with N=16 transaction slots
component main {public [threshold, datasetCommitment, requestNonce]} = SumGreaterThan(16);
