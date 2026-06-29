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

from agicore_core.qualia_engine import CoreQualiaEngine
from gpt_oss.strategic_memory import Episode, StrategicMemory


@dataclass
class Expert:
    """Contenedor de metadatos para cada experto registrado."""

    module: Any
    tasks: List[str] = field(default_factory=list)
    contexts: List[str] = field(default_factory=list)
    goals: List[str] = field(default_factory=list)
    priority: int = 0
    qualia_policies: List[str] = field(default_factory=list)
    cognitive_patterns: List[str] = field(default_factory=list)
    risk_profile: str = "standard"


class MetaRouter:
    """Enrutador de solicitudes basado en expertos.

    Los expertos registrados deben implementar un método ``handle`` que reciba
    un diccionario con la solicitud completa. Cada experto puede declarar las
    tareas, contextos y metas que soporta para que el enrutador seleccione el
    más adecuado. Opcionalmente, el enrutador puede trabajar con una memoria
    estratégica para aprender de resultados pasados.
    """

    def __init__(self, memory: Optional[StrategicMemory] = None, qualia_node: Any | None = None) -> None:
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
        self._qualia_node = qualia_node

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
        qualia_policies: List[str] | None = None,
        cognitive_patterns: List[str] | None = None,
        risk_profile: str = "standard",
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
            qualia_policies=qualia_policies or [],
            cognitive_patterns=cognitive_patterns or [],
            risk_profile=risk_profile,
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
        qualia: Dict[str, Any] | None = None,
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

        if qualia and qualia.get("blocked"):
            return {}

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

            if qualia:
                policy_names = {
                    policy.get("name", "") if isinstance(policy, dict) else str(policy)
                    for policy in qualia.get("policies", [])
                }
                if policy_names and expert.qualia_policies:
                    score += len(policy_names.intersection(expert.qualia_policies))
                active_patterns = {
                    pattern.get("name", pattern) if isinstance(pattern, dict) else pattern
                    for pattern in qualia.get("cognitive_patterns", [])
                }
                score += len(active_patterns.intersection(expert.cognitive_patterns))
                classification = qualia.get("ethical_classification")
                if classification == "cuestionable":
                    score -= 1
                if classification == "nocivo":
                    score -= 100
                evolutionary = qualia.get("evolutionary_signals", {})
                if isinstance(evolutionary, dict):
                    recommended = evolutionary.get("selected_expert") or evolutionary.get("recommended_action")
                    confidence = float(evolutionary.get("confidence", 0.0) or 0.0)
                    if recommended and str(recommended) in {name, *expert.tasks, *expert.goals}:
                        score += int(round(min(confidence, 1.0) * 6))
                    score += int(round(float(evolutionary.get("neuromorphic_activation", 0.0) or 0.0)))

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


    @staticmethod
    def _qualia_metadata(request: Dict[str, Any], state: Dict[str, Any] | None = None) -> Dict[str, Any]:
        qualia = request.get("qualia") if isinstance(request.get("qualia"), dict) else {}
        state = state or {}
        return {
            "ethical_classification": qualia.get("ethical_classification"),
            "violated_constraints": qualia.get("violated_constraints", []),
            "qualia_policy_action": qualia.get("policy_action"),
            "qualia_legal_policy_action": qualia.get("legal_policy_action"),
            "qualia_ethical_evidence": qualia.get("ethical_evidence", {}),
            "qualia_evolutionary_signals": qualia.get("evolutionary_signals", {}),
            "qualia_decision_audit": state.get("qualia_decision_audit", qualia.get("decision_audit", {})),
            "qualia_neuromorphic_feedback": state.get(
                "qualia_neuromorphic_feedback", request.get("qualia_neuromorphic_feedback", {})
            ),
            "evolution_feedback": state.get("evolution_feedback", {}),
            "qualia_last_phase": state.get("qualia_last_phase"),
            "qualia_trace_length": state.get("qualia_trace_length"),
        }

    @staticmethod
    def _blocked_qualia_result(request: Dict[str, Any]) -> Dict[str, Any]:
        return CoreQualiaEngine.blocked_result(request)

    def _record_blocked_episode(
        self,
        request: Dict[str, Any],
        result: Dict[str, Any],
        task: Any,
        context: Any,
        goals: Any,
    ) -> None:
        if self._memory is None:
            return
        state = dict(request)
        if self._qualia_node is not None:
            self._qualia_node.integrate_response(result, state, phase="router_blocked")
        metadata = {
            "task": task,
            "context": context,
            "goals": goals,
            "expert": None,
            "status": "blocked_by_qualia",
            "latency": 0.0,
        }
        metadata.update(self._qualia_metadata(request, state))
        self._memory.add_episode(
            Episode(
                timestamp=datetime.now(),
                input=request,
                action="blocked_by_qualia",
                outcome=result,
                metadata=metadata,
            )
        )

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

        if "qualia" not in request and self._qualia_node is not None:
            request = self._qualia_node.enrich_request(request, phase="router")

        task = request.get("task")
        context = request.get("context")
        goals = request.get("goals")
        if task is None or context is None or goals is None:
            raise ValueError(
                "La solicitud debe incluir 'task', 'context' y 'goals'",
            )
        if not isinstance(goals, list) or not all(isinstance(g, str) for g in goals):
            raise ValueError("La clave 'goals' debe ser una lista de cadenas")

        qualia = request.get("qualia") if isinstance(request.get("qualia"), dict) else None
        if qualia and CoreQualiaEngine.must_block(request):
            result = self._blocked_qualia_result(request)
            self._record_blocked_episode(request, result, task, context, goals)
            return result

        scores = self.select_expert(
            task,
            context,
            goals,
            weight_task=weight_task,
            weight_context=weight_context,
            weight_goal=weight_goal,
            qualia=qualia,
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
            state = dict(request)
            if self._qualia_node is not None and qualia:
                self._qualia_node.integrate_response({"error": str(exc)}, state, phase="router_error")
            if self._memory is not None:
                metadata = {
                    "task": task,
                    "context": context,
                    "goals": goals,
                    "expert": selected_name,
                    "status": "failure",
                    "latency": perf_counter() - start,
                }
                metadata.update(self._qualia_metadata(request, state))
                episode = Episode(
                    timestamp=datetime.now(),
                    input=request,
                    action=selected_name,
                    outcome=str(exc),
                    metadata=metadata,
                )
                self._memory.add_episode(episode)
            raise

        state = dict(request)
        if self._qualia_node is not None and qualia:
            self._qualia_node.integrate_response(result, state, phase="router")
            request.update(
                {
                    key: state[key]
                    for key in (
                        "qualia_neuromorphic_feedback",
                        "evolution_feedback",
                        "qualia_decision_audit",
                        "qualia_last_phase",
                        "qualia_trace_length",
                    )
                    if key in state
                }
            )

        if self._memory is not None:
            metadata = {
                "task": task,
                "context": context,
                "goals": goals,
                "expert": selected_name,
                "status": "success",
                "latency": perf_counter() - start,
            }
            metadata.update(self._qualia_metadata(request, state))
            episode = Episode(
                timestamp=datetime.now(),
                input=request,
                action=selected_name,
                outcome=result,
                metadata=metadata,
            )
            self._memory.add_episode(episode)

        return result
