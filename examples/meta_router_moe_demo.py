"""Demostración de `MetaRouter` con múltiples expertos.

Ejecutar desde la raíz del repositorio:

    python examples/meta_router_moe_demo.py

Este ejemplo define dos expertos ficticios que resuelven metas distintas.
Un `Planner` genera un plan con pasos para cada meta y el
`ReasoningKernel` ejecuta el plan pasando cada paso por `MetaRouter`, que
selecciona el experto adecuado.
"""

from __future__ import annotations

from pathlib import Path
import sys
sys.path.append(str(Path(__file__).resolve().parent.parent))

from agicore_core import Planner, ReasoningKernel
from agix.orchestrator import VirtualQualia
from meta_router import MetaRouter


class DummyExpert:
    """Experto simple que devuelve su propio nombre."""

    def __init__(self, name: str) -> None:
        self.name = name

    def handle(self, request: dict) -> str:  # pragma: no cover - ejemplo interactivo
        print(f"Experto '{self.name}' recibió: {request}")
        return self.name


class PlanClient:
    """Cliente para `VirtualQualia` que devuelve un paso predefinido."""

    def __init__(self, step: dict) -> None:
        self.step = step

    def enviar_estado(self, state: dict):  # pragma: no cover - ejemplo interactivo
        return self.step

    def difundir_evento(self, event: str):  # pragma: no cover - ejemplo interactivo
        return None


def main() -> None:  # pragma: no cover - ejemplo interactivo
    # --------------------------------------------------------------
    # 1. Configurar MetaRouter con dos expertos y sus metas.
    # --------------------------------------------------------------
    router = MetaRouter()
    router.register(
        "sumador",
        DummyExpert("sumador"),
        tasks=["math"],
        contexts=["demo"],
        goals=["sum"],
    )
    router.register(
        "multiplicador",
        DummyExpert("multiplicador"),
        tasks=["math"],
        contexts=["demo"],
        goals=["multiply"],
    )

    # --------------------------------------------------------------
    # 2. Crear un plan que contenga pasos con metas distintas.
    #    Para simplificar, usamos `VirtualQualia` con dos clientes
    #    que devuelven directamente los pasos.
    # --------------------------------------------------------------
    step_sum = {"task": "math", "goals": ["sum"], "data": {"a": 2, "b": 3}}
    step_mul = {
        "task": "math",
        "goals": ["multiply"],
        "data": {"a": 2, "b": 3},
    }
    orchestrator = VirtualQualia(clients=[PlanClient(step_sum), PlanClient(step_mul)])
    planner = Planner(orchestrator)
    plan = planner.plan({"objective": "demo"})
    print("Plan generado por Planner:", plan)

    # --------------------------------------------------------------
    # 3. Ejecutar el plan con ReasoningKernel y mostrar experto.
    # --------------------------------------------------------------
    kernel = ReasoningKernel(router)
    results = kernel.execute_plan(plan, task="math", context="demo", goals=[])
    for idx, expert_name in enumerate(results, start=1):
        print(f"Paso {idx}: experto seleccionado -> {expert_name}")


if __name__ == "__main__":  # pragma: no cover - ejemplo interactivo
    main()
