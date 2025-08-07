from __future__ import annotations

"""Enrutador central para delegar solicitudes entre módulos.

La clase :class:`MetaRouter` mantiene un registro de módulos y dirige cada
solicitud al destino adecuado. Por defecto se registra el
:class:`agicore_core.ReasoningKernel` bajo la clave ``"reasoning"``.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List

from agicore_core import ReasoningKernel


@dataclass
class Expert:
    """Contenedor de metadatos para cada experto registrado."""

    module: Any
    tasks: List[str] = field(default_factory=list)
    contexts: List[str] = field(default_factory=list)
    goals: List[str] = field(default_factory=list)
    priority: int = 0


class ReasoningExpert:
    """Pequeño adaptador para :class:`ReasoningKernel`.

    Provee un método :meth:`handle` que delega en
    :meth:`ReasoningKernel.execute_plan` para mantener una interfaz común
    entre todos los expertos registrados.
    """

    def __init__(self, kernel: ReasoningKernel) -> None:
        self._kernel = kernel

    def handle(self, request: Dict[str, Any]) -> Any:  # pragma: no cover - delega
        plan = request.get("plan", [])
        return self._kernel.execute_plan(plan)


class MetaRouter:
    """Enrutador de solicitudes basado en expertos.

    Los expertos registrados deben implementar un método ``handle`` que reciba
    un diccionario con la solicitud completa. Cada experto puede declarar las
    tareas, contextos y metas que soporta para que el enrutador seleccione el
    más adecuado.
    """

    def __init__(self) -> None:
        self._experts: Dict[str, Expert] = {}
        # Registro por defecto del kernel de razonamiento con un adaptador.
        self.register(
            "reasoning",
            ReasoningExpert(ReasoningKernel()),
            tasks=["reasoning"],
        )

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
        self, task: str, context: str, goals: List[str]
    ) -> Dict[str, int]:
        """Calcula un puntaje para cada experto registrado.

        La heurística otorga puntos por coincidencia exacta entre la solicitud y
        los metadatos de cada experto. Cada tarea o contexto coincidente suma un
        punto y cada meta coincidente suma otro. Además se añade la ``priority``
        declarada por el experto.
        """

        scores: Dict[str, int] = {}
        goals_set = set(goals)
        for name, expert in self._experts.items():
            score = expert.priority
            if task in expert.tasks:
                score += 1
            if context in expert.contexts:
                score += 1
            score += len(goals_set.intersection(expert.goals))
            scores[name] = score
        return scores

    def route(self, request: Dict[str, Any]) -> Any:
        """Envía ``request`` al experto más adecuado.

        Parameters
        ----------
        request:
            Diccionario que debe contener las claves ``"task"``, ``"context"``
            y ``"goals"`` (lista de metas). Otros campos se pasan directamente
            al experto seleccionado.
        """

        task = request.get("task")
        context = request.get("context")
        goals = request.get("goals")
        if task is None or context is None or goals is None:
            raise ValueError(
                "La solicitud debe incluir 'task', 'context' y 'goals'"
            )

        scores = self.select_expert(task, context, goals)
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
