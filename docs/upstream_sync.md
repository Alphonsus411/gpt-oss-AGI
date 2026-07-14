# Sincronización con upstream

Este documento registra el punto de referencia usado para comparar este fork con el repositorio upstream oficial de OpenAI.

## Upstream configurado

- **URL upstream:** `https://github.com/openai/gpt-oss`
- **Remoto Git local:** `upstream`
- **Commit exacto de `openai/gpt-oss` usado como base del fork:** `4931694686fadfa74a80554473d32f7dd4d059f3`
- **Fecha del commit base upstream:** `2025-08-05T17:52:43-07:00`
- **Asunto del commit base upstream:** `fix build`
- **Commit observado en `upstream/main` tras `git fetch upstream --prune`:** `d21f34ec3c1ede813adfbd83f07d2ad2eec7ff02`
- **Fecha del commit observado en `upstream/main`:** `2026-06-09T15:51:19-07:00`
- **Fecha de esta sincronización:** `2026-07-14` (UTC)

## Ramas y referencias comparadas

- **Rama local sincronizada:** `work`
- **HEAD local durante la auditoría:** `40fffb28f73226ec6c953aa31fe1fb988d928d23`
- **Rama upstream comparada:** `upstream/main`
- **Comparación de preservación local:** `4931694686fadfa74a80554473d32f7dd4d059f3..HEAD`
- **Comparación recomendada contra upstream actual:** `upstream/main...HEAD`

Git no devolvió un `merge-base` directo entre `HEAD` local y `upstream/main`, por lo que el punto base se registra de forma explícita con el SHA completo anterior. Ese commit sí existe en los objetos descargados desde upstream y está contenido en `upstream/main`.

## Resumen de conflictos y resoluciones

No se realizó una fusión automática ni un rebase de `upstream/main` sobre la rama local en esta sincronización. Por tanto, no hubo conflictos de Git que resolver en archivos de código.

Resoluciones aplicadas en esta actualización:

- Se añadió/configuró el remoto local `upstream` apuntando a `https://github.com/openai/gpt-oss`.
- Se ejecutó `git fetch upstream --prune` para actualizar las referencias remotas.
- Se seleccionó y verificó el commit base exacto `4931694686fadfa74a80554473d32f7dd4d059f3`.
- Se conservan las extensiones locales del fork y se añade una auditoría automatizada para exigir que este SHA base permanezca documentado.

Al sincronizar en el futuro, deben preservarse explícitamente las extensiones AGI/AGIX añadidas en este fork y revisar cualquier conflicto que afecte a los módulos listados abajo.

## Extensiones preservadas

Las siguientes extensiones del fork deben conservarse durante comparaciones, rebases o fusiones contra upstream:

- `agicore_core/`: configuración AGIX/Qualia, `QualiaNode`, `CoreQualiaEngine`, `SafetyGate`, adaptadores AGIX y kernel de razonamiento.
- `gpt_oss/planner.py`: modos de planificación que pueden ajustarse mediante memoria.
- `meta_router.py`: enrutado de expertos con memoria episódica y señales Qualia.
- `agicore_core/reasoning_kernel.py`: kernel de razonamiento preservado para el fork.
- `gpt_oss/strategic_memory.py`: memoria RAM/SQLite, redacción de secretos, auditoría y aprendizaje inferencial seguro.
- `ReasoningKernel`: extensión local disponible en `agicore_core/reasoning_kernel.py` y reexportada desde `agicore_core`.
- `gpt_oss/responses_api/inference/qualia_guard.py`: preflight contextual y filtrado de salida de Responses API.

## Auditoría obligatoria

La prueba `tests/test_upstream_sync_audit.py` y el script independiente `scripts/audit_upstream_sync.py` fallan si `docs/upstream_sync.md` deja de contener el SHA upstream base completo `4931694686fadfa74a80554473d32f7dd4d059f3` o si el documento ya no menciona las ramas/referencias comparadas.

## Advertencia de fork experimental

`gpt-oss-AGI` es un fork comunitario experimental y no oficial. No modifica ni redistribuye pesos de OpenAI, no afirma alcanzar AGI y puede divergir del diseño upstream. Toda sincronización debe revisar manualmente los cambios de seguridad, memoria y perfiles AGIX antes de publicar artefactos.

## Comando recomendado para comparar contra upstream

Después de ejecutar `git fetch upstream`, usa este comando para comparar el fork actual contra la rama principal upstream:

```bash
git diff upstream/main...HEAD
```

Para revisar únicamente el resumen de archivos modificados:

```bash
git diff --stat upstream/main...HEAD
```
