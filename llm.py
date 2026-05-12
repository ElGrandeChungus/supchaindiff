import json
import logging
from pathlib import Path
from typing import Any, Dict, List

from openai import OpenAI

from config import Config

logger = logging.getLogger(__name__)

_VALID_SEVERITIES = {"HIGH", "MEDIUM", "LOW", "NONE"}


def get_openai_client(config: Config) -> OpenAI:
    return OpenAI(
        base_url=config.llm_base_url,
        api_key=config.llm_api_key,
        timeout=float(config.llm_timeout_seconds),
    )


def score_tool_severity(tool_summary: Dict[str, Any], config: Config) -> Dict[str, Any]:
    """Score one tool. Returns {tool_id, severity, note}. Falls back to UNSCORED on any error."""
    tool_id = tool_summary["tool_id"]
    fallback = {"tool_id": tool_id, "severity": "UNSCORED", "note": ""}

    if not config.llm_enabled:
        return {**fallback, "note": "LLM disabled"}

    try:
        client = get_openai_client(config)
        prompt = _load_prompt("prompts/severity.txt").replace(
            "{{TOOL_JSON}}", json.dumps(tool_summary, indent=2, default=str)
        )
        response = client.chat.completions.create(
            model=config.llm_model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
        )
        parsed = json.loads(response.choices[0].message.content)
        severity = parsed.get("severity", "UNSCORED")
        if severity not in _VALID_SEVERITIES:
            severity = "UNSCORED"
        return {"tool_id": tool_id, "severity": severity, "note": parsed.get("note", "")}
    except Exception as exc:
        logger.warning("LLM severity scoring failed for %s: %s", tool_id, exc)
        return fallback


def generate_executive_summary(
    all_summaries: List[Dict[str, Any]], config: Config
) -> str:
    """Generate plain-text executive summary. Returns [LLM UNAVAILABLE] on any error."""
    if not config.llm_enabled:
        return "[LLM UNAVAILABLE]"

    try:
        client = get_openai_client(config)
        prompt = _load_prompt("prompts/summary.txt").replace(
            "{{SUMMARIES_JSON}}", json.dumps(all_summaries, indent=2, default=str)
        )
        response = client.chat.completions.create(
            model=config.llm_model,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content
    except Exception as exc:
        logger.warning("LLM executive summary failed: %s", exc)
        return "[LLM UNAVAILABLE]"


def build_tool_summaries(
    groups: Dict[str, Dict[str, Any]], date_a: str, date_b: str
) -> List[Dict[str, Any]]:
    """Build the structured JSON object passed to LLM calls (spec §5.2)."""
    summaries = []
    for ben, group in groups.items():
        summaries.append(
            {
                "tool_id": ben,
                "counts": {
                    "added": len(group["added"]),
                    "removed": len(group["removed"]),
                    "changed": len(group["changed_b"]),
                    "unchanged": len(group["unchanged"]),
                },
                "changed_fields": group["field_diffs"],
            }
        )
    return summaries


def _load_prompt(path: str) -> str:
    resolved = Path(__file__).parent / path
    with open(resolved, encoding="utf-8") as f:
        return f.read()
