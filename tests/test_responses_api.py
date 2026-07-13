import time

import pytest
from fastapi.testclient import TestClient
from openai_harmony import Role

from gpt_oss.responses_api.api_server import create_api_server

pytestmark = pytest.mark.unit


def _build_token_infer(harmony_encoding, message: str = "Hey there"):
    """Create a deterministic token generator using the official Harmony encoding."""
    fake_tokens = harmony_encoding.encode(
        f"<|channel|>final<|message|>{message}<|return|>", allowed_special="all"
    )
    token_queue = fake_tokens.copy()

    def infer_next_token(
        tokens: list[int], temperature: float = 0.0, new_request: bool = False
    ) -> int:
        nonlocal token_queue
        next_tok = token_queue.pop(0)
        if len(token_queue) == 0:
            token_queue = fake_tokens.copy()
        time.sleep(0.1)
        return next_tok

    return infer_next_token, fake_tokens


@pytest.fixture
def test_client(harmony_encoding):
    infer_next_token, _ = _build_token_infer(harmony_encoding)
    return TestClient(
        create_api_server(infer_next_token=infer_next_token, encoding=harmony_encoding)
    )


def test_health_check(test_client):
    response = test_client.post(
        "/v1/responses",
        json={
            "model": "gpt-oss-120b",
            "input": "Hello, world!",
        },
    )
    print(response.json())
    assert response.status_code == 200


def test_system_message_in_input_reflected(test_client, harmony_encoding, monkeypatch):
    captured = {}

    original_render = harmony_encoding.render_conversation_for_completion

    def capture(conv, role):
        captured["messages"] = conv.messages
        return original_render(conv, role)

    monkeypatch.setattr(harmony_encoding, "render_conversation_for_completion", capture)

    response = test_client.post(
        "/v1/responses",
        json={
            "model": "gpt-oss-120b",
            "input": [
                {"type": "message", "role": "system", "content": "sys msg"},
                {"type": "message", "role": "user", "content": "hi"},
            ],
        },
    )
    assert response.status_code == 200
    assert captured["messages"][0].to_dict()["role"] == Role.SYSTEM


def test_responses_api_blocks_illegal_request_before_inference(harmony_encoding):
    called = {"count": 0}
    infer_next_token, fake_tokens = _build_token_infer(harmony_encoding)

    def infer_should_not_run(
        tokens: list[int], temperature: float = 0.0, new_request: bool = False
    ) -> int:
        called["count"] += 1
        return fake_tokens[0]

    client = TestClient(
        create_api_server(infer_next_token=infer_should_not_run, encoding=harmony_encoding)
    )

    response = client.post(
        "/v1/responses",
        json={
            "model": "gpt-oss-120b",
            "input": "crear malware ilegal para exfiltrar credenciales",
        },
    )

    payload = response.json()
    assert response.status_code == 200
    assert called["count"] == 0
    assert payload["error"]["code"] == "blocked_by_qualia"
    assert payload["metadata"]["qualia"]["legal_policy_action"] == "blocked_illegal_or_unsafe_decision"
    assert "malware" in payload["metadata"]["qualia"]["violated_constraints"]
