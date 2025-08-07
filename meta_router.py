"""Enrutador central para delegar solicitudes entre módulos."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class Expert:
    """Contenedor de metadatos para cada experto registrado."""

    module: Any
    tasks: List[str] = field(default_factory=list)
    contexts: List[str] = field(default_factory=list)
    goals: List[str] = field(default_factory=list)
    priority: int = 0


class MetaRouter:
    """Enrutador de solicitudes basado en expertos.

    Los expertos registrados deben implementar un método ``handle`` que reciba
    un diccionario con la solicitud completa. Cada experto puede declarar las
    tareas, contextos y metas que soporta para que el enrutador seleccione el
    más adecuado.
    """

    def __init__(self) -> None:
        self._experts: Dict[str, Expert] = {}

    def register(
        self,
        name: str,
        module: Any,
        *,
        tasks: List[str] | None = None,
        contexts: List[str] | None = None,
        goals: List[str] | None = None,
        priority: int = 0,
    ) -> None:
        """Registra un nuevo ``module`` bajo ``name`` con metadatos opcionales."""

        self._experts[name] = Expert(
            module=module,
            tasks=tasks or [],
            contexts=contexts or [],
            goals=goals or [],
            priority=priority,
        )

    def select_expert(
        self,
        task: str,
        context: str,
        goals: List[str],
        *,
        weight_task: int = 1,
        weight_context: int = 1,
        weight_goal: int = 1,
    ) -> Dict[str, int]:
        """Calcula un puntaje para cada experto registrado.

        Parameters
        ----------
        task, context, goals:
            Elementos de la solicitud que se comparan con los metadatos
            proporcionados por cada experto.
        weight_task, weight_context, weight_goal:
            Pesos que multiplica cada coincidencia de ``task``, ``context`` y
            ``goals`` respectivamente.
        """

        scores: Dict[str, int] = {}
        goals_set = set(goals)
        for name, expert in self._experts.items():
            score = expert.priority
            if task in expert.tasks:
                score += weight_task
            if context in expert.contexts:
                score += weight_context
            score += weight_goal * len(goals_set.intersection(expert.goals))
            scores[name] = score
        return scores

    def route(
        self,
        request: Dict[str, Any],
        *,
        weight_task: int = 1,
        weight_context: int = 1,
        weight_goal: int = 1,
    ) -> Any:
        """Envía ``request`` al experto más adecuado.

        Parameters
        ----------
        request:
            Diccionario que debe contener las claves ``"task"``, ``"context"``
            y ``"goals"`` (lista de metas). Otros campos se pasan directamente
            al experto seleccionado.
        weight_task, weight_context, weight_goal:
            Pesos que controlan la importancia relativa de cada tipo de
            coincidencia en la heurística de selección.
        """

        task = request.get("task")
        context = request.get("context")
        goals = request.get("goals")
        if task is None or context is None or goals is None:
            raise ValueError(
                "La solicitud debe incluir 'task', 'context' y 'goals'",
            )

        scores = self.select_expert(
            task,
            context,
            goals,
            weight_task=weight_task,
            weight_context=weight_context,
            weight_goal=weight_goal,
        )
        if not scores:
            raise ValueError("No hay expertos registrados")

        max_score = max(scores.values())
        if max_score <= 0:
            raise ValueError("Ningún experto coincide con la solicitud")

        candidates = [name for name, score in scores.items() if score == max_score]
        # Regla de desempate: orden alfabético del nombre del experto.
        selected_name = sorted(candidates)[0]
        expert = self._experts[selected_name].module
        if hasattr(expert, "handle"):
            return expert.handle(request)

        raise ValueError(f"Experto {selected_name} incompatible")
