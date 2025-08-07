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
        weight_task: int = 1,
        weight_context: int = 1,
        weight_goal: int = 1,
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
        weight_task, weight_context, weight_goal:
            Pesos que se pasan a :meth:`meta_router.MetaRouter.route` para
            ajustar la heurística de selección.
        """

        request = {"task": task, "context": context, "goals": goals}
        request.update(step)
        return self.router.route(
            request,
            weight_task=weight_task,
            weight_context=weight_context,
            weight_goal=weight_goal,
        )

    def execute_plan(
        self,
        plan: List[Dict[str, Any]],
        *,
        task: str,
        context: str,
        goals: List[str],
        weight_task: int = 1,
        weight_context: int = 1,
        weight_goal: int = 1,
    ) -> List[Any]:
        """Ejecuta secuencialmente todos los pasos del plan."""

        return [
            self.execute_step(
                step,
                task=task,
                context=context,
                goals=goals,
                weight_task=weight_task,
                weight_context=weight_context,
                weight_goal=weight_goal,
            )
            for step in plan
        ]
