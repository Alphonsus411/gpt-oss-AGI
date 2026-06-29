from importlib import import_module as _im

try:
    # Load the compiled extension (gpt_oss.metal._metal)
    _ext = _im(f"{__name__}._metal")
except ModuleNotFoundError:
    class Model:
        def __init__(self, *args, **kwargs):
            raise RuntimeError("Metal extension is not available")

    class Tokenizer:
        def __init__(self, *args, **kwargs):
            raise RuntimeError("Metal extension is not available")

        def decode(self, *args, **kwargs):
            raise RuntimeError("Metal extension is not available")

    class Context:
        def __init__(self, *args, **kwargs):
            raise RuntimeError("Metal extension is not available")

        def append(self, *args, **kwargs):
            raise RuntimeError("Metal extension is not available")
else:
    globals().update({k: v for k, v in _ext.__dict__.items() if not k.startswith("_")})
    del _ext
del _im
