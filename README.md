<img alt="gpt-oss-120" src="./docs/gpt-oss.svg">
<p align="center">
  <a href="https://gpt-oss.com"><strong>Prueba gpt-oss</strong></a> ·
  <a href="https://cookbook.openai.com/topic/gpt-oss"><strong>Guías</strong></a> ·
  <a href="https://openai.com/index/gpt-oss-model-card"><strong>Ficha del modelo</strong></a> ·
  <a href="https://openai.com/index/introducing-gpt-oss/"><strong>Blog de OpenAI</strong></a>
</p>
<p align="center">
  <strong>Descarga <a href="https://huggingface.co/openai/gpt-oss-120b">gpt-oss-120b</a> y <a href="https://huggingface.co/openai/gpt-oss-20b">gpt-oss-20b</a> en Hugging Face</strong>
</p>

<br>

> **Aviso sobre este fork:** `gpt-oss-agi` es un fork comunitario experimental y **no oficial** de OpenAI. No modifica ni redistribuye pesos de los modelos `gpt-oss`, no demuestra ni afirma alcanzar AGI, e integra una capa experimental de gobierno AGIX/Qualia para evaluación, planificación y control de seguridad. El nombre de distribución Python cambia a `gpt-oss-agi`, pero los imports públicos se mantienen como `gpt_oss` y `agicore_core`.

