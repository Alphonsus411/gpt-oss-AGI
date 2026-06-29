"""Puente seguro entre señales de entrenamiento GPT, Qualia y memoria."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Mapping

from gpt_oss.strategic_memory import Episode

from .qualia_engine import CoreQualiaEngine
from .safety_gate import SafetyGate


@dataclass
class TrainingSignal:
    """Señal auditable procedente de entrenamiento, evaluación o inferencia."""

    source: str
    metric: str
    value: float
    phase: str = "training"
    sample: Any | None = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TrainingFeedback:
    """Resultado de filtrar señales de entrenamiento con Qualia."""

    accepted_signals: List[TrainingSignal] = field(default_factory=list)
    rejected_signals: List[TrainingSignal] = field(default_factory=list)
    reason: str = "accepted"
    aggregated_reward: float = 0.0
    audit: Dict[str, Any] = field(default_factory=dict)


class QualiaTrainingBridge:
    """Filtra aprendizaje para impedir que señales inseguras adapten el Core."""

    def __init__(self, qualia_engine: CoreQualiaEngine | None = None) -> None:
        self.qualia_engine = qualia_engine or CoreQualiaEngine()
        self.safety_gate = SafetyGate(self.qualia_engine)

    def record_training_signal(self, signal: TrainingSignal, state: Mapping[str, Any]) -> TrainingFeedback:
        payload = {
            **dict(state),
            "task": "training_signal",
            "context": signal.source,
            "goals": ["safe_learning"],
            "metric": signal.metric,
            "value": signal.value,
            "sample": signal.sample,
            "training_metadata": signal.metadata,
        }
        checked = self.safety_gate.check_request(payload, phase=signal.phase)
        if self.safety_gate.must_block(checked) or not self.filter_unsafe_signal(signal, checked.get("qualia", {})):
            blocked = self.safety_gate.blocked_response(checked)
            return TrainingFeedback(
                rejected_signals=[signal],
                reason=str(blocked.get("reason") or "blocked_by_qualia"),
                aggregated_reward=-1.0,
                audit=blocked,
            )
        reward = max(-1.0, min(1.0, float(signal.value)))
        audit = checked.get("qualia", {}).get("decision_audit", {}) if isinstance(checked.get("qualia"), dict) else {}
        return TrainingFeedback(
            accepted_signals=[signal],
            reason="accepted_by_qualia",
            aggregated_reward=reward,
            audit=audit,
        )

    @staticmethod
    def filter_unsafe_signal(signal: TrainingSignal, qualia_payload: Mapping[str, Any]) -> bool:
        if qualia_payload.get("blocked"):
            return False
        if qualia_payload.get("legal_policy_action") == "blocked_illegal_or_unsafe_decision":
            return False
        unsafe = {"malware", "ilegalidad", "dano_fisico", "privacidad", "manipulacion"}
        constraints = qualia_payload.get("violated_constraints", [])
        for item in constraints:
            name = item.get("name") if isinstance(item, Mapping) else str(item)
            if name in unsafe:
                return False
        return True

    @staticmethod
    def to_memory_episode(feedback: TrainingFeedback) -> Episode:
        signal = (feedback.accepted_signals or feedback.rejected_signals)[0]
        return Episode(
            timestamp=datetime.utcnow(),
            input=signal.sample,
            action="training_signal",
            outcome=feedback.reason,
            metadata={
                "source": signal.source,
                "metric": signal.metric,
                "value": signal.value,
                "phase": signal.phase,
                "reward": feedback.aggregated_reward,
                "qualia_decision_audit": feedback.audit,
                "status": "accepted" if feedback.accepted_signals else "rejected_learning",
            },
        )
