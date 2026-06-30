# Arquitectura AGIX/Qualia en GPT-OSS

Este proyecto fija la integración con `agix==1.9.0` y expone extras opcionales para capacidades `ml`, `data` y `neuro`. El objetivo del núcleo es que toda decisión relevante del GPT pase por un ciclo Qualia común antes y después de ejecutarse.

## Flujo central

1. **Entrada**: scripts, planificadores, routers o ciclos de tokens construyen una petición con `task`, `context`, `goals`, `prompt` o `token`.
2. **CoreQualiaEngine.govern_decision**: delega en `QualiaNode.enrich_request` para adjuntar políticas, patrones cognitivos, restricciones morales, estado fenomenológico, compatibilidad AGIX y señales evolutivas; además centraliza si la decisión debe bloquearse antes de tocar el GPT.
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
| Router directo | `MetaRouter(qualia_node=...)` enriquece la petición, devuelve resultados bloqueados auditables sin llamar al experto e integra feedback posterior. |
| Planificador AGIX | `agicore_core.Planner` crea `CoreQualiaEngine` por defecto y bloquea planes ilegales antes de `VirtualQualia.broadcast_state`. |
| Generación CLI | `QualiaControlledTokenGenerator` consulta Qualia antes de pedir el siguiente token y después de validar el token decodificado. |

### Dimensión neuromórfica

El perfil `qualia_profile.json` configura `neuromorphic_agent.input_size` en
`4`, alineado con el vector que el Core calcula para AGIX:

1. longitud normalizada del texto;
2. número normalizado de metas;
3. número normalizado de restricciones violadas;
4. puntuación ética.

Si un despliegue AGIX usa otra dimensión, `AgixEvolutionAdapters` ajusta el
vector al `input_size` configurado mediante truncado explícito o relleno con
ceros, y expone `neuromorphic_input_size` y `neuromorphic_input_vector` en las
señales auditables.

## Integración estructurada de capacidades AGIX adicionales

El Core ahora separa las capacidades AGIX en capas auditables:

1. **Compatibilidad**: `agicore_core.agix_compat` detecta los componentes documentados en AGIX 1.9.0, incluidos `MetaLearner`, `Ontology`, `LatentRepresentation`, `NeuroSymbolicBridge`, `EvaluationMetrics`, `ConceptClassifier`, `HeuristicConceptCreator`, `EmotionSimulator` y `AttentionFocus`.
2. **Adaptadores cognitivos**: `AgixCognitiveAdapters` normaliza conceptos, foco atencional, estados emocionales, representaciones latentes y métricas de evaluación. Si AGIX no está instalado, devuelve señales locales seguras y degradación explícita.
3. **SafetyGate**: centraliza el bloqueo moral/legal para que router, planner, inferencia, entrenamiento y generación puedan consultar la misma decisión Qualia antes de tocar el GPT.
4. **Memoria inferencial**: `StrategicMemory` separa episodios utilizables, auditoría y aprendizaje rechazado. Las hipótesis inferidas solo se consolidan desde episodios permitidos.
5. **Training bridge**: `QualiaTrainingBridge` filtra señales de entrenamiento/evaluación antes de convertirlas en episodios de memoria o feedback adaptativo.
6. **Puente neuro-simbólico**: `CoreNeuroSymbolicBridge` expone una interfaz estable para extraer conceptos y representaciones neuro-simbólicas con fallback local.

Las políticas morales siguen siendo rígidas: cualquier payload con `blocked`, `blocked_illegal_or_unsafe_decision` o decisión moral `allowed=false` queda excluido de router/backend y no alimenta memoria inferencial ni señales de entrenamiento.
