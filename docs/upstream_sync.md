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

- `agicore_core`
- `gpt_oss/planner.py`
- `meta_router.py`
- `gpt_oss/strategic_memory.py`
- `agicore_core/reasoning_kernel.py`

## Comando recomendado para comparar contra upstream

Después de ejecutar `git fetch upstream`, usa este comando para comparar el fork actual contra la rama principal upstream:

```bash
git diff upstream/main...HEAD
```

Para revisar únicamente el resumen de archivos modificados:

```bash
git diff --stat upstream/main...HEAD
```
