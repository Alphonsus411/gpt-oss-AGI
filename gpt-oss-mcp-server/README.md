# Servidores MCP para herramientas de referencia de gpt-oss

Este directorio contiene servidores MCP para las herramientas de referencia en el repositorio [gpt-oss](https://github.com/openai/gpt-oss).
Puedes configurar estas herramientas detrás de servidores MCP y usarlas en tus aplicaciones.
Para servicios de inferencia que se integren con MCP, también puedes utilizarlas como herramientas de referencia.

En particular, este directorio contiene un script `build-system-prompt.py` que generará exactamente el mismo prompt del sistema que `reference-system-prompt.py`.
El script del prompt del sistema muestra todas las precauciones necesarias para descubrir automáticamente las herramientas y construir el prompt del sistema antes de enviarlo a Harmony.

## Uso

```bash
# Instala las dependencias
uv pip install -r requirements.txt
```

```bash
# Asumimos que harmony y gpt-oss están instalados
uv pip install mcp[cli]
# iniciar los servidores
mcp run -t sse browser_server.py:mcp
mcp run -t sse python_server.py:mcp
```

Ahora puedes utilizar MCP inspector para experimentar con las herramientas.
Una vez abierto, establece SSE en `http://localhost:8001/sse` y `http://localhost:8000/sse` respectivamente.

Para comparar el prompt del sistema y ver cómo construirlo mediante el descubrimiento de servicios MCP, consulta `build-system-prompt.py`.
Este script generará exactamente el mismo prompt del sistema que `reference-system-prompt.py`.
