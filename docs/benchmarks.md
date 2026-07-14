# Benchmarks Responses + Qualia

Resultados reproducibles generados por `benchmarks/bench_responses_qualia.py`.

## Última ejecución registrada

- Fecha UTC: `2026-07-13T18:49:55+00:00`
- Python: `3.12.13`
- Plataforma: `Linux-6.12.47-x86_64-with-glibc2.39`
- Prompt fijo: `Resume las garantías de seguridad de Qualia en respuestas por streaming y enumera señales de auditoría reproducibles.`
- Tokens objetivo por iteración: `256`
- Tamaño de chunk: `16`
- Iteraciones medidas: `5`
- Warmup: `1`

| Modo | Disponible | Preflight mediana ms | Preflight p95 ms | Chunk mediana ms | Chunk p95 ms | Tokens/s mediana | Tokens/s p95 | Nota |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| none | sí | 0.000 | 0.000 | 0.000 | 0.000 | 25845532.97 | 28400265.72 | ok |
| local_safe | sí | 0.119 | 0.139 | 0.015 | 0.052 | 738088.24 | 824535.07 | ok |
| strict_compatible | no | — | — | — | — | — | — | Contrato AGIX/Qualia estricto incumplido: strict_minimum_component_missing=qualia_engine; strict_minimum_component_missing=moral_evaluator; qualia_engine_not_available |

## Reproducibilidad

Ejecutar localmente:

```bash
python benchmarks/bench_responses_qualia.py --iterations 5 --warmup 1 --target-tokens 256 --chunk-size 16 --write-docs --strict-agix
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
