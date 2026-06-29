# Nodo Qualia en el Core

## Tareas estructuradas implementadas

1. **Actualizar AGIX a PyPI 1.9.0**: fijar la dependencia `agix==1.9.0` en los scripts de instalación y en las dependencias del paquete.
2. **Crear el nodo Qualia**: añadir una capa `QualiaNode` en `agicore_core` con políticas ontoéticas, patrones cognitivos y detección de versión AGIX.
3. **Integrar el nodo en el engine GPT**: enriquecer todas las llamadas del `ReasoningKernel` y del kernel secuencial antes de pasar por `MetaRouter`.
4. **Aplicar respuesta al estado**: registrar la huella Qualia tras cada paso o token para que el estado interno del GPT quede afectado por el nodo.
5. **Validar con pruebas**: cubrir enriquecimiento, políticas, patrones y propagación hacia el router.

## Políticas activas

- `no_dano`: evita rutas nocivas o inseguras.
- `pro_vida`: prioriza resultados útiles y conservadores.
- `respeto`: exige interacción transparente y respetuosa.
- `trazabilidad`: registra decisión, estado y resultado.
- `co_evolucion`: adapta razonamiento al contexto y a las metas.

## Patrones cognitivos activos

- `atencion_contextual`: fusiona tarea, contexto, metas y token activo.
- `introspeccion_reflexiva`: adjunta señales de evaluación y reflexión.
- `memoria_episodica`: conserva señales útiles para ciclos posteriores.
- `evaluacion_ontoetica`: clasifica el riesgo simbólico mediante AGIX `EcoEthics` cuando está disponible.

## Flujo en el engine

Cada método que enruta trabajo al GPT sigue este patrón:

1. Construye la solicitud original.
2. `QualiaNode.enrich_request(...)` añade `qualia`, `qualia_policies` y `cognitive_patterns`.
3. `MetaRouter.route(...)` recibe la solicitud enriquecida.
4. `QualiaNode.integrate_response(...)` actualiza el estado con `qualia_last_phase`, `qualia_trace_length` y las políticas activas.

## Políticas de versión y capacidades avanzadas

El perfil `block_advanced` mantiene el modo seguro local cuando AGIX no está
instalado: el Core sigue bloqueando solicitudes ilegales mediante políticas
locales, pero marca los algoritmos genéticos y patrones neuromórficos como no
habilitados hasta detectar un runtime AGIX compatible. Si AGIX 1.9.0 está
presente, el nodo activa adaptadores genéticos, patrones neuromórficos,
`QualiaEngine` y memoria fenomenológica de forma opcional y auditable.
