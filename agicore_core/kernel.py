"""Ejecución de planes paso a paso mediante un ``MetaRouter``.

Este módulo proporciona la clase :class:`ReasoningKernel` que interpreta un
plan y delega cada paso en una instancia de :class:`meta_router.MetaRouter`.
"""

from __future__ import annotations

from typing import Any, Dict, List

from meta_router import MetaRouter


class ReasoningKernel:
    """Ejecuta pasos de razonamiento usando un enrutador externo."""

    def __init__(self, router: MetaRouter) -> None:
        self.router = router

    def execute_step(
        self,
        step: Dict[str, Any],
        *,
        task: str,
        context: str,
        goals: List[str],
    ) -> Any:
        """Envía ``step`` al experto adecuado mediante ``router``.

        Parameters
        ----------
        step:
            Descripción del paso a ejecutar. Se fusiona con la información
            de ``task``, ``context`` y ``goals`` para construir la solicitud
            final.
        task, context, goals:
            Metadatos utilizados por :class:`MetaRouter` para seleccionar el
            experto más adecuado.
        """

        request = {"task": task, "context": context, "goals": goals}
        request.update(step)
        return self.router.route(request)

    def execute_plan(
        self,
        plan: List[Dict[str, Any]],
        *,
        task: str,
        context: str,
        goals: List[str],
    ) -> List[Any]:
        """Ejecuta secuencialmente todos los pasos del plan."""

        return [
            self.execute_step(step, task=task, context=context, goals=goals)
            for step in plan
        ]
