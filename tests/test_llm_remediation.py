"""
Unit tests for AegisLake Multi-Provider LLM Remediation Copilot
Verifies Google Gemini, Hugging Face Qwen 2.5 Coder, and Deterministic Fallback.
"""

import pytest
from unittest.mock import patch, MagicMock
from aegis_agent.tools.llm_remediation import generate_llm_remediation


def test_llm_remediation_fallback_when_no_token():
    """Verify that missing credentials trigger the deterministic fallback engine."""
    with patch.dict("os.environ", {}, clear=True):
        result = generate_llm_remediation(
            root_cause_table="stg_silver_authorizations",
            root_cause_column="raw_amount",
            expression="raw_amount * 100",
            break_payload={"authorization_id": "AUTH_004", "discrepancy_amount_scaled": -65.0},
        )

        assert result["provider"] == "deterministic_fallback"
        assert "UPDATE stg_silver_authorizations" in result["proposed_patch"]
        assert "AUTH_004" in result["proposed_patch"]
        assert "patch_rationale" in result


@patch("aegis_agent.tools.llm_remediation.genai.Client")
@patch("aegis_agent.tools.llm_remediation.GEMINI_AVAILABLE", True)
def test_llm_remediation_success_with_gemini(mock_gemini_client_cls):
    """Verify successful remediation patch using Google Gemini (e.g. gemini-2.5-flash)."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = '{"proposed_patch": "UPDATE stg_silver_authorizations SET auth_amount_minor = auth_amount_minor * 100 WHERE authorization_id = \'AUTH_004\';", "patch_rationale": "Corrected minor unit exponent via Gemini."}'
    mock_client.models.generate_content.return_value = mock_response
    mock_gemini_client_cls.return_value = mock_client

    with patch.dict("os.environ", {"GEMINI_API_KEY": "mock_gemini_key_123"}, clear=True):
        result = generate_llm_remediation(
            root_cause_table="stg_silver_authorizations",
            root_cause_column="auth_amount_minor",
            expression="auth_amount_minor / 100",
            break_payload={"authorization_id": "AUTH_004", "discrepancy_amount_scaled": -65.0},
            provider="gemini",
            model_name="gemini-2.5-flash",
        )

        assert result["provider"] == "gemini"
        assert result["model_name"] == "gemini-2.5-flash"
        assert "AUTH_004" in result["proposed_patch"]
        assert "via Gemini" in result["patch_rationale"]


@patch("aegis_agent.tools.llm_remediation.InferenceClient")
@patch("aegis_agent.tools.llm_remediation.HF_AVAILABLE", True)
def test_llm_remediation_success_with_hf_qwen(mock_inference_client_cls):
    """Verify successful remediation patch using Hugging Face Qwen 2.5 Coder 32B."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(
            message=MagicMock(
                content='{"proposed_patch": "UPDATE stg_silver_authorizations SET auth_amount_minor = auth_amount_minor WHERE authorization_id = \'AUTH_004\';", "patch_rationale": "Corrected minor unit exponent via Qwen."}'
            )
        )
    ]
    mock_client.chat_completion.return_value = mock_response
    mock_inference_client_cls.return_value = mock_client

    with patch.dict("os.environ", {"HF_TOKEN": "mock_hf_token_xyz"}, clear=True):
        result = generate_llm_remediation(
            root_cause_table="stg_silver_authorizations",
            root_cause_column="auth_amount_minor",
            expression="auth_amount_minor / 100",
            break_payload={"authorization_id": "AUTH_004", "discrepancy_amount_scaled": -65.0},
            provider="huggingface",
            model_name="Qwen/Qwen2.5-Coder-32B-Instruct",
        )

        assert result["provider"] == "huggingface"
        assert result["model_name"] == "Qwen/Qwen2.5-Coder-32B-Instruct"
        assert "AUTH_004" in result["proposed_patch"]
        assert "via Qwen" in result["patch_rationale"]
