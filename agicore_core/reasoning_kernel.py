"""Núcleo de razonamiento con gestión de estado."""

from __future__ import annotations

from typing import Any, Dict

from meta_router import MetaRouter

from .planner import Planner


class ReasoningKernel:
    """Coordina un planificador y un enrutador manteniendo estado interno."""

    def __init__(self, planner: Planner, router: MetaRouter) -> None:
        self.planner = planner
        self.router = router
        self._state: Dict[str, Any] = {}

    def set_state(self, state: Dict[str, Any]) -> None:
        """Establece el ``state`` inicial para el planificador."""

        self._state = state

    def get_state(self) -> Dict[str, Any]:
        """Devuelve el estado interno actual."""

        return self._state

    def evaluate_step(self, step: Dict[str, Any]) -> Any:
        """Evalúa un ``step`` con ramificación condicional.

        Cada ``step`` puede incluir las claves opcionales ``if``, ``then`` y
        ``else``. La condición indicada en ``if`` se evalúa en el contexto del
        estado actual. Dependiendo de su resultado se selecciona la rama
        ``then`` o ``else`` y se fusiona con el resto del paso y con el estado
        antes de delegar la ejecución al :class:`MetaRouter`.

        El resultado devuelto por el enrutador se incorpora al estado: si es un
        ``dict`` se combina mediante :py:meth:`dict.update`; en caso contrario se
        almacena bajo la clave ``"result"``.
        """

        step = dict(step)  # evitar mutaciones externas
        condition = step.pop("if", None)
        then_branch = step.pop("then", {})
        else_branch = step.pop("else", {})

        if condition is not None:
            if isinstance(condition, str):
                try:
                    condition_value = bool(eval(condition, {}, self._state))
                except Exception:
                    condition_value = False
            else:
                condition_value = bool(condition)
            branch = then_branch if condition_value else else_branch
            step.update(branch)

        request: Dict[str, Any] = {**self._state, **step}
        result = self.router.route(request)

        if isinstance(result, dict):
            self._state.update(result)
        else:
            self._state["result"] = result
        return result
