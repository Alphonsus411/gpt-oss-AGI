"""Utilities for managing strategic memory and episodic data."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List


@dataclass
class Episode:
    """Representa una interacción con información contextual."""

    timestamp: datetime
    input: Any
    action: Any
    outcome: Any
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class InferenceHypothesis:
    """Patrón inferido desde episodios seguros ya aprendidos."""

    pattern: Dict[str, Any]
    evidence: List[Episode]
    confidence: float
    ethical_constraints: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class MemoryConsolidationResult:
    """Resultado auditable de consolidar memoria episódica en hipótesis."""

    episodes_used: int
    hypotheses_created: List[InferenceHypothesis] = field(default_factory=list)
    hypotheses_updated: List[InferenceHypothesis] = field(default_factory=list)
    discarded_signals: List[Dict[str, Any]] = field(default_factory=list)


class StrategicMemory:
    """Almacena memoria estratégica, auditoría y aprendizaje inferencial seguro."""

    def __init__(self, max_episodes: int | None = None) -> None:
        self._storage: Dict[str, Any] = {}
        self._episodes: List[Episode] = []
        self._audit_episodes: List[Episode] = []
        self._rejected_learning: List[Episode] = []
        self._hypotheses: List[InferenceHypothesis] = []
        self._max_episodes = max_episodes

    def save(self, key: str, value: Any) -> None:
        if key in self._storage:
            raise ValueError(f"La clave '{key}' ya existe en la memoria.")
        self._storage[key] = value

    def get(self, key: str, default: Any | None = None) -> Any:
        return self._storage.get(key, default)

    def update(self, key: str, value: Any) -> None:
        if key not in self._storage:
            raise KeyError(f"La clave '{key}' no se encuentra en la memoria.")
        self._storage[key] = value

    def add_episode(self, data: Episode) -> None:
        """Añade un episodio utilizable solo si no fue bloqueado por Qualia."""

        if self._is_blocked_or_rejected(data):
            self.add_rejected_learning(data, reason="blocked_or_rejected_by_qualia")
            return
        self._append_bounded(self._episodes, data)

    def add_audit_episode(self, data: Episode) -> None:
        """Registra trazabilidad sin alimentar aprendizaje inferencial."""

        self._audit_episodes.append(data)

    def add_rejected_learning(self, data: Episode, reason: str) -> None:
        """Registra una señal que no debe consolidarse como conocimiento."""

        data.metadata = {**data.metadata, "rejection_reason": reason, "status": data.metadata.get("status", "rejected_learning")}
        self._rejected_learning.append(data)
        self._audit_episodes.append(data)

    def query(self, pattern: Dict[str, Any]) -> List[Episode]:
        return self._query_collection(self._episodes, pattern)

    def query_audit(self, pattern: Dict[str, Any]) -> List[Episode]:
        return self._query_collection(self._audit_episodes, pattern)

    def query_rejected(self, pattern: Dict[str, Any]) -> List[Episode]:
        return self._query_collection(self._rejected_learning, pattern)

    def infer_patterns(self, criteria: Dict[str, Any] | None = None) -> List[InferenceHypothesis]:
        if criteria:
            return self.query_inferred(criteria)
        if not self._hypotheses:
            self.consolidate_from_episodes()
        return list(self._hypotheses)

    def consolidate_from_episodes(self, min_support: int = 2, max_hypotheses: int = 20) -> MemoryConsolidationResult:
        groups: dict[tuple[Any, Any, Any], list[Episode]] = defaultdict(list)
        discarded: list[dict[str, Any]] = []
        for episode in self._episodes:
            if self._is_blocked_or_rejected(episode):
                discarded.append({"reason": "blocked_or_rejected", "episode": episode})
                continue
            key = (
                episode.metadata.get("task", episode.action),
                episode.metadata.get("context"),
                self._hashable(episode.metadata.get("goals")),
            )
            groups[key].append(episode)

        created: list[InferenceHypothesis] = []
        updated: list[InferenceHypothesis] = []
        for (task, context, goals), evidence in groups.items():
            if len(evidence) < min_support:
                continue
            successes = sum(1 for ep in evidence if ep.metadata.get("status") in {"success", "accepted", None})
            confidence = round(min(1.0, successes / len(evidence)), 3)
            constraints = sorted({str(item) for ep in evidence for item in ep.metadata.get("violated_constraints", [])})
            hypothesis = InferenceHypothesis(
                pattern={"task": task, "context": context, "goals": goals, "recommended_action": evidence[-1].action},
                evidence=list(evidence),
                confidence=confidence,
                ethical_constraints=constraints,
            )
            previous = self._find_hypothesis(hypothesis.pattern)
            if previous is None:
                created.append(hypothesis)
                self._hypotheses.append(hypothesis)
            else:
                previous.evidence = hypothesis.evidence
                previous.confidence = hypothesis.confidence
                previous.ethical_constraints = hypothesis.ethical_constraints
                updated.append(previous)
            if len(created) + len(updated) >= max_hypotheses:
                break
        return MemoryConsolidationResult(
            episodes_used=sum(len(eps) for eps in groups.values()),
            hypotheses_created=created,
            hypotheses_updated=updated,
            discarded_signals=discarded,
        )

    def query_inferred(self, pattern: Dict[str, Any]) -> List[InferenceHypothesis]:
        results: list[InferenceHypothesis] = []
        for hypothesis in self._hypotheses:
            if all(hypothesis.pattern.get(key) == value for key, value in pattern.items()):
                results.append(hypothesis)
        return results

    def summarize(self) -> Dict[str, Any]:
        acciones = Counter(ep.action for ep in self._episodes)
        resultados = Counter(ep.outcome for ep in self._episodes)
        return {
            "total": len(self._episodes),
            "audit_total": len(self._audit_episodes),
            "rejected_total": len(self._rejected_learning),
            "hypotheses_total": len(self._hypotheses),
            "actions": acciones.most_common(),
            "outcomes": resultados.most_common(),
        }

    def _append_bounded(self, collection: List[Episode], data: Episode) -> None:
        if self._max_episodes is not None:
            while len(collection) >= self._max_episodes:
                collection.pop(0)
        collection.append(data)

    @staticmethod
    def _query_collection(collection: List[Episode], pattern: Dict[str, Any]) -> List[Episode]:
        resultados: List[Episode] = []
        for episodio in collection:
            coincide = True
            for clave, valor in pattern.items():
                attr = getattr(episodio, clave, episodio.metadata.get(clave))
                if attr != valor:
                    coincide = False
                    break
            if coincide:
                resultados.append(episodio)
        return resultados

    @staticmethod
    def _is_blocked_or_rejected(episode: Episode) -> bool:
        status = episode.metadata.get("status")
        if status in {"blocked_by_qualia", "rejected_learning"}:
            return True
        if episode.metadata.get("qualia_policy_action") == "blocked_by_ontoethical_policy":
            return True
        if episode.metadata.get("qualia_legal_policy_action") == "blocked_illegal_or_unsafe_decision":
            return True
        if isinstance(episode.outcome, dict) and episode.outcome.get("blocked"):
            return True
        return False

    @staticmethod
    def _hashable(value: Any) -> Any:
        if isinstance(value, list):
            return tuple(value)
        if isinstance(value, dict):
            return tuple(sorted(value.items()))
        return value

    def _find_hypothesis(self, pattern: Dict[str, Any]) -> InferenceHypothesis | None:
        for hypothesis in self._hypotheses:
            if hypothesis.pattern == pattern:
                return hypothesis
        return None
