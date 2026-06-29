"""Ejecución de planes paso a paso mediante un ``MetaRouter``.

Este módulo proporciona la clase :class:`ReasoningKernel` que interpreta un
plan y delega cada paso en una instancia de :class:`meta_router.MetaRouter`.
"""

from __future__ import annotations

from typing import Any, Dict, List

from meta_router import MetaRouter

from .qualia_node import QualiaNode


class ReasoningKernel:
    """Ejecuta pasos de razonamiento usando un enrutador externo."""

    def __init__(self, router: MetaRouter, qualia_node: QualiaNode | None = None) -> None:
        self.router = router
        self.qualia_node = qualia_node or QualiaNode()

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
        request = self.qualia_node.enrich_request(request, phase="kernel_step")
        try:
            result = self.router.route(
                request,
                weight_task=weight_task,
                weight_context=weight_context,
                weight_goal=weight_goal,
            )
        except TypeError:
            # Algunos ``MetaRouter`` de pruebas no aceptan pesos heurísticos
            result = self.router.route(request)
        state: Dict[str, Any] = {}
        self.qualia_node.integrate_response(result, state, phase="kernel_step")
        return result

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
