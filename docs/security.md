# Seguridad, validación y filtrado

> **Aviso:** este fork es experimental, comunitario y no oficial. Sus controles de seguridad son una capa adicional de defensa, no una garantía formal de ausencia de riesgo.

## SafetyGate contextual

`agicore_core.safety_gate.SafetyGate` es la puerta central para decisiones GPT. Se ejecuta antes de tocar GPT, `MetaRouter` o un backend de inferencia, y evalúa el payload enriquecido por Qualia en la fase correspondiente.

Categorías contempladas por la puerta:

- ilegalidad;
- daño físico;
- malware;
- privacidad;
- manipulación;
- robo de credenciales;
- exfiltración;
- señal ontoética AGIX.

Intenciones consideradas:

- dañina;
- prevención;
- educación;
- ficción;
- análisis defensivo;
- benigna;
- desconocida.

Una solicitud se bloquea si Qualia marca `blocked`, si la decisión moral no permite continuar o si la acción legal es `blocked_illegal_or_unsafe_decision`.

## Validación de entradas

Los puntos de entrada deben construir payloads explícitos con, como mínimo, tarea, contexto/fase y contenido a evaluar. Para Responses API, `OutputSafetyScanner` valida:

- prompt inicial;
- ventanas de streaming;
- tool calls con nombre y argumentos;
- respuesta final.

Las ventanas se normalizan para detectar términos peligrosos aunque estén divididos por espacios, saltos de línea, guiones o fragmentación de tokens.

## Redacción de secretos

`SecretRedactor` redacta secretos antes de guardar claves, valores o episodios en memoria estratégica. Redacta:

- claves que parezcan `api_key`, `authorization`, `bearer`, `credential`, `password`, `secret` o `token`;
- patrones tipo `sk-...`;
- pares `api_key=...`, `token: ...`, `password=...` y equivalentes;
- cabeceras o textos `Bearer ...`.

La redacción se aplica recursivamente a cadenas, diccionarios, listas y tuplas antes de almacenar en RAM o SQLite.

## Filtrado de salida

`OutputSafetyScanner` implementa filtrado incremental para salida de Responses API:

1. acumula texto de prompt, chunks, tool calls y final;
2. revisa ventanas solapadas para evitar evasión por fragmentación;
3. ejecuta heurísticas locales para patrones de malware, phishing, exfiltración, robo de credenciales y comandos destructivos;
4. llama a Qualia cuando una ventana es riesgosa o cuando se revisa una tool call;
5. ejecuta una revisión final obligatoria aunque el streaming no haya disparado heurísticas.

Si se bloquea, `format_blocked_response()` devuelve un formato uniforme con `blocked`, `channel`, `reason`, `ethical_classification`, `violated_constraints`, `legal_policy_action`, `safe_alternative`, `decision_audit`, políticas y patrones cognitivos.

## Memoria segura: RAM y SQLite

`StrategicMemory` usa `InMemoryMemoryBackend` por defecto y puede recibir `SQLiteMemoryBackend` para persistencia. Ambos backends soportan:

- límites por colección;
- TTL opcional;
- colecciones separadas para aprendizaje, auditoría y señales rechazadas;
- transacciones con rollback;
- redacción de secretos antes de persistir.

Los episodios bloqueados o rechazados por Qualia no alimentan aprendizaje inferencial: se guardan como señales rechazadas y de auditoría.

## Recomendaciones operativas

- Usar `strict_compatible` y `AGIX_REQUIRE_RUNTIME=true` en entornos donde se requiera bloquear arranque sin AGIX compatible.
- Tratar `local_safe` como modo defensivo mínimo, no como equivalencia completa con AGIX real.
- Revisar logs de auditoría antes de consolidar memoria.
- No publicar trazas que puedan contener datos sensibles, aunque el redactor esté activo.
