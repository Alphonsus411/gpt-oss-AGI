#!/usr/bin/env python3
"""Benchmark reproducible de streaming Responses con gobierno Qualia.

Mide latencia de preflight, latencia por chunk y tokens/s en tres modos:
- sin Qualia;
- Qualia local_safe;
- AGIX/Qualia strict_compatible cuando el runtime lo permite.

El benchmark usa una fuente determinista de tokens para aislar el coste de la
capa Qualia sin requerir GPU. Si se activa strict y AGIX no cumple el contrato,
el modo se marca como no disponible en lugar de fallar.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import statistics
import sys
import time
from contextlib import contextmanager
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from agicore_core.agix_compat import AgixStrictCompatibilityError
from agicore_core.qualia_node import QualiaNode

DEFAULT_PROMPT = (
    "Resume las garantías de seguridad de Qualia en respuestas por streaming "
    "y enumera señales de auditoría reproducibles."
)
DOCS_PATH = Path("docs/benchmarks.md")


@dataclass(frozen=True)
class BenchmarkConfig:
    prompt: str
    target_tokens: int
    chunk_size: int
    iterations: int
    warmup: int
    strict_agix: bool


@dataclass
class ModeResult:
    mode: str
    available: bool
    reason: str
    preflight_latency_ms_median: float | None = None
    preflight_latency_ms_p95: float | None = None
    chunk_latency_ms_median: float | None = None
    chunk_latency_ms_p95: float | None = None
    tokens_per_second_median: float | None = None
    tokens_per_second_p95: float | None = None
    iterations: int = 0
    tokens: int = 0


@contextmanager
def temporary_env(overrides: dict[str, str | None]) -> Iterator[None]:
    previous = {key: os.environ.get(key) for key in overrides}
    try:
        for key, value in overrides.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        yield
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int(round((pct / 100) * (len(ordered) - 1)))))
    return ordered[index]


def deterministic_tokens(prompt: str, target_tokens: int) -> list[str]:
    seed = (prompt + " qualia audit response stream reproducible benchmark").split()
    if not seed:
        seed = ["qualia"]
    return [seed[index % len(seed)] for index in range(target_tokens)]


def chunk_tokens(tokens: list[str], chunk_size: int) -> Iterator[list[str]]:
    for index in range(0, len(tokens), chunk_size):
        yield tokens[index : index + chunk_size]


def build_node(mode: str) -> QualiaNode | None:
    if mode == "none":
        return None
    with temporary_env(
        {
            "AGIX_RUNTIME_PROFILE": mode,
            "AGIX_REQUIRE_RUNTIME": "1" if mode == "strict_compatible" else None,
        }
    ):
        return QualiaNode()


def run_iteration(
    node: QualiaNode | None, prompt: str, tokens: list[str], chunk_size: int
) -> tuple[float, list[float], float]:
    request: dict[str, Any] = {"input": prompt, "stream": True}
    state: dict[str, Any] = {"stream": True}

    start = time.perf_counter()
    if node is not None:
        request = node.enrich_request(request, phase="responses.preflight")
        if request.get("qualia", {}).get("blocked"):
            raise RuntimeError("El prompt de benchmark fue bloqueado por Qualia")
    preflight = time.perf_counter() - start

    generation_start = time.perf_counter()
    chunk_latencies: list[float] = []
    emitted = 0
    for chunk in chunk_tokens(tokens, chunk_size):
        chunk_start = time.perf_counter()
        text = " ".join(chunk)
        if node is not None:
            state = node.integrate_response(
                {
                    "type": "response.output_text.delta",
                    "delta": text,
                    "tokens": len(chunk),
                },
                state,
                phase="responses.chunk",
            )
        emitted += len(chunk)
        chunk_latencies.append(time.perf_counter() - chunk_start)
    elapsed = time.perf_counter() - generation_start
    return preflight, chunk_latencies, emitted / elapsed if elapsed > 0 else 0.0


def benchmark_mode(mode: str, config: BenchmarkConfig) -> ModeResult:
    try:
        node = build_node(mode)
    except AgixStrictCompatibilityError as exc:
        return ModeResult(mode=mode, available=False, reason=str(exc))

    tokens = deterministic_tokens(config.prompt, config.target_tokens)
    preflights: list[float] = []
    chunks: list[float] = []
    rates: list[float] = []
    total_runs = config.warmup + config.iterations
    for run_index in range(total_runs):
        preflight, chunk_latencies, rate = run_iteration(
            node, config.prompt, tokens, config.chunk_size
        )
        if run_index >= config.warmup:
            preflights.append(preflight * 1000)
            chunks.extend(value * 1000 for value in chunk_latencies)
            rates.append(rate)

    return ModeResult(
        mode=mode,
        available=True,
        reason="ok",
        preflight_latency_ms_median=statistics.median(preflights),
        preflight_latency_ms_p95=percentile(preflights, 95),
        chunk_latency_ms_median=statistics.median(chunks),
        chunk_latency_ms_p95=percentile(chunks, 95),
        tokens_per_second_median=statistics.median(rates),
        tokens_per_second_p95=percentile(rates, 95),
        iterations=config.iterations,
        tokens=config.target_tokens,
    )


def render_markdown(config: BenchmarkConfig, results: list[ModeResult]) -> str:
    command = (
        "python benchmarks/bench_responses_qualia.py "
        f"--iterations {config.iterations} --warmup {config.warmup} "
        f"--target-tokens {config.target_tokens} --chunk-size {config.chunk_size} --write-docs"
    )
    if config.strict_agix:
        command += " --strict-agix"
    rows = []
    for item in results:
        if item.available:
            rows.append(
                "| {mode} | sí | {pre:.3f} | {pre95:.3f} | {chunk:.3f} | {chunk95:.3f} | {tps:.2f} | {tps95:.2f} | {reason} |".format(
                    mode=item.mode,
                    pre=item.preflight_latency_ms_median,
                    pre95=item.preflight_latency_ms_p95,
                    chunk=item.chunk_latency_ms_median,
                    chunk95=item.chunk_latency_ms_p95,
                    tps=item.tokens_per_second_median,
                    tps95=item.tokens_per_second_p95,
                    reason=item.reason,
                )
            )
        else:
            rows.append(
                f"| {item.mode} | no | — | — | — | — | — | — | {item.reason} |"
            )
    generated = datetime.now(timezone.utc).isoformat(timespec="seconds")
    return f"""# Benchmarks Responses + Qualia

