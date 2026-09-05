$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

$CIRCUIT_DIR = "circuits/sum_greater_than"
$BUILD_DIR = "circuits/build_tmp"
$PTAU_FILE = "circuits/pot12_final.ptau"

$CIRCOM_EXE = "$env:TEMP\circom_2.1.8.exe"
$EXPECTED_HASH = "09BE6611B4956707F00DC679158AABCD41D8667A2E38A589C6501BCAE4514375"

if (-Not (Test-Path $CIRCOM_EXE)) {
    Write-Host "Downloading circom v2.1.8..."
    Invoke-WebRequest -Uri "https://github.com/iden3/circom/releases/download/v2.1.8/circom-windows-amd64.exe" -OutFile $CIRCOM_EXE
}

$hash = (Get-FileHash $CIRCOM_EXE -Algorithm SHA256).Hash
if ($hash -ne $EXPECTED_HASH) {
    Write-Error "Hash mismatch for circom.exe! Expected $EXPECTED_HASH but got $hash"
    exit 1
}
Write-Host "Circom binary verified (SHA-256: $hash)"

# Create build_tmp
if (Test-Path $BUILD_DIR) {
    Remove-Item -Recurse -Force $BUILD_DIR
}
New-Item -ItemType Directory -Force -Path $BUILD_DIR | Out-Null

Write-Host "Compiling circuit into $BUILD_DIR..."
Copy-Item "$CIRCUIT_DIR/circuit.circom" -Destination "$BUILD_DIR/"

& $CIRCOM_EXE "$BUILD_DIR/circuit.circom" --r1cs --wasm --sym -o $BUILD_DIR

if ($LASTEXITCODE -ne 0) {
    Write-Error "Circom compilation failed."
    exit 1
}

Write-Host "Generating Groth16 zkey in $BUILD_DIR..."
# Need to use local node_modules snarkjs or npx
# Using 'npx' directly
& npx snarkjs groth16 setup "$BUILD_DIR/circuit.r1cs" "$PTAU_FILE" "$BUILD_DIR/circuit_0000.zkey"
& npx snarkjs zkey contribute "$BUILD_DIR/circuit_0000.zkey" "$BUILD_DIR/circuit.zkey" --name="First Contribution" -v -e="random text"
Remove-Item "$BUILD_DIR/circuit_0000.zkey"

Write-Host "Exporting verification key..."
& npx snarkjs zkey export verificationkey "$BUILD_DIR/circuit.zkey" "$BUILD_DIR/verification_key.json"

Write-Host "Compilation complete in build_tmp."
Write-Host "Run the boundary tests against 'build_tmp'. If they pass, move artifacts to sum_greater_than."
