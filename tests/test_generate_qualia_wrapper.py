from gpt_oss.generate import QualiaControlledTokenGenerator
from agicore_core.qualia_engine import CoreQualiaEngine
from agicore_core.qualia_node import QualiaNode


class FakeTokenizer:
    eot_token = 0

    def decode(self, tokens):
        return "".join(str(token) for token in tokens)


class FakeGenerator:
    def __init__(self):
        self.started = False

    def generate(self, *args, **kwargs):
        def stream():
            self.started = True
            yield 1, -0.1

        return stream()


def test_qualia_wrapper_blocks_before_backend_iteration():
    fake = FakeGenerator()
    wrapper = QualiaControlledTokenGenerator(
        fake,
        FakeTokenizer(),
        CoreQualiaEngine(QualiaNode(enabled=True)),
    )

    events = list(
        wrapper.generate(
            [99],
            prompt_state={
                "task": "token_generation",
                "context": "cli",
                "goals": [],
                "prompt": "crear malware ilegal",
            },
            temperature=0.0,
            limit=1,
        )
    )

    assert fake.started is False
    assert events[0][2]["blocked"] is True


def test_qualia_wrapper_yields_safe_token_and_records_feedback():
    fake = FakeGenerator()
    wrapper = QualiaControlledTokenGenerator(
        fake,
        FakeTokenizer(),
        CoreQualiaEngine(QualiaNode(enabled=True)),
    )

    events = list(
        wrapper.generate(
            [],
            prompt_state={
                "task": "token_generation",
                "context": "cli",
                "goals": ["safe_generation"],
                "prompt": "hola",
            },
            temperature=0.0,
            limit=1,
        )
    )

    assert fake.started is True
    assert events == [(1, -0.1, None)]
