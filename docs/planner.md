# Planner

El `Planner` coordina la intención global del agente, administra una cola de metas priorizadas y activa submodos de razón.
Ayuda a estructurar tareas complejas definiendo objetivos claros y ajustando el comportamiento del modelo.

## Establecer metas

```python
from gpt_oss.planner import Planner

planner = Planner()
planner.set_intention("Investigar sobre AGI")
planner.add_goal("Buscar artículos relevantes", prioridad=2)
planner.add_goal("Resumir resultados", prioridad=1)

siguiente_meta = planner.get_next_goal()
print(siguiente_meta)
```

## Activar submodos

```python
planner.activate_mode("creative")
print(planner.current_mode())
print(planner.get_mode_parameters())
```

## Uso con memoria estratégica

El `Planner` puede aprovechar `StrategicMemory` para ajustar automáticamente
los parámetros del modo en función de experiencias previas. Al activar un modo
se consultan episodios anteriores exitosos del mismo tipo y se promedia la
temperatura registrada en ellos.

```python
from gpt_oss.strategic_memory import StrategicMemory, Episode
from datetime import datetime

memory = StrategicMemory()
memory.add_episode(
    Episode(timestamp=datetime.now(), input="i", action="a", outcome="success",
            metadata={"mode": "creative", "temperature": 0.8})
)

planner = Planner(memory=memory)
planner.activate_mode("creative")
print(planner.get_mode_parameters())  # temperatura ajustada ~0.8

# Registrar un nuevo episodio
planner.record_episode("pregunta", "respuesta", "success")
```

## Tests

Para ejecutar las pruebas relacionadas con el `Planner`:

```bash
pytest tests/test_planner.py tests/test_goal_planner.py tests/test_planner_memory.py
```
