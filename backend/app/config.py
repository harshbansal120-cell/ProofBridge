"""
ProofBridge — Configuration
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Paths
ROOT_DIR = Path(__file__).parent.parent.parent  # proofbridge/
CIRCUITS_DIR = ROOT_DIR / "circuits"
DEMO_DIR = ROOT_DIR / "demo"
SCRIPTS_DIR = ROOT_DIR / "scripts"

# Server
BACKEND_HOST = os.getenv("BACKEND_HOST", "0.0.0.0")
BACKEND_PORT = int(os.getenv("BACKEND_PORT", "18080"))

# AI & LLM Provider Config
AI_MODE = os.getenv("AI_MODE", "demo").lower()  # Expected: demo, gemini, open_source, ensemble

# Gemini Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

# OpenRouter Configuration
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "")  # Must be explicitly configured in production


# Open Source / Ollama Configuration
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

# RegTech-7B-Instruct is the preferred domain-specific model for regulatory/financial claims
PROOFBRIDGE_MODEL_REGTECH = os.getenv("PROOFBRIDGE_MODEL_REGTECH", "a-ivanovitch/RegTech-7B-Instruct")
PROOFBRIDGE_MODEL_FALLBACK = os.getenv("PROOFBRIDGE_MODEL_FALLBACK", "qwen:0.5b")

PROOFBRIDGE_INTENT_MODEL = os.getenv("PROOFBRIDGE_INTENT_MODEL", PROOFBRIDGE_MODEL_FALLBACK)
PROOFBRIDGE_CLAIM_MODEL = os.getenv("PROOFBRIDGE_CLAIM_MODEL", PROOFBRIDGE_MODEL_FALLBACK)
PROOFBRIDGE_EVIDENCE_MODEL = os.getenv("PROOFBRIDGE_EVIDENCE_MODEL", PROOFBRIDGE_MODEL_FALLBACK)
PROOFBRIDGE_PRIVACY_MODEL = os.getenv("PROOFBRIDGE_PRIVACY_MODEL", PROOFBRIDGE_MODEL_FALLBACK)
PROOFBRIDGE_CRITIC_MODEL = os.getenv("PROOFBRIDGE_CRITIC_MODEL", PROOFBRIDGE_MODEL_FALLBACK)

# Experimental Integrations
ENABLE_OUTLINES = os.getenv("ENABLE_OUTLINES", "false").lower() == "true"
ENABLE_DOCLING = os.getenv("ENABLE_DOCLING", "false").lower() == "true"

# Demo
DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() == "true"

# Cryptographic Registry
TRUSTED_ISSUERS = {
    "DEMO_PROCESSOR": {
        "key_id": "demo-processor-ed25519-v1",
        "algorithm": "Ed25519",
        "public_key_path": str(ROOT_DIR / "backend" / "config" / "demo_processor_public_key.pem"),
    }
}

# Frontend
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

# Database
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite+aiosqlite:///{ROOT_DIR / 'proofbridge.db'}")

# Node.js path for snarkjs
NODE_EXECUTABLE = os.getenv("NODE_EXECUTABLE", "node")
