# Memoria episódica estratégica

La memoria estratégica permite al agente recordar episodios pasados y
usar esa información para tomar mejores decisiones. Cada episodio incluye
el momento en el que ocurrió, la entrada procesada, la acción realizada,
el resultado obtenido y metadatos asociados.

## API básica

### Almacenamiento de claves
```python
from gpt_oss.strategic_memory import StrategicMemory

mem = StrategicMemory()
mem.save("plan", "inicial")
mem.update("plan", "actualizado")
print(mem.get("plan"))
```

### Episodios
```python
from datetime import datetime
from gpt_oss.strategic_memory import Episode, StrategicMemory

mem = StrategicMemory()
mem.add_episode(
    Episode(
        timestamp=datetime.now(),
        input="hola",
        action="saludo",
        outcome="success",
        metadata={"tema": "demo"},
    )
)
print(mem.query({"tema": "demo"}))
print(mem.summarize())
```

## Integración con `MetaRouter`

`MetaRouter` puede consultar los episodios almacenados para ajustar la
puntuación de cada experto según su historial.

```python
from datetime import datetime
from meta_router import MetaRouter
from gpt_oss.strategic_memory import Episode, StrategicMemory

memory = StrategicMemory()
router = MetaRouter(memory=memory)
router.register("traductor", Translator(), tasks=["translate"], contexts=["cli"], goals=["en-es"])

# Registrar un fallo previo del experto "traductor"
memory.add_episode(
    Episode(
        timestamp=datetime.now(),
        input={},
        action="traductor",
        outcome="error",
        metadata={
            "task": "translate",
            "context": "cli",
            "goals": ["en-es"],
            "expert": "traductor",
            "status": "failure",
            "latency": 0,
        },
    )
)

router.route({"task": "translate", "context": "cli", "goals": ["en-es"], "text": "hola"})
```

## Integración con `Planner`

El `Planner` consulta la memoria para ajustar automáticamente los
parámetros del modo activo en función de episodios previos.

```python
from datetime import datetime
from gpt_oss.planner import Planner
from gpt_oss.strategic_memory import Episode, StrategicMemory

memory = StrategicMemory()
memory.add_episode(
    Episode(
        timestamp=datetime.now(),
        input="i",
        action="a",
        outcome="success",
        metadata={"mode": "creative", "temperature": 0.8},
    )
)

planner = Planner(memory=memory)
planner.activate_mode("creative")
print(planner.get_mode_parameters())
```
