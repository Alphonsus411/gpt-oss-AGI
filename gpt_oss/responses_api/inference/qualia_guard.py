"""Envoltorio Qualia para llamadas de inferencia de Responses API."""

from __future__ import annotations

from typing import Any, Callable, Mapping

from agicore_core.qualia_engine import CoreQualiaEngine
from agicore_core.qualia_responses import format_blocked_response


class QualiaGuardedInference:
    """Protege inferencias directas con gobierno central Qualia."""

    def __init__(self, backend: Callable[..., int], qualia_engine: CoreQualiaEngine | None = None) -> None:
        self.backend = backend
        self.qualia_engine = qualia_engine or CoreQualiaEngine()

    def preflight(self, request: Mapping[str, Any], *, phase: str = "inference_pre") -> tuple[dict[str, Any], dict[str, Any] | None]:
        enriched, blocked = self.qualia_engine.govern_decision(request, phase=phase)
        if blocked is not None:
            formatted = format_blocked_response(blocked, channel=phase)
            self.qualia_engine.after_decision(formatted, enriched, phase=phase)
            return enriched, formatted
        return enriched, None

    def __call__(self, tokens: list[int], temperature: float = 0.0, new_request: bool = False, *, request_state: Mapping[str, Any] | None = None) -> int:
        state = dict(request_state or {})
        state.update({"task": "responses_api_token", "tokens_seen": len(tokens)})
        _, blocked = self.preflight(state, phase="inference_pre")
        if blocked is not None:
            raise RuntimeError(blocked["message"])
        token = self.backend(tokens, temperature=temperature, new_request=new_request)
        post_state = {**state, "last_token_id": token}
        enriched, blocked = self.preflight(post_state, phase="inference_token")
        if blocked is not None:
            raise RuntimeError(blocked["message"])
        self.qualia_engine.after_decision({"token": token}, enriched, phase="inference_token")
        return token
