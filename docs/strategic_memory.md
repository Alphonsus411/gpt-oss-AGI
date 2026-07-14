# Memoria episódica estratégica

La memoria estratégica permite al agente recordar episodios pasados y usar esa información para tomar mejores decisiones. Cada episodio incluye momento, entrada, acción, resultado y metadatos. En este fork, la memoria está diseñada para ser segura por defecto: redacta secretos y evita que episodios bloqueados por Qualia alimenten aprendizaje inferencial.

## Backends disponibles

### RAM por defecto

`StrategicMemory()` crea un `InMemoryMemoryBackend`. Es útil para pruebas, ejecución local y agentes efímeros. Soporta TTL, límites por colección y transacciones con rollback mediante copia interna.

### SQLite persistente

`SQLiteMemoryBackend` persiste claves y episodios en dos tablas (`kv` y `episodes`). Mantiene la misma interfaz que el backend RAM, añade persistencia transaccional y permite cerrar la conexión con `close()`.

```python
from gpt_oss.strategic_memory import SQLiteMemoryBackend, StrategicMemory

backend = SQLiteMemoryBackend("memory.sqlite", max_episodes=1000)
mem = StrategicMemory(backend=backend)
mem.save("plan", {"estado": "inicial"})
mem.persist()
backend.close()
```

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

## Redacción de secretos

Antes de guardar datos, `SecretRedactor` redacta valores sensibles en cadenas y estructuras anidadas. Cubre claves tipo `api_key`, `authorization`, `bearer`, `credential`, `password`, `secret` y `token`, además de patrones comunes como `sk-...`, `Bearer ...` y pares `token=...`.

```python
from gpt_oss.strategic_memory import StrategicMemory

mem = StrategicMemory()
mem.save("cred", {"api_key": "sk-1234567890abcdef"})
assert mem.get("cred")["api_key"] == "[REDACTED]"
```

## Colecciones de aprendizaje, auditoría y rechazo

- `add_episode()` añade episodios a aprendizaje solo si no fueron bloqueados o rechazados por Qualia.
- `add_audit_episode()` registra trazabilidad sin alimentar inferencia.
- `add_rejected_learning()` guarda señales rechazadas y también las audita.

Un episodio se rechaza para aprendizaje si su estado es `blocked_by_qualia` o `rejected_learning`, si la acción de política Qualia indica bloqueo, o si el resultado contiene `blocked: true`.

## Consolidación inferencial segura

`consolidate_from_episodes()` agrupa episodios seguros por tarea, contexto y metas; exige soporte mínimo; calcula confianza por éxitos; y adjunta restricciones éticas observadas. Las señales bloqueadas quedan en `discarded_signals` y no se convierten en hipótesis.

## Integración con `MetaRouter`

`MetaRouter` puede consultar los episodios almacenados para ajustar la puntuación de cada experto según su historial.

```python
from datetime import datetime
from meta_router import MetaRouter
from gpt_oss.strategic_memory import Episode, StrategicMemory

memory = StrategicMemory()
router = MetaRouter(memory=memory)
router.register("traductor", Translator(), tasks=["translate"], contexts=["cli"], goals=["en-es"])

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

El `Planner` consulta la memoria para ajustar automáticamente los parámetros del modo activo en función de episodios previos.

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
