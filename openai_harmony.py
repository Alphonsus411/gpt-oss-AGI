"""Stub mínimo de la librería ``openai_harmony`` para las pruebas."""

from enum import Enum
from typing import List


class HarmonyEncodingName(str, Enum):
    HARMONY_GPT_OSS = "harmony-gpt-oss"


class ReasoningEffort(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Author:
    pass


class Conversation:
    pass


class DeveloperContent:
    pass


class HarmonyEncoding:
    def encode(self, text: str, allowed_special: str = "all") -> List[int]:
        return []

    def parse_messages_from_completion_tokens(self, tokens: List[int], role: "Role"):
        return []


class Message:
    @classmethod
    def from_role_and_content(cls, role: "Role", content: str) -> "Message":
        return cls()

    def with_recipient(self, recipient: str) -> "Message":
        return self

    def with_channel(self, channel: str) -> "Message":
        return self

    def to_dict(self):
        return {}


class Role(Enum):
    ASSISTANT = "assistant"


class StreamableParser:
    pass


class StreamState:
    pass


class SystemContent:
    pass


class ToolDescription:
    pass


def load_harmony_encoding(name: HarmonyEncodingName) -> HarmonyEncoding:
    raise RuntimeError("openai_harmony no está disponible en el entorno de pruebas")


class Content:
    pass


class TextContent:
    pass


class SystemError:
    def __init__(self, message: str):
        self.message = message


class ToolNamespaceConfig:
    pass
