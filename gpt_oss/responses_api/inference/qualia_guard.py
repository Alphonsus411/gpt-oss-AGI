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
        risky = [window for window in windows if self._local_risk_score(window) > 0]
        target = risky[-1] if risky else final_text[-self.window_size :]
        return self._run_qualia(target, phase=phase, reason="final_response")

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
        return f"{spaced}\n{compact_words}"

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


@dataclass
class _InferenceRequestState:
    """Estado incremental interno de una inferencia directa protegida."""

    scanner: OutputSafetyScanner
    tokens_seen: int = 0
    degraded_token_id_only: bool = False


class QualiaGuardedInference:
    """Protege inferencias directas con gobierno central Qualia.

    La protección ya no ejecuta Qualia por cada token benigno. Cada request
    mantiene un :class:`OutputSafetyScanner` incremental que reevalúa solo el
    preflight inicial, tool calls, respuesta final, ventanas localmente riesgosas
    y checkpoints configurables.

    Modo degradado: algunos backends actuales solo devuelven IDs de token y no
    exponen texto decodificado en ``request_state``. En ese caso no hay contenido
    nuevo para aplicar heurísticas locales; se conserva el preflight inicial y se
    ejecutan checkpoints sobre metadatos cada ``checkpoint_interval`` tokens,
    además de tool calls/final si el caller los entrega explícitamente.
    """

    def __init__(
        self,
        backend: Callable[..., int],
        qualia_engine: CoreQualiaEngine | None = None,
        *,
        checkpoint_interval: int = 64,
        scanner_factory: Callable[..., OutputSafetyScanner] = OutputSafetyScanner,
    ) -> None:
        self.backend = backend
        self.qualia_engine = qualia_engine or CoreQualiaEngine()
        self.checkpoint_interval = max(1, checkpoint_interval)
        self.scanner_factory = scanner_factory
        self._request_state: _InferenceRequestState | None = None

    def preflight(self, request: Mapping[str, Any], *, phase: str = "inference_pre") -> tuple[dict[str, Any], dict[str, Any] | None]:
        enriched, blocked = self.qualia_engine.govern_decision(request, phase=phase)
        if blocked is not None:
            formatted = format_blocked_response(blocked, channel=phase)
            self.qualia_engine.after_decision(formatted, enriched, phase=phase)
            return enriched, formatted
        return enriched, None

    @property
    def qualia_calls(self) -> int:
        """Número de llamadas Qualia del escáner incremental activo."""

        return self._request_state.scanner.qualia_calls if self._request_state else 0

    def __call__(self, tokens: list[int], temperature: float = 0.0, new_request: bool = False, *, request_state: Mapping[str, Any] | None = None) -> int:
        state = dict(request_state or {})
        if new_request or self._request_state is None:
            self._start_request(state, len(tokens))
        assert self._request_state is not None

        self._scan_request_events(state)
        token = self.backend(tokens, temperature=temperature, new_request=new_request)
        self._request_state.tokens_seen = max(self._request_state.tokens_seen + 1, len(tokens) + 1)

        decoded = self._extract_decoded_delta(state)
        if decoded:
            self._raise_if_blocked(
                self._request_state.scanner.scan_stream_chunk(decoded, phase="inference_stream")[1]
            )
        else:
            self._request_state.degraded_token_id_only = True

        if self._should_checkpoint(state):
            checkpoint = {
                **state,
                "task": state.get("task", "responses_api_token_checkpoint"),
                "tokens_seen": self._request_state.tokens_seen,
                "last_token_id": token,
                "degraded_token_id_only": self._request_state.degraded_token_id_only,
            }
            _, blocked = self.preflight(checkpoint, phase="inference_checkpoint")
            self._raise_if_blocked(blocked)

        self.qualia_engine.after_decision(
            {"token": token, "degraded_token_id_only": self._request_state.degraded_token_id_only},
            {"tokens_seen": self._request_state.tokens_seen},
            phase="inference_token",
        )
        return token

    def _start_request(self, state: Mapping[str, Any], tokens_seen: int) -> None:
        prompt = self._extract_prompt(state)
        scanner = self.scanner_factory(qualia_engine=self.qualia_engine, base_request=state)
        self._request_state = _InferenceRequestState(scanner=scanner, tokens_seen=tokens_seen)
        _, blocked = scanner.evaluate_initial_prompt(prompt, phase="inference_pre")
        self._raise_if_blocked(blocked)

    def _scan_request_events(self, state: Mapping[str, Any]) -> None:
        assert self._request_state is not None
        for tool_call in self._iter_tool_calls(state):
            _, blocked = self._request_state.scanner.scan_tool_call(
                str(tool_call.get("name", tool_call.get("tool", "unknown"))),
                str(tool_call.get("arguments", tool_call.get("args", ""))),
                phase="inference_tool_call",
            )
            self._raise_if_blocked(blocked)

        final_text = state.get("final_text") or state.get("final_response")
        if final_text is not None or state.get("final"):
            _, blocked = self._request_state.scanner.scan_final_response(
                str(final_text) if final_text is not None else None,
                phase="inference_final",
            )
            self._raise_if_blocked(blocked)

    def _should_checkpoint(self, state: Mapping[str, Any]) -> bool:
        assert self._request_state is not None
        interval = int(state.get("qualia_checkpoint_interval", self.checkpoint_interval) or self.checkpoint_interval)
        interval = max(1, interval)
        return self._request_state.tokens_seen % interval == 0

    def _extract_prompt(self, state: Mapping[str, Any]) -> str:
        prompt = state.get("prompt", state.get("input", state.get("decoded_text", "")))
        if isinstance(prompt, list):
            return "\n".join(str(item) for item in prompt)
        return str(prompt)

    def _extract_decoded_delta(self, state: Mapping[str, Any]) -> str:
        for key in ("decoded_delta", "delta", "token_text", "text_delta"):
            value = state.get(key)
            if value:
                return str(value)
        return ""

    def _iter_tool_calls(self, state: Mapping[str, Any]) -> list[Mapping[str, Any]]:
        tool_calls = state.get("tool_calls") or state.get("tool_call")
        if tool_calls is None:
            return []
        if isinstance(tool_calls, Mapping):
            return [tool_calls]
        if isinstance(tool_calls, list):
            return [item for item in tool_calls if isinstance(item, Mapping)]
        return []

    def _raise_if_blocked(self, blocked: Mapping[str, Any] | None) -> None:
        if blocked is not None:
            raise RuntimeError(str(blocked.get("message", "blocked by Qualia")))
