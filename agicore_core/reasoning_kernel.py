"""Núcleo de razonamiento con gestión de estado."""

from __future__ import annotations

from typing import Any, Dict, List

from meta_router import MetaRouter

from .planner import Planner
from .meta_evaluator import MetaEvaluator


class ReasoningKernel:
    """Coordina un planificador y un enrutador manteniendo estado interno."""

    def __init__(
        self,
        planner: Planner,
        router: MetaRouter,
        evaluator: MetaEvaluator | None = None,
    ) -> None:
        self.planner = planner
        self.router = router
        self.evaluator = evaluator
        self._state: Dict[str, Any] = {}
        self.history: List[Dict[str, Any]] = []

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

        if self.evaluator is not None:
            self.evaluator.evaluar_ciclo({"result": result, "state": self._state})

        return result

    def run(self, max_iterations: int = 10) -> Dict[str, Any]:
        """Genera planes y ejecuta pasos hasta cumplir las metas.

        En cada iteración se obtiene un plan del :class:`Planner` utilizando el
        estado actual. Los pasos del plan se ejecutan mediante
        :meth:`evaluate_step` y se registran en ``history`` junto con el
        resultado o el error producido. El bucle finaliza si todas las metas
        están satisfechas o si se alcanza ``max_iterations``.

        Parameters
        ----------
        max_iterations:
            Número máximo de iteraciones del ciclo de planificación y
            ejecución.

        Returns
        -------
        dict
            El estado interno tras finalizar la ejecución.
        """

        if self.planner is None:
            raise ValueError("Se requiere un Planner para ejecutar 'run'")

        for iteration in range(max_iterations):
            try:
                plan = self.planner.plan(self._state)
            except Exception as exc:  # pragma: no cover - planificación fallida
                self.history.append({"iteration": iteration, "error": str(exc)})
                break

            for step in plan:
                try:
                    result = self.evaluate_step(step)
                    self.history.append({"step": step, "result": result})
                except Exception as exc:  # pragma: no cover - error del experto
                    self.history.append({"step": step, "error": str(exc)})
                    if self.evaluator is not None:
                        sugerencia = self.evaluator.sugerir_reconfiguracion(self.history)
                        if sugerencia:
                            self._state.update(sugerencia)
                        self.evaluator.reflexionar(self.history)
                    return self._state

                goals = self._state.get("goals", [])
                if isinstance(goals, list) and all(self._state.get(g) for g in goals):
                    if self.evaluator is not None:
                        sugerencia = self.evaluator.sugerir_reconfiguracion(self.history)
                        if sugerencia:
                            self._state.update(sugerencia)
                        self.evaluator.reflexionar(self.history)
                    return self._state

            if self.evaluator is not None:
                sugerencia = self.evaluator.sugerir_reconfiguracion(self.history)
                if sugerencia:
                    self._state.update(sugerencia)

        if self.evaluator is not None:
            self.evaluator.reflexionar(self.history)

        return self._state
