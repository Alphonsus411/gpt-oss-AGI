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
