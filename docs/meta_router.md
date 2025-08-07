# Flujo de enrutamiento

El archivo `meta_router.py` introduce la clase `MetaRouter`, un punto central
para enviar solicitudes a distintos módulos basándose en metadatos declarados.

1. El cliente construye un diccionario con las claves `task`, `context` y
   `goals` (lista de metas) describiendo su petición.
2. `MetaRouter` calcula una puntuación para cada experto registrado según las
   coincidencias con esos metadatos.
3. El experto con mayor puntuación recibe la solicitud completa mediante su
   método `handle`.

Este diseño permite ampliar el sistema registrando nuevos expertos sin
modificar el núcleo del enrutador.