Bienvenido a la serie gpt-oss, [los modelos de pesos abiertos de OpenAI](https://openai.com/open-models/) diseñados para un razonamiento potente, tareas agénticas y una amplia variedad de casos de uso para desarrolladores.

Estamos liberando dos variantes de estos modelos abiertos:

- `gpt-oss-120b` — para producción y casos de uso de alto razonamiento que encajan en una GPU H100 (117B parámetros con 5.1B activos)
- `gpt-oss-20b` — para menor latencia y casos de uso locales o especializados (21B parámetros con 3.6B activos)

Ambos modelos fueron entrenados usando nuestro [formato de respuesta harmony][harmony] y solo deben utilizarse con este formato; de lo contrario, no funcionarán correctamente.

### Destacados

- **Licencia Apache 2.0 permisiva:** Construye libremente sin restricciones copyleft ni riesgos de patentes.
- **Esfuerzo de razonamiento configurable:** Ajusta fácilmente el esfuerzo de razonamiento (bajo, medio, alto) según las necesidades de tu caso de uso y latencia.
- **Cadena de pensamiento completa:** Acceso total al proceso de razonamiento del modelo para facilitar la depuración y aumentar la confianza en las salidas. No destinado a mostrarse a usuarios finales.
- **Afinable:** Personaliza completamente los modelos mediante fine-tuning de parámetros.
- **Capacidades agénticas:** Usa las capacidades nativas del modelo para llamadas a funciones, [navegación web](#browser), [ejecución de código Python](#python) y salidas estructuradas.
- **Cuantización nativa MXFP4:** Los modelos se entrenan con precisión MXFP4 para la capa MoE, permitiendo que `gpt-oss-120b` funcione en una sola GPU H100 y `gpt-oss-20b` dentro de 16GB de memoria.

### Ejemplos de inferencia

#### Transformers

Puedes usar `gpt-oss-120b` y `gpt-oss-20b` con Transformers. Si utilizas la plantilla de chat de Transformers se aplicará automáticamente el [formato de respuesta harmony][harmony]. Si usas `model.generate` directamente, necesitas aplicar el formato harmony manualmente usando la plantilla de chat o nuestro paquete [`openai-harmony`][harmony].

```python
from transformers import pipeline
import torch

model_id = "openai/gpt-oss-120b"

pipe = pipeline(
    "text-generation",
    model=model_id,
    torch_dtype="auto",
    device_map="auto",
)

messages = [
    {"role": "user", "content": "Explica la mecánica cuántica de forma clara y concisa."},
]

outputs = pipe(
    messages,
    max_new_tokens=256,
)
print(outputs[0]["generated_text"][-1])
```

[Aprende más sobre cómo usar gpt-oss con Transformers.](https://cookbook.openai.com/articles/gpt-oss/run-transformers)

### Otros detalles

Para información sobre vLLM, PyTorch/Triton/Metal, Ollama, LM Studio y otros temas, consulta la documentación original en inglés.

Visita también la lista [awesome-gpt-oss](awesome-gpt-oss.es.md) para encontrar herramientas y proyectos de la comunidad.

### Licencia

Este proyecto se distribuye bajo la Licencia Apache 2.0. Puedes encontrar el texto original en `LICENSE` y una traducción al español en `LICENSE.es`.

[harmony]: https://github.com/openai/harmony

## Sincronización con upstream

Consulta [`docs/upstream_sync.md`](docs/upstream_sync.md) para ver el remoto upstream configurado, el commit base usado para comparación y las extensiones del fork que deben preservarse durante futuras sincronizaciones.

## Integración AGIX/Qualia

El Core fija `agix==1.9.0` y usa `agicore_core.QualiaNode` como capa rectora de planificación, enrutado y ciclo de tokens. Qualia aplica políticas ontoéticas, restricciones morales/legales, patrones cognitivos y señales evolutivas antes de que una solicitud llegue al GPT o al `MetaRouter`.

Perfiles opcionales para capacidades avanzadas de AGIX:

```bash
pip install -e .[agix-neuro]   # módulos neuroinspirados de AGIX
pip install -e .[agix-ml]      # módulos ML de AGIX
pip install -e .[agix-data]    # integración de datos
pip install -e .[agix-full]    # perfil completo ml+data+neuro
```

Por defecto, `agicore_core/config/qualia_profile.json` arranca en modo seguro local (`runtime_profile=local_safe`) con `require_agix_runtime=false`, por lo que una instalación limpia funciona sin AGIX y mantiene políticas locales, auditoría y restricciones morales/legales con adaptadores avanzados desactivados. El modo degradado y el modo estricto siguen disponibles: se puede apuntar a un perfil alternativo con `AGICORE_QUALIA_PROFILE`, exigir runtime real con `AGIX_REQUIRE_RUNTIME=true` y seleccionar explícitamente el modo estricto con `AGIX_RUNTIME_PROFILE=strict_compatible`.

La API de Responses y los backends de inferencia pueden gobernarse con `CoreQualiaEngine`: cada petición se evalúa antes de invocar al GPT, y los tokens/chunks generados vuelven a pasar por Qualia para bloquear contenido ilegal o inseguro antes de emitirse. Las respuestas bloqueadas comparten un formato auditable con `reason`, `legal_policy_action`, `violated_constraints`, `safe_alternative` y `decision_audit`.

## CI y publicación

La integración continua está documentada en [`docs/ci.md`](docs/ci.md). El workflow principal de CI valida pruebas sin AGIX, pruebas con `agix==1.9.0`, Harmony/Responses API reales, lint con Ruff, type checking con Pyright, build de wheel/sdist, instalación limpia de artefactos y auditoría con `pip-audit`.

La publicación a PyPI está separada en un workflow dedicado de release/manual con entorno protegido `release`; no se publica nunca desde un `push` normal a `main`.

## Arquitectura, seguridad y memoria del fork

Documentación ampliada:

- [`docs/architecture.md`](docs/architecture.md): base upstream, módulos preservados, capas Qualia/AGIX, perfiles AGIX, flujo de decisión y estado PyPI.
- [`docs/security.md`](docs/security.md): SafetyGate contextual, validación de entradas, redacción de secretos, filtrado de salida y recomendaciones operativas.
- [`docs/strategic_memory.md`](docs/strategic_memory.md): backends RAM/SQLite, colecciones de auditoría/rechazo y consolidación inferencial segura.
- [`docs/benchmarks.md`](docs/benchmarks.md): resultados registrados de Responses + Qualia y cómo reproducirlos.

### Resumen operativo del fork

- **Commit upstream usado como base común:** `4931694686fadfa74a80554473d32f7dd4d059f3`; último `upstream/main` observado en la sincronización documental: `d21f34ec3c1ede813adfbd83f07d2ad2eec7ff02`.
- **Módulos del fork a preservar:** `agicore_core/`, `gpt_oss/planner.py`, `meta_router.py`, `gpt_oss/strategic_memory.py`, `agicore_core/reasoning_kernel.py` y `gpt_oss/responses_api/inference/qualia_guard.py`.
- **Perfiles AGIX:** instalación base con `agix==1.9.0`; extras `agix-neuro`, `agix-ml`, `agix-data` y `agix-full`; perfiles runtime `local_safe`, `degraded` y `strict_compatible`.
- **SafetyGate contextual:** `CoreQualiaEngine`/`SafetyGate` evalúa solicitudes antes de GPT, router o backend, y devuelve bloqueos auditables con alternativa segura.
- **Validación y secretos:** la memoria estratégica redacta claves y patrones sensibles antes de almacenar en RAM o SQLite.
- **Filtrado de salida:** `OutputSafetyScanner` inspecciona prompt, tool calls, chunks de streaming y respuesta final mediante ventanas solapadas y Qualia.
- **Memoria:** `StrategicMemory` usa RAM por defecto y puede persistir en SQLite; separa aprendizaje, auditoría y señales rechazadas.
- **Benchmarks:** la última ejecución registrada midió `none`, `local_safe` y `strict_compatible`; el modo estricto quedó no disponible si faltan componentes AGIX completos.
- **PyPI:** el paquete se declara como `gpt-oss-agi` versión `0.0.1`; la publicación está separada en workflow protegido y no ocurre desde pushes normales a `main`.
- **Advertencia:** este fork es experimental, comunitario y no oficial; no representa a OpenAI, no redistribuye pesos y no garantiza AGI.
