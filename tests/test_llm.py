import json
from unittest.mock import MagicMock, patch
import pytest
from config import Config
from llm import score_tool_severity, generate_executive_summary, build_tool_summaries


SAMPLE_TOOL_SUMMARY = {
    "tool_id": "T1",
    "counts": {"added": 1, "removed": 0, "changed": 2, "unchanged": 10},
    "changed_fields": [
        {"ben": "T1", "part": "P1", "field": "Qty", "old": 5, "new": 10}
    ],
}


def test_score_tool_severity_returns_unscored_when_llm_disabled():
    config = Config(llm_enabled=False)
    result = score_tool_severity(SAMPLE_TOOL_SUMMARY, config)
    assert result["tool_id"] == "T1"
    assert result["severity"] == "UNSCORED"


def test_score_tool_severity_returns_unscored_on_json_parse_failure():
    config = Config(llm_enabled=True, llm_model="test-model")
    mock_response = MagicMock()
    mock_response.choices[0].message.content = "NOT VALID JSON {{{"
    with patch("llm.get_openai_client") as mock_client:
        mock_client.return_value.chat.completions.create.return_value = mock_response
        result = score_tool_severity(SAMPLE_TOOL_SUMMARY, config)
    assert result["severity"] == "UNSCORED"


def test_score_tool_severity_returns_unscored_on_connection_error():
    config = Config(llm_enabled=True, llm_model="test-model")
    with patch("llm.get_openai_client") as mock_client:
        mock_client.return_value.chat.completions.create.side_effect = Exception("connection refused")
        result = score_tool_severity(SAMPLE_TOOL_SUMMARY, config)
    assert result["severity"] == "UNSCORED"


def test_score_tool_severity_returns_valid_severity():
    config = Config(llm_enabled=True, llm_model="test-model")
    mock_response = MagicMock()
    mock_response.choices[0].message.content = json.dumps({
        "tool_id": "T1",
        "severity": "HIGH",
        "note": "Critical date changes detected"
    })
    with patch("llm.get_openai_client") as mock_client:
        mock_client.return_value.chat.completions.create.return_value = mock_response
        result = score_tool_severity(SAMPLE_TOOL_SUMMARY, config)
    assert result["severity"] == "HIGH"
    assert result["tool_id"] == "T1"
    assert "note" in result


def test_score_tool_severity_handles_invalid_severity_value():
    config = Config(llm_enabled=True, llm_model="test-model")
    mock_response = MagicMock()
    mock_response.choices[0].message.content = json.dumps({
        "tool_id": "T1",
        "severity": "EXTREME",
        "note": "bad value"
    })
    with patch("llm.get_openai_client") as mock_client:
        mock_client.return_value.chat.completions.create.return_value = mock_response
        result = score_tool_severity(SAMPLE_TOOL_SUMMARY, config)
    assert result["severity"] == "UNSCORED"


def test_generate_executive_summary_returns_unavailable_when_disabled():
    config = Config(llm_enabled=False)
    result = generate_executive_summary([], config)
    assert result == "[LLM UNAVAILABLE]"


def test_generate_executive_summary_returns_unavailable_on_error():
    config = Config(llm_enabled=True, llm_model="test-model")
    with patch("llm.get_openai_client") as mock_client:
        mock_client.return_value.chat.completions.create.side_effect = Exception("timeout")
        result = generate_executive_summary([], config)
    assert result == "[LLM UNAVAILABLE]"


def test_build_tool_summaries_uses_config_column_names():
    import pandas as pd
    from diff import compute_diff, group_by_ben

    config = Config(ben_column="Tool", part_number_column="PN")
    df_a = pd.DataFrame({"Tool": ["T1"], "PN": ["P1"], "Qty": [5]})
    df_b = pd.DataFrame({"Tool": ["T1"], "PN": ["P1"], "Qty": [10]})
    diff_result = compute_diff(df_a, df_b, config)
    groups = group_by_ben(diff_result, config, tool_order=[])
    summaries = build_tool_summaries(groups, "0312", "0401")
    assert summaries[0]["tool_id"] == "T1"
    assert summaries[0]["counts"]["changed"] == 1
    assert summaries[0]["changed_fields"][0]["ben"] == "T1"
    assert summaries[0]["changed_fields"][0]["part"] == "P1"
