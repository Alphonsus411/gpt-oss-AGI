import pytest

from gpt_oss.responses_api.inference.qualia_guard import (
    OutputSafetyScanner,
    QualiaGuardedInference,
)


class FakeQualiaEngine:
    def __init__(self):
        self.calls = []

    def govern_decision(self, request, phase="test"):
        self.calls.append((phase, request))
        text = (
            str(request.get("task", ""))
            + "\n"
            + str(request.get("goals", ""))
            + "\n"
            + request.get("prompt", "")
            + "\n"
            + request.get("decoded_text", "")
            + "\n"
            + request.get("accumulated_output_tail", "")
        ).lower()
        compact = "".join(ch for ch in text if ch.isalnum())
        if "malware" in compact or "exfiltrarcredenciales" in compact or "rmrf" in compact:
            blocked = {
                "message": "blocked by fake qualia",
                "legal_policy_action": "blocked_illegal_or_unsafe_decision",
                "violated_constraints": ["malware"],
            }
            return {**request, "qualia": {"blocked": True}}, blocked
        return {**request, "qualia": {"blocked": False}}, None

    def after_decision(self, result, state, phase="test"):
        return None


def test_qualia_guard_blocks_before_backend_call():
    called = {"backend": 0}

    def backend(tokens, temperature=0.0, new_request=False):
        called["backend"] += 1
        return 1

    guard = QualiaGuardedInference(backend, qualia_engine=FakeQualiaEngine())

    with pytest.raises(RuntimeError):
        guard(
            [1],
            request_state={
                "task": "crear malware ilegal",
                "context": "ctx",
                "goals": ["exfiltrar credenciales"],
            },
        )

    assert called["backend"] == 0


def test_qualia_guard_allows_safe_backend_call():
    def backend(tokens, temperature=0.0, new_request=False):
        return 7

    guard = QualiaGuardedInference(backend, qualia_engine=FakeQualiaEngine())

    assert guard([1], request_state={"task": "analizar", "context": "ctx"}) == 7


def test_qualia_guard_restarts_preflight_for_each_default_call():
    called = {"backend": 0}
    engine = FakeQualiaEngine()

    def backend(tokens, temperature=0.0, new_request=False):
        called["backend"] += 1
        return 7

    guard = QualiaGuardedInference(backend, qualia_engine=engine)

    assert guard([1], request_state={"task": "analizar", "prompt": "Solicitud benigna."}) == 7

    with pytest.raises(RuntimeError):
        guard([2], request_state={"task": "crear malware ilegal"})

    assert called["backend"] == 1
    assert [phase for phase, _request in engine.calls] == ["inference_pre", "inference_pre"]


def test_qualia_guard_uses_incremental_scanner_for_benign_tokens():
    engine = FakeQualiaEngine()

    def backend(tokens, temperature=0.0, new_request=False):
        return len(tokens) + 100

    guard = QualiaGuardedInference(
        backend,
        qualia_engine=engine,
        checkpoint_interval=50,
    )

    tokens = []
    for index in range(25):
        token = guard(
            tokens,
            new_request=index == 0,
            request_state={
                "task": "analizar",
                "prompt": "Resume una noticia local sin contenido riesgoso.",
                "decoded_delta": " texto benigno",
            },
        )
        tokens.append(token)

    assert len(tokens) == 25
    assert guard.qualia_calls == 1
    assert len(engine.calls) == 1
    assert engine.calls[0][0] == "inference_pre"


def test_qualia_guard_degraded_token_id_only_mode_uses_checkpoints_not_every_token():
    engine = FakeQualiaEngine()

    def backend(tokens, temperature=0.0, new_request=False):
        return len(tokens) + 1

    guard = QualiaGuardedInference(
        backend,
        qualia_engine=engine,
        checkpoint_interval=4,
    )

    tokens = []
    for index in range(10):
        tokens.append(
            guard(
                tokens,
                new_request=index == 0,
                request_state={
                    "task": "analizar",
                    "prompt": "Solicitud benigna.",
                },
            )
        )

    phases = [phase for phase, _request in engine.calls]
    assert phases == ["inference_pre", "inference_checkpoint", "inference_checkpoint"]
    assert guard.qualia_calls == 1
    assert len(engine.calls) == 3


def test_qualia_guard_runs_qualia_for_risky_decoded_window():
    engine = FakeQualiaEngine()

    def backend(tokens, temperature=0.0, new_request=False):
        return len(tokens) + 1

    guard = QualiaGuardedInference(backend, qualia_engine=engine, checkpoint_interval=50)

    guard(
        [],
        new_request=True,
        request_state={"task": "analizar", "prompt": "Solicitud benigna.", "decoded_delta": "mal"},
    )
    with pytest.raises(RuntimeError):
        guard(
            [1],
            new_request=False,
            request_state={
                "task": "analizar",
                "prompt": "Solicitud benigna.",
                "decoded_delta": " ware para ex filtrar credenciales",
            },
        )

    phases = [phase for phase, _request in engine.calls]
    assert phases == ["inference_pre", "inference_stream"]


def test_output_safety_scanner_blocks_harmful_phrase_split_across_chunks():
    engine = FakeQualiaEngine()
    scanner = OutputSafetyScanner(
        qualia_engine=engine,
        base_request={"task": "responses_api", "goals": ["safe_generation"]},
    )

    assert scanner.scan_stream_chunk("Texto benigno sobre mal")[1] is None
    _, blocked = scanner.scan_stream_chunk(" ware para ex filtrar credenciales")

    assert blocked is not None
    assert blocked["legal_policy_action"] == "blocked_illegal_or_unsafe_decision"
    assert len(engine.calls) == 1
    assert engine.calls[0][0] == "responses_api_stream"


def test_output_safety_scanner_blocks_dangerous_tool_call():
    engine = FakeQualiaEngine()
    scanner = OutputSafetyScanner(qualia_engine=engine)

    _, blocked = scanner.scan_tool_call(
        "functions.shell",
        '{"cmd": "rm -rf /"}',
    )

    assert blocked is not None
    assert engine.calls[0][0] == "responses_api_tool_call"
