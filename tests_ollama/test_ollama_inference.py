import json as json_module
import threading
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from gpt_oss.responses_api.inference.ollama import setup_model, EOS_TOKEN


class DummyEncoding:
    def encode(self, text, allowed_special="all"):
        return [ord(c) for c in text]

    def decode(self, tokens):
        return ''.join(chr(t) for t in tokens)


def fake_load_harmony_encoding(name):
    return DummyEncoding()


class FakeResponse:
    def __init__(self, lines):
        self._lines = lines

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        pass

    def raise_for_status(self):
        pass

    def iter_lines(self, decode_unicode=True):
        for line in self._lines:
            yield line


def test_multiple_instances_independent(monkeypatch):
    monkeypatch.setattr(
        "gpt_oss.responses_api.inference.ollama.load_harmony_encoding",
        fake_load_harmony_encoding,
    )

    def fake_post(url, json, stream, timeout):
        token = "A" if "custom1" in url else "B"
        lines = [
            json_module.dumps({"response": token, "done": False}),
            json_module.dumps({"done": True, "context": [1, 2, 3]}),
        ]
        return FakeResponse(lines)

    monkeypatch.setattr(
        "gpt_oss.responses_api.inference.ollama.requests.post", fake_post
    )

    infer1 = setup_model("model1", endpoint_url="http://custom1/api/generate")
    infer2 = setup_model("model2", endpoint_url="http://custom2/api/generate")

    results = {}

    def run_infer(name, infer):
        tokens = []
        tok = infer([1], 0.0, new_request=True)
        while tok not in (EOS_TOKEN, 0):
            tokens.append(tok)
            tok = infer([], 0.0)
        results[name] = tokens

    t1 = threading.Thread(target=run_infer, args=("m1", infer1))
    t2 = threading.Thread(target=run_infer, args=("m2", infer2))
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    assert results["m1"] == [ord("A")]
    assert results["m2"] == [ord("B")]


def test_env_url(monkeypatch):
    monkeypatch.setenv("OLLAMA_ENDPOINT", "https://env.example/api/generate")
    monkeypatch.setattr(
        "gpt_oss.responses_api.inference.ollama.load_harmony_encoding",
        fake_load_harmony_encoding,
    )
    captured = {}

    def fake_post(url, json, stream, timeout):
        captured["url"] = url
        lines = [
            json_module.dumps({"response": "X", "done": False}),
            json_module.dumps({"done": True}),
        ]
        return FakeResponse(lines)

    monkeypatch.setattr(
        "gpt_oss.responses_api.inference.ollama.requests.post", fake_post
    )

    infer = setup_model("model_env")
    tok = infer([1], 0.0, new_request=True)
    assert captured["url"] == "https://env.example/api/generate"
    assert tok == ord("X")
