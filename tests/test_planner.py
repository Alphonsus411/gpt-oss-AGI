"""Pruebas para el módulo :mod:`agicore_core.planner`."""

from agicore_core import Planner


def test_plan_returns_list():
    planner = Planner()
    result = planner.plan({"task": "demo"})
    assert isinstance(result, list)
