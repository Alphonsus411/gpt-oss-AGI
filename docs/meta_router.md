# Flujo de enrutamiento

El archivo `meta_router.py` introduce la clase `MetaRouter`, un punto central
para enviar solicitudes a distintos módulos.

1. El cliente construye un diccionario con la clave `module` que identifica el
   destino.
2. `MetaRouter` busca el módulo en su registro interno.
3. Si el módulo es `reasoning`, se invoca a `ReasoningKernel.execute_plan` con
   el plan provisto en `plan`.
4. Para cualquier otro módulo registrado se llama a su método `handle` y se
   le entrega el diccionario original.

Este diseño permite ampliar el sistema registrando nuevos módulos sin modificar
el núcleo del enrutador.
