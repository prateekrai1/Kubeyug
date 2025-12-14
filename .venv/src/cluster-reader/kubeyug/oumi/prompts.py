import json
from typing import Any


# Keep the output schema stable; your CLI/installer depends on it.
DECISION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "chartKey": {"type": "string"},
        "reason": {"type": "string"},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
    },
    "required": ["chartKey", "reason"],
}


def build_tool_selection_prompt(
    *,
    goal: str,
    cluster_summary: dict[str, Any],
    tools: list[dict[str, Any]],
    max_reason_sentences: int = 2,
) -> str:
    """
    Returns a single prompt string. The model should output ONLY a JSON object.

    NOTE: avoid passing shell commands in tools; pass metadata only (helm chart, namespace, constraints).
    """
    allowed_keys = [t.get("key") for t in tools if t.get("key")]
    tool_summaries = [
        {
            "key": t.get("key"),
            "name": t.get("name"),
            "category": t.get("category"),          # optional if you store it
            "namespace": t.get("namespace"),
            "helm_chart": t.get("helm_chart"),
            "strengths": t.get("strengths"),        # optional
            "requirements": t.get("requirements"),  # optional
        }
        for t in tools
    ]

    # Everything the model needs is in one JSON input blob to reduce ambiguity. [web:575]
    input_blob = {
        "goal": goal,
        "cluster_summary": cluster_summary,
        "allowed_tool_keys": allowed_keys,
        "tools": tool_summaries,
        "output_schema": DECISION_SCHEMA,
        "constraints": {
            "json_only": True,
            "reason_sentences_max": max_reason_sentences,
            "chartKey_must_be_in_allowed_tool_keys": True,
        },
    }

    return (
        "You are Kubeyug, a Kubernetes add-on installer planner.\n"
        "Task: choose the best tool for the goal given the cluster summary.\n"
        "Rules:\n"
        "1) Output ONLY a JSON object. No markdown, no prose.\n"
        "2) chartKey must be one of allowed_tool_keys.\n"
        f"3) reason must be <= {max_reason_sentences} sentences.\n"
        "4) If information is insufficient, pick the simplest safe default from allowed_tool_keys.\n"
        "\n"
        f"INPUT:\n{json.dumps(input_blob, ensure_ascii=False)}\n"
    )


def build_monitoring_prompt(cluster_summary: dict[str, Any], tools: list[dict[str, Any]]) -> str:
    return build_tool_selection_prompt(
        goal="monitoring",
        cluster_summary=cluster_summary,
        tools=tools,
        max_reason_sentences=2,
    )
