import tiktoken

from gpt_oss.tools.simple_browser.simple_browser_tool import ENC_NAME, get_tokens


def test_default_encoding_matches_model():
    text = "Hola mundo"
    encoding = tiktoken.encoding_for_model("gpt-4.1-mini")
    assert ENC_NAME == encoding.name
    tool_tokens = get_tokens(text)
    assert tool_tokens.tokens == encoding.encode(text, disallowed_special=())
