import pytest

from gpt_oss.responses_api.inference.qualia_guard import QualiaGuardedInference


def test_qualia_guard_blocks_before_backend_call():
    called = {"backend": 0}

    def backend(tokens, temperature=0.0, new_request=False):
        called["backend"] += 1
        return 1

    guard = QualiaGuardedInference(backend)

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

    guard = QualiaGuardedInference(backend)

    assert guard([1], request_state={"task": "analizar", "context": "ctx"}) == 7
