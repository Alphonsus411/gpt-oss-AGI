import argparse
import pytest


class DummyMessage:
    def __init__(self, recipient: str):
        self.recipient = recipient


def simulate_tool_call(recipient: str, args):
    last_message = DummyMessage(recipient)
    if last_message.recipient.startswith("browser."):
        if not args.browser:
            raise RuntimeError("Browser tool is not enabled")
    elif last_message.recipient.startswith("python"):
        if not args.python:
            raise RuntimeError("Python tool is not enabled")
    elif last_message.recipient == "functions.apply_patch":
        if not args.apply_patch:
            raise RuntimeError("Apply patch tool is not enabled")


@pytest.mark.parametrize(
    "recipient, message",
    [
        ("browser.search", "Browser tool is not enabled"),
        ("python", "Python tool is not enabled"),
        ("functions.apply_patch", "Apply patch tool is not enabled"),
    ],
)
def test_tool_disabled_raises(recipient, message):
    args = argparse.Namespace(browser=False, python=False, apply_patch=False)
    with pytest.raises(RuntimeError, match=message):
        simulate_tool_call(recipient, args)
