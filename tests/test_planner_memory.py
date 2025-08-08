"""Pruebas de integración entre Planner y StrategicMemory."""

from datetime import datetime

import pytest

from gpt_oss.planner import Planner
from gpt_oss.strategic_memory import Episode, StrategicMemory


def test_activate_mode_ajusta_parametros_desde_memoria() -> None:
    memory = StrategicMemory()
    memory.add_episode(
        Episode(
            timestamp=datetime.now(),
            input="i",
            action="a",
            outcome="success",
            metadata={"mode": "analytic", "temperature": 0.7},
        )
    )
    planner = Planner(memory=memory)
    planner.activate_mode("analytic")
    assert planner.get_mode_parameters()["temperature"] == 0.7


def test_record_episode_guarda_modo_y_temperatura() -> None:
    memory = StrategicMemory()
    planner = Planner(memory=memory)
    planner.activate_mode("creative")
    planner.record_episode("pregunta", "respuesta", "success")
    episodios = memory.query({"mode": "creative"})
    assert len(episodios) == 1
    ep = episodios[0]
    assert ep.outcome == "success"
    assert ep.metadata["temperature"] == planner.get_mode_parameters()["temperature"]


def test_activate_mode_promedia_temperaturas_memoria() -> None:
    memory = StrategicMemory()
    memory.add_episode(
        Episode(
            timestamp=datetime.now(),
            input="i1",
            action="a1",
            outcome="success",
            metadata={"mode": "analytic", "temperature": 0.4},
        )
    )
    memory.add_episode(
        Episode(
            timestamp=datetime.now(),
            input="i2",
            action="a2",
            outcome="success",
            metadata={"mode": "analytic", "temperature": 0.6},
        )
    )
    planner = Planner(memory=memory)
    planner.activate_mode("analytic")
    assert planner.get_mode_parameters()["temperature"] == pytest.approx(0.5)
