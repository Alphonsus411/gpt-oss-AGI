# Integración continua y publicación

La automatización de GitHub Actions está separada en dos workflows para evitar que una subida normal a `main` pueda publicar paquetes en PyPI.

## CI (`.github/workflows/CI.yml`)

El workflow `CI` se ejecuta en `pull_request`, en cualquier `push` de rama y manualmente con `workflow_dispatch`. No escucha eventos de tags ni de releases, no tiene permisos OIDC y no contiene pasos de publicación.

Jobs principales:

1. **Tests without AGIX**: instala el proyecto con dependencias de test, desinstala `agix` y ejecuta toda la suite que no requiere recursos externos con `AGIX_RUNTIME_PROFILE=local_safe`, salvo los casos del endpoint heredado en `tests/test_api_endpoints.py`. También desactiva el requisito estricto del runtime para validar que el modo seguro/fallback funciona sin AGIX instalado.
2. **Tests with `agix==1.9.0`**: instala explícitamente `agix==1.9.0`, comprueba la versión instalada y ejecuta la suite que no requiere recursos externos con el perfil degradado. Excluye los casos del endpoint heredado en `tests/test_api_endpoints.py` y, temporalmente, seis pruebas unitarias incompatibles con el perfil global `degraded`; cada una se deselecciona por su identificador completo para conservar el resto de la cobertura hasta corregirlas.
3. **Real Harmony and Responses API**: ejecuta `tests/test_responses_api.py` usando el paquete real `openai-harmony` y el servidor Responses API del repositorio.
4. **Ruff check**: ejecuta `ruff check .`.
5. **Type checking with pyright**: instala el paquete en modo editable y ejecuta `pyright`.
6. **Build wheel and sdist**: ejecuta `python -m build` y sube los artefactos `dist/*`.
7. **Clean install wheel and sdist**: descarga los artefactos de build e instala por separado el wheel y el sdist en un `venv` limpio.
8. **Dependency audit with pip-audit**: instala el proyecto y ejecuta `pip-audit`.

El benchmark opcional de Qualia se mantiene como job manual y no bloqueante. Solo se ejecuta al lanzar el workflow manualmente con `run_qualia_benchmark=true`.

## Publicación PyPI (`.github/workflows/publish.yml`)

La publicación está aislada en el workflow `Publish to PyPI`. Solo se puede ejecutar en estas situaciones:

- cuando se publica una release de GitHub (`release: published`);
- manualmente con `workflow_dispatch`, escribiendo `publish` en `confirm_publish`.

El job usa el entorno protegido `release` y Trusted Publishing mediante OIDC (`id-token: write`). La protección del entorno `release` debe configurarse en GitHub con revisores obligatorios o las reglas internas del proyecto. El workflow no se ejecuta en `push` normal a `main` ni en pushes de ramas.

## Recomendaciones de mantenimiento

- Mantener la versión de AGIX sincronizada con `pyproject.toml`, `requirements.txt` y `agicore_core/config/qualia_profile.json`.
- Si `ruff`, `pyright` o `pip-audit` empiezan a fallar por deuda técnica existente, corregir la configuración o las exclusiones en un cambio separado antes de hacerlos obligatorios para protección de rama.
- Revisar periódicamente que `publish.yml` siga apuntando al entorno protegido `release` y que el proyecto en PyPI tenga Trusted Publishing configurado para este repositorio.
