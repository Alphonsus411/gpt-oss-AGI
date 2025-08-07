"""Pruebas para el planificador de ``gpt_oss`` con metas prioritarias."""

import pytest

from gpt_oss.planner import Planner


def test_set_intention():
    planner = Planner()
    planner.set_intention("organizar tareas")
    assert planner.global_intent == "organizar tareas"


def test_add_goal_and_get_next_goal():
    planner = Planner()
    planner.add_goal("baja", 1)
    planner.add_goal("alta", 5)
    assert planner.get_next_goal() == "alta"
    assert planner.get_next_goal() == "baja"
    assert planner.get_next_goal() is None


def test_add_goal_negative_priority():
    planner = Planner()
    with pytest.raises(ValueError):
        planner.add_goal("invalida", -1)


def test_activate_mode_and_current_mode():
    planner = Planner()
    planner.activate_mode("creative")
    assert planner.current_mode() == "creative"
    assert planner.mode_parameters["temperature"] == 1.0


def test_activate_mode_invalid():
    planner = Planner()
    with pytest.raises(ValueError):
        planner.activate_mode("unknown")
