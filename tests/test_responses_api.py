import time

import pytest
from fastapi.testclient import TestClient
from openai_harmony import (
    HarmonyEncodingName,
    Role,
    load_harmony_encoding,
)

from gpt_oss.responses_api.api_server import create_api_server

try:
    encoding = load_harmony_encoding(HarmonyEncodingName.HARMONY_GPT_OSS)
except Exception:
    pytest.skip("openai_harmony encoding unavailable", allow_module_level=True)

fake_tokens = encoding.encode(
    "<|channel|>final<|message|>Hey there<|return|>", allowed_special="all"
)

token_queue = fake_tokens.copy()


def stub_infer_next_token(
    tokens: list[int], temperature: float = 0.0, new_request: bool = False
) -> int:
    global token_queue
    next_tok = token_queue.pop(0)
    if len(token_queue) == 0:
        token_queue = fake_tokens.copy()
    time.sleep(0.1)
    return next_tok


@pytest.fixture
def test_client():
    return TestClient(
        create_api_server(infer_next_token=stub_infer_next_token, encoding=encoding)
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


def test_system_message_in_input_reflected(test_client, monkeypatch):
    captured = {}

    original_render = encoding.render_conversation_for_completion

    def capture(conv, role):
        captured["messages"] = conv.messages
        return original_render(conv, role)

    monkeypatch.setattr(encoding, "render_conversation_for_completion", capture)

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
