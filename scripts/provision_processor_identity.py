import os
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization

def provision_keys():
    ROOT = Path(__file__).parent.parent
    
    config_dir = ROOT / "backend" / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    
    pub_path = config_dir / "demo_processor_public_key.pem"
    priv_path = ROOT / "backend" / ".demo_processor_private_key.pem"
    
    if pub_path.exists() and priv_path.exists():
        print("Keys already provisioned. Skipping.")
        return
        
    print("Generating pre-provisioned Demo Processor Ed25519 keys...")
    private_key = ed25519.Ed25519PrivateKey.generate()
    
    with open(priv_path, "wb") as f:
        f.write(private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ))
        
    with open(pub_path, "wb") as f:
        f.write(private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ))
        
    # Append to gitignore if not present
    gitignore = ROOT / ".gitignore"
    if gitignore.exists():
        with open(gitignore, "a+") as f:
            f.seek(0)
            content = f.read()
            if ".demo_processor_private_key.pem" not in content:
                f.write("\n.demo_processor_private_key.pem\n")
    
    print(f"Public key written to {pub_path.relative_to(ROOT)} (can be committed)")
    print(f"Private key written to {priv_path.relative_to(ROOT)} (ignored)")

if __name__ == "__main__":
    provision_keys()
