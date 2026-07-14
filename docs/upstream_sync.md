# Sincronización con upstream

Este documento registra el punto de referencia usado para comparar este fork con el repositorio upstream oficial de OpenAI.

## Upstream configurado

- **URL upstream:** `https://github.com/openai/gpt-oss`
- **Remoto Git local:** `upstream`
- **Commit exacto de `openai/gpt-oss` usado como base común:** `4931694686fadfa74a80554473d32f7dd4d059f3`
- **Commit actual observado en `upstream/main` durante la sincronización:** `d21f34ec3c1ede813adfbd83f07d2ad2eec7ff02`
- **Fecha de sincronización:** `2026-07-13` (UTC)

## Resumen de conflictos resueltos

No se realizó una fusión automática de `upstream/main` en esta actualización documental. Por tanto, no hubo conflictos de Git que resolver en este paso. El fork mantiene sus cambios locales sobre el punto base indicado y deja documentado el remoto upstream para futuras sincronizaciones controladas.

Al sincronizar en el futuro, deben preservarse explícitamente las extensiones AGI/AGIX añadidas en este fork y revisar cualquier conflicto que afecte a los módulos listados abajo.

## Extensiones preservadas

Las siguientes extensiones del fork deben conservarse durante comparaciones, rebases o fusiones contra upstream:

- `agicore_core/`: configuración AGIX/Qualia, `QualiaNode`, `CoreQualiaEngine`, `SafetyGate`, adaptadores AGIX y kernel de razonamiento.
- `gpt_oss/planner.py`: modos de planificación que pueden ajustarse mediante memoria.
- `meta_router.py`: enrutado de expertos con memoria episódica y señales Qualia.
- `gpt_oss/strategic_memory.py`: memoria RAM/SQLite, redacción de secretos, auditoría y aprendizaje inferencial seguro.
- `agicore_core/reasoning_kernel.py`: kernel de razonamiento preservado para el fork.
- `gpt_oss/responses_api/inference/qualia_guard.py`: preflight contextual y filtrado de salida de Responses API.

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
