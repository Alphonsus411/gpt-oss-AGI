"""Adaptadores cognitivos opcionales para módulos AGIX documentados.

Estos adaptadores mantienen el Core funcional sin AGIX instalado y normalizan
señales de aprendizaje, conceptos, foco atencional y métricas de evaluación en
payloads auditables que Qualia puede adjuntar a cada decisión GPT.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, Mapping

from .agix_compat import load_first_component


_COMPONENTS: dict[str, tuple[tuple[str, str], ...]] = {
    "meta_learner": (("agix.learning.meta", "MetaLearner"), ("agix.learning", "MetaLearner")),
    "ontology": (("agix.memory", "Ontology"), ("agix.reasoning", "Ontology")),
    "latent_representation": (("agix.memory", "LatentRepresentation"), ("agix.reasoning", "LatentRepresentation")),
    "neuro_symbolic_bridge": (("agix.reasoning", "NeuroSymbolicBridge"),),
    "evaluation_metrics": (("agix.evaluation", "EvaluationMetrics"),),
    "concept_classifier": (("agix.memory", "ConceptClassifier"), ("agix.reasoning", "ConceptClassifier")),
    "heuristic_concept_creator": (("agix.memory", "HeuristicConceptCreator"), ("agix.reasoning", "HeuristicConceptCreator")),
    "emotion_simulator": (("agix.emotion.emotion_simulator", "EmotionSimulator"),),
    "attention_focus": (("agix.perception.attention", "AttentionFocus"),),
}

_DECISION_METHODS: dict[str, tuple[str, ...]] = {
    "meta_learner": ("adapt", "learn", "update", "fit", "meta_update"),
    "ontology": ("infer", "query", "relate", "add_concept"),
    "latent_representation": ("encode", "transform", "project"),
    "neuro_symbolic_bridge": ("encode", "bridge", "translate"),
    "evaluation_metrics": ("evaluate", "calcular", "score", "compute"),
    "concept_classifier": ("classify", "clasificar", "predict"),
    "heuristic_concept_creator": ("create", "crear", "generate", "infer"),
    "emotion_simulator": ("simulate", "simular", "evaluate", "infer"),
    "attention_focus": ("focus", "attend", "select", "prioritize"),
}


@dataclass
class AgixCognitiveAdapters:
    """Carga y coordina capacidades cognitivas avanzadas de AGIX."""

    enabled: bool = True
    components: dict[str, Any | None] = field(default_factory=dict, init=False)
    errors: dict[str, str] = field(default_factory=dict, init=False)

    def __post_init__(self) -> None:
        self._load_components()

    def _load_components(self) -> None:
        for name, candidates in _COMPONENTS.items():
            self.components[name] = None
            if not self.enabled:
                continue
            cls, status = load_first_component(name, candidates)
            if cls is None:
                if status.error:
                    self.errors[name] = status.error
                continue
            try:
                self.components[name] = cls()
            except Exception as exc:  # pragma: no cover - depende de AGIX real
                self.errors[name] = str(exc)

    def validate_runtime_contract(self) -> Dict[str, Any]:
        """Describe disponibilidad y degradación por componente cognitivo."""

        return {
            name: self._component_contract(name, component)
            for name, component in self.components.items()
        }

    def enrich(self, request: Mapping[str, Any]) -> Dict[str, Any]:
        """Genera señales cognitivas seguras para Qualia."""

        signals: Dict[str, Any] = {
            "enabled": self.enabled,
            "agix_cognitive_contract": self.validate_runtime_contract(),
            "concepts": self._fallback_concepts(request),
            "attention_focus": None,
            "emotional_state": None,
            "latent_state": None,
            "evaluation_metrics": {},
            "meta_learning_update": None,
        }
        if not self.enabled:
            return signals

        self._apply_concept_components(request, signals)
        self._apply_attention(request, signals)
        self._apply_emotion(request, signals)
        self._apply_neuro_symbolic(request, signals)
        self._apply_evaluation(request, signals)
        return signals

    def integrate_feedback(self, result: Any, state: Mapping[str, Any]) -> Dict[str, Any]:
        """Propaga feedback seguro a MetaLearner si está disponible."""

        feedback: Dict[str, Any] = {"cognitive_feedback_applied": False}
        meta = self.components.get("meta_learner")
        if meta is None:
            return feedback
        payload = {"result": result, "state": dict(state)}
        for method_name in _DECISION_METHODS["meta_learner"]:
            method = getattr(meta, method_name, None)
            if not callable(method):
                continue
            try:
                feedback["meta_learning_update"] = method(payload)
            except TypeError:
                feedback["meta_learning_update"] = method(dict(state))
            except Exception as exc:  # pragma: no cover - depende de AGIX real
                feedback["meta_learning_error"] = str(exc)
                return feedback
            feedback["cognitive_feedback_applied"] = True
            feedback["meta_learning_method"] = method_name
            return feedback
        return feedback

    @staticmethod
    def _fallback_concepts(request: Mapping[str, Any]) -> list[dict[str, Any]]:
        terms: list[str] = []
        for key in ("task", "context", "prompt", "instruction", "goals"):
            value = request.get(key, "")
            if isinstance(value, (list, tuple)):
                terms.extend(str(item) for item in value)
            else:
                terms.extend(str(value).replace(",", " ").split())
        seen: set[str] = set()
        concepts: list[dict[str, Any]] = []
        for term in terms:
            normalized = term.strip().lower()
            if len(normalized) < 4 or normalized in seen:
                continue
            seen.add(normalized)
            concepts.append({"name": normalized, "source": "local_fallback", "confidence": 0.35})
            if len(concepts) >= 12:
                break
        return concepts

    def _apply_concept_components(self, request: Mapping[str, Any], signals: Dict[str, Any]) -> None:
        text = self._text(request)
        for name in ("concept_classifier", "heuristic_concept_creator", "ontology"):
            component = self.components.get(name)
            if component is None:
                continue
            for method_name in _DECISION_METHODS[name]:
                method = getattr(component, method_name, None)
                if not callable(method):
                    continue
                try:
                    result = method(dict(request))
                except TypeError:
                    result = method(text)
                except Exception as exc:
                    signals[f"{name}_error"] = str(exc)
                    break
                normalized = self._normalize_concepts(result, source=f"agix_{name}")
                if normalized:
                    signals["concepts"] = self._dedupe_concepts([*signals["concepts"], *normalized])
                signals[f"{name}_method"] = method_name
                break

    def _apply_attention(self, request: Mapping[str, Any], signals: Dict[str, Any]) -> None:
        self._call_first("attention_focus", request, signals, "attention_focus")

    def _apply_emotion(self, request: Mapping[str, Any], signals: Dict[str, Any]) -> None:
        self._call_first("emotion_simulator", request, signals, "emotional_state")

    def _apply_neuro_symbolic(self, request: Mapping[str, Any], signals: Dict[str, Any]) -> None:
        for name in ("latent_representation", "neuro_symbolic_bridge"):
            self._call_first(name, request, signals, "latent_state")

    def _apply_evaluation(self, request: Mapping[str, Any], signals: Dict[str, Any]) -> None:
        result = self._call_first("evaluation_metrics", request, signals, "evaluation_metrics")
        if isinstance(result, Mapping):
            signals["evaluation_metrics"] = self._normalize_metrics(result)

    def _call_first(self, name: str, request: Mapping[str, Any], signals: Dict[str, Any], output_key: str) -> Any:
        component = self.components.get(name)
        if component is None:
            return None
        for method_name in _DECISION_METHODS[name]:
            method = getattr(component, method_name, None)
            if not callable(method):
                continue
            try:
                result = method(dict(request))
            except TypeError:
                result = method(self._text(request))
            except Exception as exc:
                signals[f"{name}_error"] = str(exc)
                return None
            signals[output_key] = result
            signals[f"{name}_method"] = method_name
            return result
        return None

    @staticmethod
    def _normalize_metrics(result: Mapping[str, Any]) -> Dict[str, float]:
        metrics: Dict[str, float] = {}
        aliases = {
            "robustness": ("robustness", "robustez"),
            "generality": ("generality", "generalidad"),
            "transfer": ("transfer", "transferencia"),
            "fagi_index": ("fagi_index", "fagi", "fagi-index"),
            "explainability": ("explainability", "explicabilidad"),
        }
        for canonical, keys in aliases.items():
            for key in keys:
                if key in result:
                    try:
                        metrics[canonical] = float(result[key])
                    except (TypeError, ValueError):
                        pass
                    break
        return metrics

    @staticmethod
    def _normalize_concepts(result: Any, *, source: str) -> list[dict[str, Any]]:
        if result is None:
            return []
        if isinstance(result, str):
            values: Iterable[Any] = [result]
        elif isinstance(result, Mapping):
            values = result.get("concepts", result.get("labels", result.get("items", [])))
            if isinstance(values, str) or isinstance(values, Mapping):
                values = [values]
        elif isinstance(result, Iterable):
            values = result
        else:
            values = [result]
        concepts = []
        for item in values:
            if isinstance(item, Mapping):
                name = str(item.get("name", item.get("label", item.get("concept", "")))).strip()
                confidence = float(item.get("confidence", 0.5) or 0.5)
            else:
                name = str(item).strip()
                confidence = 0.5
            if name:
                concepts.append({"name": name.lower(), "source": source, "confidence": confidence})
        return concepts

    @staticmethod
    def _dedupe_concepts(concepts: list[dict[str, Any]]) -> list[dict[str, Any]]:
        best: dict[str, dict[str, Any]] = {}
        for concept in concepts:
            name = concept.get("name")
            if not name:
                continue
            if name not in best or float(concept.get("confidence", 0)) > float(best[name].get("confidence", 0)):
                best[name] = concept
        return list(best.values())[:20]

    @staticmethod
    def _component_contract(name: str, component: Any | None) -> Dict[str, Any]:
        methods = _DECISION_METHODS[name]
        available = [method for method in methods if component is not None and callable(getattr(component, method, None))]
        degradations = []
        if component is None:
            degradations.append("component_not_available")
        elif not available:
            degradations.append("decision_method_missing")
        return {
            "enabled": True,
            "active": component is not None,
            "methods_available": available,
            "degraded": bool(degradations),
            "degradations": degradations,
        }

    @staticmethod
    def _text(request: Mapping[str, Any]) -> str:
        return " ".join(str(request.get(key, "")) for key in ("task", "context", "prompt", "instruction", "goals", "token"))
