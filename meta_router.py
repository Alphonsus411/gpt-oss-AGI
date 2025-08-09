"""Enrutador central para delegar solicitudes entre módulos.

Este enrutador puede utilizar una instancia de
``gpt_oss.strategic_memory.StrategicMemory`` para recordar episodios
anteriores y ajustar la selección del experto más adecuado en cada
solicitud.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from time import perf_counter
from typing import Any, Dict, List, Optional

from gpt_oss.strategic_memory import Episode, StrategicMemory


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
    más adecuado. Opcionalmente, el enrutador puede trabajar con una memoria
    estratégica para aprender de resultados pasados.
    """

    def __init__(self, memory: Optional[StrategicMemory] = None) -> None:
        """Inicializa el enrutador.

        Parameters
        ----------
        memory:
            Instancia de :class:`~gpt_oss.strategic_memory.StrategicMemory` que
            almacenará los episodios generados. Si es ``None`` se omite el
            almacenamiento y la consulta de memoria.
        """

        self._experts: Dict[str, Expert] = {}
        self._memory = memory

    def set_memory(self, memory: StrategicMemory) -> None:
        """Configura la memoria estratégica utilizada por el enrutador."""

        self._memory = memory

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
        if name in self._experts:
            raise ValueError(f"El nombre '{name}' ya está registrado")

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

        Asume que ``goals`` es una lista de cadenas previamente validada
        por :meth:`route`.

        Antes de evaluar a cada experto, se consultan los episodios
        almacenados en memoria que coincidan con los parámetros recibidos.
        Los resultados previos influyen en el puntaje final de cada experto
        favoreciendo a quienes tuvieron éxito y penalizando a quienes
        presentaron fallos o alta latencia.

        Parameters
        ----------
        task, context, goals:
            Elementos de la solicitud que se comparan con los metadatos
            proporcionados por cada experto.
        weight_task, weight_context, weight_goal:
            Pesos que multiplica cada coincidencia de ``task``, ``context`` y
            ``goals`` respectivamente.
        """

        episodes = []
        if self._memory is not None:
            pattern = {"task": task, "context": context, "goals": goals}
            episodes = self._memory.query(pattern)

        scores: Dict[str, int] = {}
        goals_set = set(goals)
        for name, expert in self._experts.items():
            score = expert.priority
            if task in expert.tasks:
                score += weight_task
            if context in expert.contexts:
                score += weight_context
            score += weight_goal * len(goals_set.intersection(expert.goals))

            if episodes:
                relevant = [
                    ep for ep in episodes if ep.metadata.get("expert") == name
                ]
                for ep in relevant:
                    status = ep.metadata.get("status")
                    latency = ep.metadata.get("latency", 0)
                    if status == "success":
                        score += 1
                    elif status == "failure":
                        score -= 1
                    score -= int(latency)

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

        Tras ejecutar al experto seleccionado se almacena un episodio en la
        memoria (si está disponible) con información sobre el resultado y la
        latencia de la llamada.

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
        if not isinstance(goals, list) or not all(isinstance(g, str) for g in goals):
            raise ValueError("La clave 'goals' debe ser una lista de cadenas")

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
        if not hasattr(expert, "handle"):
            raise ValueError(f"Experto {selected_name} incompatible")

        start = perf_counter()
        try:
            result = expert.handle(request)
        except Exception as exc:  # pragma: no cover - reemisión tras registro
            if self._memory is not None:
                episode = Episode(
                    timestamp=datetime.now(),
                    input=request,
                    action=selected_name,
                    outcome=str(exc),
                    metadata={
                        "task": task,
                        "context": context,
                        "goals": goals,
                        "expert": selected_name,
                        "status": "failure",
                        "latency": perf_counter() - start,
                    },
                )
                self._memory.add_episode(episode)
            raise

        if self._memory is not None:
            episode = Episode(
                timestamp=datetime.now(),
                input=request,
                action=selected_name,
                outcome=result,
                metadata={
                    "task": task,
                    "context": context,
                    "goals": goals,
                    "expert": selected_name,
                    "status": "success",
                    "latency": perf_counter() - start,
                },
            )
            self._memory.add_episode(episode)

        return result
