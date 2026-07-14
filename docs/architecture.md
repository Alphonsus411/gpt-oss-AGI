# Arquitectura del fork gpt-oss-AGI

> **Estado:** fork comunitario experimental y no oficial de OpenAI. Esta documentación describe las capas añadidas por el fork; no implica soporte, aval ni compatibilidad garantizada con el repositorio upstream `openai/gpt-oss`.

## Base upstream y alcance

- **Upstream oficial:** `https://github.com/openai/gpt-oss`.
- **Commit base común usado para comparar el fork:** `4931694686fadfa74a80554473d32f7dd4d059f3`.
- **Último `upstream/main` observado durante la sincronización documental:** `d21f34ec3c1ede813adfbd83f07d2ad2eec7ff02`.
- **Fecha registrada:** `2026-07-13` UTC.

El fork conserva los backends y utilidades principales de gpt-oss, pero añade una capa AGIX/Qualia para gobierno contextual, memoria estratégica, planificación y auditoría. No modifica ni redistribuye pesos de los modelos `gpt-oss`.

## Módulos preservados del fork

Durante rebases, merges o comparaciones con upstream deben preservarse estos módulos y puntos de integración:

- `agicore_core/`: núcleo Qualia/AGIX, configuración, compatibilidad, SafetyGate, motor Qualia y adaptadores.
- `gpt_oss/planner.py`: planificación de modos con señales de memoria.
- `meta_router.py`: enrutado de expertos con memoria episódica y señales Qualia.
- `gpt_oss/strategic_memory.py`: memoria RAM/SQLite, redacción de secretos, auditoría y consolidación de hipótesis.
- `agicore_core/reasoning_kernel.py`: kernel de razonamiento preservado para el fork.
- `gpt_oss/responses_api/inference/qualia_guard.py`: preflight y filtrado incremental de salidas para Responses API.

## Capas principales

1. **Capa upstream gpt-oss**: modelos, tokenizer, Harmony, backends Triton/Metal/Transformers/vLLM/Ollama y servidor Responses API.
2. **Core Qualia/AGIX (`agicore_core`)**: `CoreQualiaEngine` centraliza `before_decision`, `govern_decision` y `after_decision`; `QualiaNode` enriquece solicitudes con políticas, patrones y decisiones.
3. **SafetyGate contextual**: bloquea antes de invocar GPT, router o backend cuando Qualia marca riesgo moral, legal, ontoético o inseguro.
4. **Responses API guardada**: `QualiaGuardedInference` ejecuta preflight inicial, checkpoints configurables y checks obligatorios en tool calls/final; `OutputSafetyScanner` inspecciona prompts, tool calls, chunks de streaming y respuesta final con ventanas incrementales.
5. **Memoria estratégica**: `StrategicMemory` usa un backend en RAM por defecto o `SQLiteMemoryBackend` para persistencia transaccional.
6. **Planner/MetaRouter**: consumen memoria episódica para ajustar modos, rutas y expertos sin aprender de episodios bloqueados por Qualia.

## Perfiles AGIX

El paquete fija `agix==1.9.0` y define extras opcionales:

```bash
pip install -e .[agix-neuro]
pip install -e .[agix-ml]
pip install -e .[agix-data]
pip install -e .[agix-full]
```

La configuración empaquetada `agicore_core/config/qualia_profile.json` usa
`runtime_profile=local_safe` y `require_agix_runtime=false` por defecto. Por
ello, una carga limpia del paquete arranca sin AGIX y conserva políticas
locales, auditoría y restricciones morales/legales mientras deja desactivados
los adaptadores avanzados. El mismo archivo permite alternar entre:

- `local_safe`: AGIX no disponible; se aplican políticas locales.
- `degraded`: versión AGIX no compatible; se desactivan capacidades avanzadas.
- `strict_compatible`: AGIX requerido y compatible activo.

Variables relevantes:

- `AGICORE_QUALIA_PROFILE`: ruta a un perfil alternativo.
- `AGIX_REQUIRE_RUNTIME=true`: exige runtime real y bloquea el arranque si AGIX falta o no es compatible.
- `AGIX_RUNTIME_PROFILE=strict_compatible`: selecciona modo estricto de forma explícita.

## Flujo de decisión seguro

1. La entrada se normaliza como payload con tarea, contexto, prompt, tokens o tool call.
2. `CoreQualiaEngine.govern_decision()` llama a Qualia antes de ejecutar la decisión.
3. `SafetyGate.must_block()` evalúa señales `blocked`, decisión moral, acción legal y clasificación ética.
4. Si hay bloqueo, se devuelve un objeto auditable con razón, restricciones, alternativa segura y trazas; no se invoca el backend.
5. Si se permite, la decisión se ejecuta y `after_decision()` integra resultado y feedback.
6. En streaming, la salida se revisa por ventanas solapadas y evaluación final obligatoria.

## Estado PyPI

- El nombre de distribución declarado es `gpt-oss-agi` y la versión local actual es `0.0.1`.
- La publicación a PyPI está aislada en `.github/workflows/publish.yml` y solo se ejecuta por release publicada o `workflow_dispatch` confirmado con `publish`.
- El workflow usa entorno protegido `release` y Trusted Publishing; no se publica desde pushes normales a `main`.
