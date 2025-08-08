"""Pruebas de integración del MetaEvaluator con ReasoningKernel."""

import sys
import types

# Stub de ``agix`` para aislar las pruebas de dependencias externas.
agix = types.ModuleType("agix")
agix.orchestrator = types.ModuleType("orchestrator")
agix.orchestrator.VirtualQualia = object
sys.modules.setdefault("agix", agix)
sys.modules.setdefault("agix.orchestrator", agix.orchestrator)

from agicore_core.reasoning_kernel import ReasoningKernel
from agicore_core.meta_evaluator import MetaEvaluator
from meta_router import MetaRouter


class DummyExpert:
    """Experto mínimo que acumula las llamadas recibidas."""

    def __init__(self):
        self.calls = []

    def handle(self, request):
        self.calls.append(request)
        count = request.get("count", 0) + request.get("payload", 0)
        return {"count": count}


class CountingMetaEvaluator(MetaEvaluator):
    """Extiende ``MetaEvaluator`` registrando invocaciones de ``evaluar_ciclo``."""

    def __init__(self):
        super().__init__()
        self.calls = 0

    def evaluar_ciclo(self, resultados):  # type: ignore[override]
        self.calls += 1
        return super().evaluar_ciclo(resultados)


class DummyPlanner:
    def plan(self, state):
        return [{"task": "do", "payload": 1}]


def test_meta_evaluator_generates_suggestions_and_updates_state():
    router = MetaRouter()
    expert = DummyExpert()
    router.register("dummy", expert, tasks=["do"], contexts=["ctx"], goals=["finish"])
    evaluator = CountingMetaEvaluator()
    kernel = ReasoningKernel(planner=DummyPlanner(), router=router, evaluator=evaluator)
    kernel.set_state({"context": "ctx", "goals": ["finish"], "count": 0})

    # Historial inicial con métricas elevadas para forzar sugerencias.
    kernel.history = [{"error": 1.0, "tiempo": 2.0} for _ in range(5)]

    final_state = kernel.run(max_iterations=2)

    # ``evaluar_ciclo`` se invoca una vez por iteración.
    assert evaluator.calls == 2

    # El estado incorpora sugerencias de reconfiguración.
    assert final_state["error"] == "disminuir tasa de aprendizaje"
    assert final_state["tiempo"] == "optimizar componentes críticos"

    # Tras ``reflexionar`` se actualizan métricas agregadas y sugerencias internas.
    assert evaluator.metricas_agregadas == {"error": 1.0, "tiempo": 2.0}
    assert evaluator.sugerencias == [
        {
            "error": "disminuir tasa de aprendizaje",
            "tiempo": "optimizar componentes críticos",
        }
    ]
