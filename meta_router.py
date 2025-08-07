from __future__ import annotations

"""Enrutador central para delegar solicitudes entre módulos.

La clase :class:`MetaRouter` mantiene un registro de módulos y dirige cada
solicitud al destino adecuado. Por defecto se registra el
:class:`agicore_core.ReasoningKernel` bajo la clave ``"reasoning"``.
"""

from typing import Any, Dict

from agicore_core import ReasoningKernel


class MetaRouter:
    """Enrutador minimalista de solicitudes.

    Los módulos adicionales deben proporcionar un método ``handle`` que reciba
    un diccionario con la solicitud. Para el caso del módulo ``"reasoning"`` se
    utiliza :class:`ReasoningKernel` y se espera una clave ``"plan"`` con los
    pasos a ejecutar.
    """

    def __init__(self) -> None:
        self._modules: Dict[str, Any] = {}
        # Registro por defecto del kernel de razonamiento.
        self.register("reasoning", ReasoningKernel())

    def register(self, name: str, module: Any) -> None:
        """Registra un ``module`` bajo el identificador ``name``."""

        self._modules[name] = module

    def route(self, request: Dict[str, Any]) -> Any:
        """Envía ``request`` al módulo adecuado.

        Parameters
        ----------
        request:
            Diccionario que contiene al menos la clave ``"module"`` que indica
            el destino.
        """

        module_name = request.get("module")
        if module_name not in self._modules:
            raise ValueError(f"Módulo no registrado: {module_name}")

        module = self._modules[module_name]
        if isinstance(module, ReasoningKernel):
            plan = request.get("plan", [])
            return module.execute_plan(plan)

        if hasattr(module, "handle"):
            return module.handle(request)

        raise ValueError(f"Módulo {module_name} incompatible")
