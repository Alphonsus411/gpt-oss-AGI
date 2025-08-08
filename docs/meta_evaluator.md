# MetaEvaluator

`MetaEvaluator` recopila métricas de los ciclos del núcleo y aprende de ellas
para proponer mejoras estructurales.

## Instanciación junto a ReasoningKernel

El evaluador se integra en el ciclo principal a través de `ReasoningKernel`.
A continuación se muestra una configuración mínima que lo instancia junto al
planificador y el enrutador:

```python
from agicore_core import Planner, ReasoningKernel, MetaEvaluator
from meta_router import MetaRouter

router = MetaRouter()
planner = Planner()
evaluator = MetaEvaluator()
kernel = ReasoningKernel(planner, router, evaluator=evaluator)
```

En cada paso, el kernel envía las métricas al evaluador, que puede proponer
ajustes y actualizar su conocimiento interno.

## Parámetros y estrategias de reconfiguración

`MetaEvaluator` analiza los resultados de los ciclos buscando indicadores
numéricos o patrones de error. Sus principales campos de estado son:

- **historial_metricas**: resúmenes numéricos registrados en cada iteración.
- **metricas_agregadas**: promedios calculados tras llamar a `reflexionar`.
- **patrones_fallo**: conteo de mensajes de error detectados.
- **sugerencias**: cambios recomendados para la configuración interna.

La heurística de `sugerir_reconfiguracion` examina métricas como `error` y
`tiempo` para proponer ajustes. Por defecto:

- Si el error medio supera `0.5`, recomienda **disminuir la tasa de aprendizaje**.
- Si el tiempo medio es mayor que `1.0`, sugiere **optimizar componentes críticos**.

Estas reglas pueden ampliarse con umbrales y acciones específicos del dominio,
permitiendo estrategias de reconfiguración adaptadas a cada sistema.

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
