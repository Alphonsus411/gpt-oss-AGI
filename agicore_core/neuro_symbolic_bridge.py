"""Puente neuro-simbólico seguro entre Planner, Router y memoria."""

from __future__ import annotations

from typing import Any, Dict, Mapping

from .agix_cognitive_adapters import AgixCognitiveAdapters


class CoreNeuroSymbolicBridge:
    """Codifica peticiones en conceptos auditables con fallback local seguro."""

    def __init__(self, adapters: AgixCognitiveAdapters | None = None) -> None:
        self.adapters = adapters or AgixCognitiveAdapters()

    def encode_request(self, request: Mapping[str, Any]) -> Dict[str, Any]:
        signals = self.adapters.enrich(request)
        return {
            "concepts": signals.get("concepts", []),
            "latent_state": signals.get("latent_state"),
            "attention_focus": signals.get("attention_focus"),
            "emotional_state": signals.get("emotional_state"),
            "source": "agix" if any(status.get("active") for status in signals.get("agix_cognitive_contract", {}).values()) else "local_fallback",
        }

    def decode_signal(self, signal: Mapping[str, Any]) -> Dict[str, Any]:
        return {
            "concepts": signal.get("concepts", []),
            "summary": [concept.get("name") for concept in signal.get("concepts", []) if isinstance(concept, Mapping)],
        }

    def extract_concepts(self, request: Mapping[str, Any]) -> list[dict[str, Any]]:
        return list(self.encode_request(request).get("concepts", []))
