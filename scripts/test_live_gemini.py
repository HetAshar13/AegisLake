"""
Interactive Live Test: Google Gemini Remediation Copilot
Tests live API connectivity and SQL patch generation using your Google AI Studio API key.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Ensure 'src' is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

# UTF-8 stdout encoding for Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

# Load .env file
load_dotenv()

from aegis_agent.tools.llm_remediation import generate_llm_remediation

def main():
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    active_model = os.getenv("AEGIS_GEMINI_MODEL", "gemini-3.5-flash-lite")

    print("=" * 65)
    print("🛡️  AegisLake: Live Google Gemini Integration Test")
    print("=" * 65)

    if not api_key:
        print("\n❌ No GEMINI_API_KEY found in your environment or .env file.")
        print("To test live Gemini connectivity:")
        print("1. Create a file named '.env' in your project root.")
        print("2. Add this line: GEMINI_API_KEY=\"your_key_here\"")
        print("3. Optional: Add AEGIS_GEMINI_MODEL=\"gemini-2.5-flash\" (or your preferred model)")
        print("\nRunning in deterministic fallback mode...\n")
    else:
        # Mask the key for security display
        masked_key = api_key[:6] + "..." + api_key[-4:]
        print(f"\n✅ GEMINI_API_KEY detected: {masked_key}")
        print(f"🎯 Target Model: {active_model}\n")

    # Sample context from our actual lakehouse break (AUTH_004)
    sample_context = {
        "root_cause_table": "stg_silver_authorizations",
        "root_cause_column": "auth_amount_minor",
        "expression": "raw_amount * 100",
        "break_payload": {
            "authorization_id": "AUTH_004",
            "currency": "EUR",
            "reconciliation_status": "BREAK_UNMATCHED_AUTHORIZATION",
            "discrepancy_amount_scaled": -65.0,
            "auth_amount_minor": 6500,
            "settled_amount_minor": 0
        }
    }

    print("📡 Sending AST lineage context to Remediation Copilot...")
    result = generate_llm_remediation(
        root_cause_table=sample_context["root_cause_table"],
        root_cause_column=sample_context["root_cause_column"],
        expression=sample_context["expression"],
        break_payload=sample_context["break_payload"],
        provider="gemini" if api_key else None,
        model_name=active_model
    )

    print("\n" + "=" * 65)
    print(f"🎯 Provider:   {result['provider'].upper()}")
    print(f"🤖 Model:      {result['model_name']}")
    print("-" * 65)
    print("🛠️  Proposed SQL Patch:")
    print(result["proposed_patch"])
    print("-" * 65)
    print("📋 Engineering Rationale:")
    print(result["patch_rationale"])
    print("=" * 65)

if __name__ == "__main__":
    main()
