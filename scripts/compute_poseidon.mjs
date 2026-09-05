import { buildPoseidon } from "circomlibjs";

async function main() {
    const args = process.argv.slice(2);
    if (!args[0]) {
        console.error("Missing amounts JSON");
        process.exit(1);
    }
    const amounts = JSON.parse(args[0]);

    if (amounts.length > 16) {
        console.error("Poseidon expects max 16 amounts for this circuit.");
        process.exit(1);
    }
    
    // Pad to 16 if necessary so the circuit hash matches exactly
    const paddedAmounts = [...amounts];
    while (paddedAmounts.length < 16) {
        paddedAmounts.push(0);
    }

    const poseidon = await buildPoseidon();
    
    // Convert array to BigInts if needed by poseidon
    const F = poseidon.F;
    const hash = poseidon(paddedAmounts);
    const hashString = F.toString(hash);

    console.log(hashString);
}

main().catch(err => {
    console.error(err);
    process.exit(1);
});
