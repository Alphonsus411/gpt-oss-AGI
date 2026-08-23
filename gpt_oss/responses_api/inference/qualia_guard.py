"""Envoltorio Qualia para llamadas de inferencia de Responses API."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping

from agicore_core.qualia_engine import CoreQualiaEngine
from agicore_core.qualia_responses import format_blocked_response


_DANGEROUS_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(pattern, re.IGNORECASE | re.DOTALL)
    for pattern in (
        r"\bmal\s*ware\b",
        r"\bex\s*filtr\w*\b.{0,80}\bcredenciales\b",
        r"\bcredenciales\b.{0,80}\bex\s*filtr\w*\b",
        r"\brob\w*\b.{0,80}\bcredenciales\b",
        r"\bphish\w*\b",
        r"\bkey\s*logger\b",
        r"\bransom\s*ware\b",
        r"\bpassword\s*steal\w*\b",
        r"\bcurl\b.{0,120}\b(sh|bash)\b",
        r"\brm\s+-rf\s+/(?:\s|$)",
        r"\bdd\s+if=/dev/zero\s+of=/dev/",
    )
)


@dataclass
class OutputSafetyScanner:
    """Escáner incremental de salida para Responses API.

    El escáner mantiene texto acumulado y evalúa ventanas solapadas para atrapar
    expresiones dañinas aunque aparezcan divididas entre tokens. Para reducir el
    coste, ejecuta heurísticas locales por chunk y solo llama a Qualia/AGIX cuando
    una ventana supera umbral de riesgo, cuando se inspecciona una tool call o en
    la evaluación final obligatoria.
    """

    qualia_engine: CoreQualiaEngine | None = None
    base_request: Mapping[str, Any] | None = None
    window_size: int = 512
    overlap_size: int = 128
    min_chunk_chars_for_qualia: int = 80
    accumulated_text: str = ""
    _qualia_calls: int = 0
    _seen_windows: set[tuple[str, int, int]] = field(default_factory=set)

    def __post_init__(self) -> None:
        self.qualia_engine = self.qualia_engine or CoreQualiaEngine()
        self.base_request = dict(self.base_request or {})

    @property
    def qualia_calls(self) -> int:
        return self._qualia_calls

    def evaluate_initial_prompt(self, prompt: str, *, phase: str = "responses_api") -> tuple[dict[str, Any], dict[str, Any] | None]:
        self.accumulated_text += f"\n[PROMPT]\n{prompt}"
        return self._run_qualia(prompt, phase=phase, reason="initial_prompt")

    def scan_stream_chunk(self, chunk: str, *, phase: str = "responses_api_stream") -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
        if not chunk:
            return None, None
        self.accumulated_text += chunk
        candidates = self._candidate_windows(final=False)
        risky = [window for window in candidates if self._local_risk_score(window) > 0]
        if not risky and len(chunk) < self.min_chunk_chars_for_qualia:
            return None, None
        if risky:
            return self._run_qualia(risky[-1], phase=phase, reason="stream_window")
        return None, None

    def scan_tool_call(self, name: str, arguments: str, *, phase: str = "responses_api_tool_call") -> tuple[dict[str, Any], dict[str, Any] | None]:
        text = f"tool={name}\narguments={arguments}"
        self.accumulated_text += f"\n[TOOL_CALL]\n{text}"
        return self._run_qualia(text, phase=phase, reason="tool_call")

    def scan_final_response(self, text: str | None = None, *, phase: str = "responses_api_final") -> tuple[dict[str, Any], dict[str, Any] | None]:
        if text:
            self.accumulated_text += f"\n[FINAL]\n{text}"
        final_text = text if text is not None else self.accumulated_text
        windows = self._candidate_windows(final=True, text=final_text)
        # Qualia owns constraints that are deliberately broader than the local
        # heuristics.  At completion, inspect every window rather than using the
        # heuristic only to choose a single tail window.
        last_result: tuple[dict[str, Any], dict[str, Any] | None] | None = None
        for window in windows or [""]:
            last_result = self._run_qualia(window, phase=phase, reason="final_response")
            if last_result[1] is not None:
                return last_result
        assert last_result is not None
        return last_result

    def _candidate_windows(self, *, final: bool, text: str | None = None) -> list[str]:
        source = text if text is not None else self.accumulated_text
        if not source:
            return []
        windows: list[str] = []
        step = max(1, self.window_size - self.overlap_size)
        if final:
            starts = range(0, len(source), step)
        else:
            start = max(0, len(source) - self.window_size - self.overlap_size)
            starts = range(start, len(source), step)
        for start in starts:
            end = min(len(source), start + self.window_size)
            if start >= end:
                continue
            key = ("final" if final else "stream", start, end)
            if key in self._seen_windows and not final:
                continue
            self._seen_windows.add(key)
            windows.append(source[start:end])
        return windows

    def _local_risk_score(self, text: str) -> int:
        normalized = self._normalize_for_scan(text)
        return sum(1 for pattern in _DANGEROUS_PATTERNS if pattern.search(normalized))

    def _normalize_for_scan(self, text: str) -> str:
        # Une divisiones artificiales entre tokens: "mal\n ware", "ex filtrar", etc.
        lowered = text.lower()
        compact_words = re.sub(r"(?<=\w)[\s_\-./]+(?=\w)", "", lowered)
        spaced = re.sub(r"[\s_\-./]+", " ", lowered)
        # Keep the original syntax as well: destructive-command patterns rely
        # on meaningful punctuation such as `-rf`, `=/`, and `/dev/`.
        return f"{lowered}\n{spaced}\n{compact_words}"

    def _run_qualia(self, text: str, *, phase: str, reason: str) -> tuple[dict[str, Any], dict[str, Any] | None]:
        request = dict(self.base_request or {})
        request.update(
            {
                "task": request.get("task", "responses_api_output_safety"),
                "context": phase,
                "scan_reason": reason,
                "prompt": text,
                "decoded_text": text,
                "accumulated_output_tail": self.accumulated_text[-self.window_size :],
            }
        )
        self._qualia_calls += 1
        enriched, blocked = self.qualia_engine.govern_decision(request, phase=phase)
        if blocked is not None:
            formatted = format_blocked_response(blocked, channel=phase)
            self.qualia_engine.after_decision(formatted, enriched, phase=phase)
        return enriched, blocked


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
