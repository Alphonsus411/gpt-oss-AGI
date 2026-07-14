import pytest
import structlog
from fastapi.testclient import TestClient

from agicore_core.domain_errors import HarmonyParseError, QualiaPolicyError
from agicore_core.qualia_node import QualiaNode
from gpt_oss.responses_api.api_server import create_api_server

pytestmark = pytest.mark.unit


def test_domain_error_returns_safe_http_response(harmony_encoding):
    def infer_next_token(tokens, temperature=0.0, new_request=False):
        return 0

    app = create_api_server(infer_next_token=infer_next_token, encoding=harmony_encoding)

    @app.get("/raise-harmony-for-test")
    async def raise_harmony_for_test():
        raise HarmonyParseError("raw secret sk-test-123 in internal exception", detail="secret detail")

    client = TestClient(app)
    response = client.get("/raise-harmony-for-test")

    assert response.status_code == 400
    payload = response.json()
    assert payload == {
        "error": {
            "code": "harmony_parse_error",
            "message": HarmonyParseError.safe_message,
        }
    }
    assert "sk-test-123" not in response.text
    assert "secret detail" not in response.text


def test_structured_logs_do_not_include_prompt_or_secrets(harmony_encoding):
    events = []

    def capture(_, __, event_dict):
        events.append(dict(event_dict))
        return event_dict

    structlog.configure(processors=[capture, structlog.processors.JSONRenderer()])

    def infer_next_token(tokens, temperature=0.0, new_request=False):
        return 0

    app = create_api_server(infer_next_token=infer_next_token, encoding=harmony_encoding)

    @app.get("/raise-domain-for-log-test")
    async def raise_domain_for_log_test():
        raise HarmonyParseError("prompt=super-secret password=hunter2", detail="hunter2")

    client = TestClient(app)
    response = client.get("/raise-domain-for-log-test")

    assert response.status_code == 400
    rendered = repr(events)
    assert "hunter2" not in rendered
    assert "super-secret" not in rendered
    assert any(event.get("event") == "responses_api.domain_error" for event in events)


def test_qualia_moral_evaluator_failure_is_not_hidden():
    class BrokenEvaluator:
        def evaluate(self, request):
            raise RuntimeError("critical qualia failure with secret")

    node = QualiaNode(enabled=True)
    node._moral_evaluator = BrokenEvaluator()

    with pytest.raises(QualiaPolicyError):
        node.enrich_request({"task": "x", "prompt": "benign"}, phase="unit")
