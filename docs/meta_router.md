# Flujo de enrutamiento

El archivo `meta_router.py` introduce la clase `MetaRouter`, un punto central
para enviar solicitudes a distintos módulos basándose en metadatos declarados.

1. El cliente construye un diccionario con las claves **obligatorias**
   `task`, `context` y `goals` (lista de metas) describiendo su petición.
2. `MetaRouter` calcula una puntuación para cada experto registrado según las
   coincidencias con esos metadatos y la prioridad declarada por el experto.
3. El experto con mayor puntuación recibe la solicitud completa mediante su
   método `handle`.

Este diseño permite ampliar el sistema registrando nuevos expertos sin
modificar el núcleo del enrutador.

## Registro de expertos

Los expertos se registran mediante `MetaRouter.register`. Cada experto debe
proporcionar un objeto (`module`) con un método `handle` y puede acompañarse de
metadatos que guíen la selección:

```python
router = MetaRouter()
router.register(
    "sumador",
    SumModule(),
    tasks=["math"],
    contexts=["cli"],
    goals=["calculate"],
    priority=1,
)
```

`tasks`, `contexts` y `goals` son listas de cadenas que indican para qué tipos
de solicitud es adecuado el experto. `priority` permite desempatar cuando las
coincidencias son similares.

## Heurística de selección

La función `select_expert` puntúa a cada experto. La heurística otorga:

- `+1` si `task` coincide con las tareas anunciadas.
- `+1` si `context` coincide con los contextos anunciados.
- `+1` por cada meta en `goals` que aparezca entre las metas del experto.
- `+priority` declarado explícitamente.

El experto con mayor puntuación es elegido. Si existe empate, se usa orden
alfabético sobre el nombre del experto como regla de desempate.

## Parámetros obligatorios y ejemplo de solicitud

`MetaRouter.route` espera un diccionario que incluya `task`, `context` y
`goals`. Cualquier otro campo se envía directamente al experto seleccionado:

```python
request = {
    "task": "math",
    "context": "cli",
    "goals": ["calculate"],
    "payload": 42,
}
router.route(request)
```

## Flujo `planner → reasoning_kernel → meta_router`

```text
[Planner] --plan--> [ReasoningKernel]
      |                 |
      |   task/context/goals + step
      |                 v
      |------------> [MetaRouter] --> experto.handle(request)
```

Un planificador genera una lista de pasos. `ReasoningKernel` toma esos pasos,
les añade los metadatos (`task`, `context`, `goals`) y delega cada uno al
`MetaRouter`, que decide qué experto debe atenderlo.

## Ejemplo completo de configuración

```python
router = MetaRouter()
router.register(
    "traductor",
    Translator(),
    tasks=["translate"],
    contexts=["cli"],
    goals=["en-es"],
)
router.register(
    "sumador",
    SumModule(),
    tasks=["math"],
    contexts=["cli"],
    goals=["calculate"],
)

kernel = ReasoningKernel(router)
plan = [{"task": "math", "payload": 2}, {"task": "translate", "text": "hola"}]
results = kernel.execute_plan(plan, task="math", context="cli", goals=["calculate"])
```

En este ejemplo, el primer paso será atendido por `sumador` y el segundo por
`traductor`, demostrando cómo la selección automática depende de los metadatos.
