# MetaEvaluator

`MetaEvaluator` recopila métricas de los ciclos del núcleo y aprende de ellas
para proponer mejoras estructurales.

## Almacenamiento de conocimiento

- **Métricas agregadas**: promedios de los valores numéricos observados en el
  historial.
- **Patrones de fallos**: recuento de mensajes de error detectados.
- **Sugerencias**: recomendaciones generadas tras cada reflexión.

La llamada a `ReasoningKernel.run` finaliza con
`evaluator.reflexionar(history)`, lo que actualiza estos registros.

## Persistencia entre sesiones

El evaluador permite serializar su estado para reutilizar lo aprendido:

```python
import json
from agicore_core.meta_evaluator import MetaEvaluator

# Guardar
with open("evaluator_state.json", "w", encoding="utf8") as fh:
    json.dump(evaluator.exportar_estado(), fh)

# Cargar
with open("evaluator_state.json", encoding="utf8") as fh:
    evaluator.cargar_estado(json.load(fh))
```

Así, el conocimiento acumulado (métricas, patrones y sugerencias) puede
recuperarse en una nueva ejecución del sistema.