Resultados reproducibles generados por `benchmarks/bench_responses_qualia.py`.

## Última ejecución registrada

- Fecha UTC: `{generated}`
- Python: `{platform.python_version()}`
- Plataforma: `{platform.platform()}`
- Prompt fijo: `{config.prompt}`
- Tokens objetivo por iteración: `{config.target_tokens}`
- Tamaño de chunk: `{config.chunk_size}`
- Iteraciones medidas: `{config.iterations}`
- Warmup: `{config.warmup}`

| Modo | Disponible | Preflight mediana ms | Preflight p95 ms | Chunk mediana ms | Chunk p95 ms | Tokens/s mediana | Tokens/s p95 | Nota |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
{chr(10).join(rows)}

## Reproducibilidad

Ejecutar localmente:

```bash
{command}
```

El benchmark no requiere GPU: usa tokens deterministas para medir el coste de
preflight y streaming de la capa Responses/Qualia. El modo `strict_compatible`
solo se mide con `--strict-agix`; si AGIX 1.9.0 o sus componentes estrictos no
están disponibles, queda registrado como `Disponible = no` sin fallar el comando.

## CI opcional no bloqueante

El workflow principal incluye el job `optional-qualia-benchmark`, activable por
`workflow_dispatch` con `run_qualia_benchmark=true`. El job usa
`continue-on-error: true` y está deshabilitado para releases/tags normales, por
lo que la ausencia de hardware o de runtime AGIX estricto no bloquea releases.
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prompt", default=DEFAULT_PROMPT)
    parser.add_argument("--target-tokens", type=int, default=256)
    parser.add_argument("--chunk-size", type=int, default=16)
    parser.add_argument("--iterations", type=int, default=5)
    parser.add_argument("--warmup", type=int, default=1)
    parser.add_argument("--strict-agix", action="store_true")
    parser.add_argument("--json", type=Path)
    parser.add_argument("--write-docs", action="store_true")
    args = parser.parse_args()

    config = BenchmarkConfig(
        prompt=args.prompt,
        target_tokens=args.target_tokens,
        chunk_size=args.chunk_size,
        iterations=args.iterations,
        warmup=args.warmup,
        strict_agix=args.strict_agix,
    )
    modes = ["none", "local_safe"] + (["strict_compatible"] if args.strict_agix else [])
    results = [benchmark_mode(mode, config) for mode in modes]

    payload = {
        "config": asdict(config),
        "results": [asdict(result) for result in results],
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    if args.write_docs:
        DOCS_PATH.write_text(render_markdown(config, results), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
