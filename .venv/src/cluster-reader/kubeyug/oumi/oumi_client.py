import json
import os
from dataclasses import dataclass
from typing import Any

from oumi.core.types import Conversation, Message, Role
from oumi.core.configs import InferenceConfig, ModelParams, GenerationParams
from oumi.inference import OpenAIInferenceEngine

from kubeyug.oumi.prompts import build_tool_selection_prompt


@dataclass
class OumiClientConfig:
    """
    Minimal config for an OpenAI-compatible endpoint (could be OpenAI, vLLM OpenAI server, etc.).
    Read from env so the CLI remains self-contained.
    """
    model: str = os.getenv("KUBEYUG_LLM_MODEL", "gpt-4o-mini")
    base_url: str | None = os.getenv("KUBEYUG_LLM_BASE_URL")
    api_key: str | None = os.getenv("KUBEYUG_LLM_API_KEY")

    max_new_tokens: int = int(os.getenv("KUBEYUG_LLM_MAX_NEW_TOKENS", "256"))
    temperature: float = float(os.getenv("KUBEYUG_LLM_TEMPERATURE", "0.1"))


class OumiClient:
    def __init__(self, cfg: OumiClientConfig | None = None):
        self.cfg = cfg or OumiClientConfig()

        model_params = ModelParams(
            model_name=self.cfg.model,
            model_kwargs={},
        )

        gen_params = GenerationParams(
            max_new_tokens=self.cfg.max_new_tokens,
            temperature=self.cfg.temperature,
        )

        self.engine = OpenAIInferenceEngine(
            model_params=model_params,
            generation_params=gen_params,
            remote_params={
                "api_key": self.cfg.api_key,
                "base_url": self.cfg.base_url,
            },
        )

        self.infer_cfg = InferenceConfig(
            model=model_params,
            generation=gen_params,
        )

    def decide(self, goal: str, cluster_summary: dict[str, Any], tools: list[dict[str, Any]]) -> dict[str, Any]:
        """
        Returns:
          {"chartKey": "<tool key>", "reason": "...", "confidence": 0..1}
        """
        prompt = self._build_prompt(goal, cluster_summary, tools)

        convo = Conversation(messages=[Message(role=Role.USER, content=prompt)])
        out = self.engine.infer([convo], self.infer_cfg)

        text = out[0].messages[-1].content
        return self._parse_or_fallback(text, tools)

    def _build_prompt(self, goal: str, cluster_summary: dict[str, Any], tools: list[dict[str, Any]]) -> str:
        return build_tool_selection_prompt(
            goal=goal,
            cluster_summary=cluster_summary,
            tools=tools,
            max_reason_sentences=2,
        )

    def _parse_or_fallback(self, model_text: str, tools: list[dict[str, Any]]) -> dict[str, Any]:
        """
        Robust JSON extraction:
        - Try parse whole output
        - Else extract first {...} block
        - Validate chartKey is in registry tool keys
        """
        tool_keys = [t.get("key") for t in tools if t.get("key")]
        tool_key_set = set(tool_keys)

        obj = None
        try:
            obj = json.loads(model_text)
        except Exception:
            start = model_text.find("{")
            end = model_text.rfind("}")
            if start != -1 and end != -1 and end > start:
                try:
                    obj = json.loads(model_text[start : end + 1])
                except Exception:
                    obj = None

        if not isinstance(obj, dict):
            return {
                "chartKey": tool_keys[0] if tool_keys else None,
                "reason": "LLM output was not valid JSON; using fallback.",
                "confidence": 0.0,
            }

        chart_key = obj.get("chartKey")
        if chart_key not in tool_key_set:
            return {
                "chartKey": tool_keys[0] if tool_keys else None,
                "reason": "LLM returned an unknown tool key; using fallback.",
                "confidence": 0.0,
            }

        conf = obj.get("confidence", 0.5)
        try:
            conf_f = float(conf)
        except Exception:
            conf_f = 0.5

        return {
            "chartKey": chart_key,
            "reason": str(obj.get("reason", ""))[:400],
            "confidence": max(0.0, min(1.0, conf_f)),
        }
