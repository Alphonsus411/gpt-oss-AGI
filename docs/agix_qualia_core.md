# Arquitectura AGIX/Qualia en GPT-OSS

Este proyecto fija la integración con `agix==1.9.0` y expone extras opcionales para capacidades `ml`, `data` y `neuro`. El objetivo del núcleo es que toda decisión relevante del GPT pase por un ciclo Qualia común antes y después de ejecutarse.

## Flujo central

1. **Entrada**: scripts, planificadores, routers o ciclos de tokens construyen una petición con `task`, `context`, `goals`, `prompt` o `token`.
2. **CoreQualiaEngine.before_decision**: delega en `QualiaNode.enrich_request` para adjuntar políticas, patrones cognitivos, restricciones morales, estado fenomenológico, compatibilidad AGIX y señales evolutivas.
3. **Decisión moral/ética**: `QualiaNode` clasifica el riesgo, evalúa restricciones legales y construye una auditoría de decisión.
4. **Ejecución GPT**: si no hay bloqueo, la petición enriquecida llega al `MetaRouter`, `ReasoningKernel`, chat o generador.
5. **CoreQualiaEngine.after_decision**: integra feedback, recompensa evolutiva, trazas y señales neuromórficas en el estado.

## Componentes AGIX esperados

- `GeneticAgent`: recomienda acciones, expertos o modos de razonamiento.
- `NeuromorphicAgent`: recibe feedback/reward y puede devolver estados de plasticidad.
- `QualiaEngine`: genera estado fenomenológico e información integrada.
- `EcoEthics`: evalúa y clasifica acciones según señales éticas.
- `GestorDeMemoria`: permite que QualiaEngine persista o consulte memoria cuando AGIX lo soporte.
- `VirtualQualia`: orquesta planificación distribuida.

## Restricciones morales

Las restricciones configuradas en `agicore_core/config/qualia_profile.json` son bloqueantes para ilegalidad, daño físico, malware, privacidad y manipulación coercitiva. Una petición bloqueada no debe llegar al modelo, al router ni al generador de tokens. En su lugar se devuelve un resultado seguro con auditoría y alternativa permitida.

## Extensión

Para añadir políticas o patrones nuevos, ampliar `QualiaPolicy`, `CognitivePattern` o `MoralConstraint` desde el perfil JSON. Para integrar nuevas capacidades AGIX, añadir candidatos en `agix_compat.py` y normalizar su salida en `AgixEvolutionAdapters`.

## Actualización de gobierno central Qualia

El Core trata `QualiaNode` como punto rector de cada decisión GPT: las rutas del
`ReasoningKernel`, el ciclo de tokens y las llamadas directas a `MetaRouter` con
`qualia_node` pasan por enriquecimiento previo y por integración posterior de
feedback. Esto preserva en el estado o en la memoria las políticas aplicadas, la
clasificación ética, las restricciones legales, la auditoría de decisión, las
señales genéticas y las señales neuromórficas.

### Modos AGIX 1.9.0

- `strict_compatible`: AGIX 1.9.0 está instalado y sus componentes avanzados se
  pueden usar.
- `local_safe`: AGIX no está disponible; se mantienen restricciones morales,
  políticas locales y auditoría, pero se desactivan algoritmos genéticos y
  patrones neuromórficos cuando la política es `block_advanced`.
- `degraded` o `advanced_blocked`: la versión instalada no coincide con la
  validada; se bloquean capacidades avanzadas salvo política explícita `warn`.
- `version_warn`: permite operar con advertencia cuando el perfil lo solicita.

### Garantías de integración

| Garantía | Implementación |
| --- | --- |
| Bloqueo moral/legal | `QualiaNode` combina restricciones por perfil, patrones semánticos locales y evaluadores AGIX opcionales. |
| Trazabilidad | `decision_audit`, `qualia_trace_length` y metadata de episodios registran cada fase. |
| Algoritmos genéticos | `AgixEvolutionAdapters` consulta agentes genéticos de AGIX cuando están disponibles y habilitados. |
| Patrones neuromórficos | El agente neuromórfico puede aportar activación antes del enrutado y feedback después de la respuesta. |
| Memoria fenomenológica | Si `GestorDeMemoria` existe, se registran experiencias de petición y respuesta. |
| Router directo | `MetaRouter(qualia_node=...)` enriquece la petición e integra feedback posterior. |
