import pytest
from gpt_oss import metal


def test_model_init_failure():
    with pytest.raises(RuntimeError):
        metal.Model("nonexistent-file")


def test_tokenizer_init_failure():
    dummy_model = object.__new__(metal.Model)
    with pytest.raises(RuntimeError):
        metal.Tokenizer(dummy_model)


def test_tokenizer_decode_failure():
    dummy_tokenizer = object.__new__(metal.Tokenizer)
    with pytest.raises(RuntimeError):
        dummy_tokenizer.decode(0)


def test_context_init_failure():
    dummy_model = object.__new__(metal.Model)
    with pytest.raises(RuntimeError):
        metal.Context(dummy_model)


def test_context_append_failure():
    dummy_context = object.__new__(metal.Context)
    with pytest.raises(RuntimeError):
        dummy_context.append(b"data")

