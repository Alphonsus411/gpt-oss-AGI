"""Pruebas para el módulo :mod:`agicore_core.kernel`."""

from agicore_core import ReasoningKernel


def test_execute_step_returns_list():
    kernel = ReasoningKernel()
    result = kernel.execute_step({"task": "demo"})
    assert isinstance(result, list)


def test_execute_plan_runs_all_steps():
    kernel = ReasoningKernel()
    plan = [{"step": 1}, {"step": 2}]
    results = kernel.execute_plan(plan)
    assert isinstance(results, list)
    assert len(results) == len(plan)
