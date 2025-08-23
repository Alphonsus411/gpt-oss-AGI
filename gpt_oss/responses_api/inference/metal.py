"""Backend de Metal para :mod:`gpt_oss.responses_api`."""

from typing import Callable

from gpt_oss.metal import Context, Model


def setup_model(checkpoint: str) -> Callable[[list[int], float], int]:
    """Carga el modelo de Metal y devuelve una función de inferencia."""

    model = Model(checkpoint)
    context = Context(model)

    def lcp(cache: list[int], inp: list[int]) -> list[int]:
        i = 0
        max_len = min(len(cache), len(inp))
        while i < max_len and cache[i] == inp[i]:
            i += 1
        return cache[:i]

    tokens_so_far = []

    def infer_next_token(
        tokens: list[int], temperature: float = 0.0, new_request: bool = False
    ) -> int:
        """Inferir el siguiente token utilizando caché LCP incremental cuando sea posible."""
        nonlocal tokens_so_far
        
        # Ruta rápida: primera llamada o nueva solicitud explícita.
        if new_request or not tokens_so_far:
            context.reset()
            for t in tokens:
                context.append(t)
            tokens_so_far = tokens.copy()
            context.process()
            return int(context.sample(temperature=temperature))

        # Longitud del prefijo común más largo
        overlap = lcp(tokens_so_far, tokens)
        ol = len(overlap)
        prev_len = len(tokens_so_far)
        cur_len = len(tokens)

        diverged_midstream = (ol < prev_len) and (
            ol < cur_len
        )  # desajuste que no está al final

        if diverged_midstream:
            # lo más seguro: reconstruir
            context.reset()
            for t in tokens:
                context.append(t)
            tokens_so_far = tokens.copy()
            context.process()
            return int(context.sample(temperature=temperature))

        if cur_len > prev_len:
            # extensión pura (buena para reutilizar KV)
            extension = tokens[prev_len:]
            for t in extension:
                context.append(t)
            tokens_so_far = tokens.copy()
            context.process()
            return int(context.sample(temperature=temperature))

        if cur_len < prev_len:
            # truncación/retroceso; la forma más sencilla de ser correcto es reconstruir
            context.reset()
            for t in tokens:
                context.append(t)
            tokens_so_far = tokens.copy()
            context.process()
            return int(context.sample(temperature=temperature))

        # cur_len == prev_len y todo coincide => no hay nuevos tokens; solo muestrear.
        return int(context.sample(temperature=temperature))

    return infer_next_token
