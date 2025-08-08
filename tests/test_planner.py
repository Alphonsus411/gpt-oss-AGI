"""Pruebas para el planificador de ``gpt_oss``.

Este conjunto de pruebas verifica la definición de intención global, la
gestión de prioridades en las metas y el cambio de submodos del planificador.
"""

from gpt_oss.planner import Planner


def test_definir_intencion() -> None:
    """El planificador debería almacenar la intención global."""

    planner = Planner()
    planner.set_intention("resolver un problema")
    assert planner.get_intention() == "resolver un problema"


def test_asignar_prioridades() -> None:
    """La meta con mayor prioridad se recupera primero."""

    planner = Planner()
    planner.add_goal("segunda", 1)
    planner.add_goal("primera", 5)
    assert planner.get_next_goal() == "primera"
    assert planner.get_next_goal() == "segunda"


def test_cambio_de_submodos() -> None:
    """El modo activo debería actualizarse correctamente al cambiarlo."""

    planner = Planner()
    planner.activate_mode("creative")
    assert planner.current_mode() == "creative"

    planner.activate_mode("analytic")
    assert planner.current_mode() == "analytic"
    params = planner.get_mode_parameters()
    assert params["heuristic"] == "critical"
