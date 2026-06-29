"""Pruebas para la carga del perfil del planificador de :mod:`agicore_core`."""

import logging
import sys
import types


def test_inicializacion_con_json_invalido(tmp_path, monkeypatch, caplog):
    """El planificador debería manejar un JSON inválido."""

    agix = types.ModuleType("agix")
    agix.orchestrator = types.ModuleType("orchestrator")
    agix.orchestrator.VirtualQualia = object
    sys.modules.setdefault("agix", agix)
    sys.modules.setdefault("agix.orchestrator", agix.orchestrator)

    from agicore_core import planner as planner_module

    module_dir = tmp_path / "agicore_core"
    config_dir = module_dir / "config"
    config_dir.mkdir(parents=True)
    (module_dir / "planner.py").write_text("", encoding="utf-8")
    (config_dir / "agent_profile.json").write_text("{invalido", encoding="utf-8")

    monkeypatch.setattr(planner_module, "__file__", str(module_dir / "planner.py"))

    with caplog.at_level(logging.WARNING):
        planificador = planner_module.Planner()
    assert planificador.agent_profile == {}
    assert "Failed to load agent profile" in caplog.text


def test_planner_acepta_orquestador_explicito_sin_importar_agix(monkeypatch):
    """El planificador puede inicializarse con un orquestador compatible."""

    from agicore_core import planner as planner_module

    def fail_load_virtual_qualia():
        raise AssertionError("No debería cargarse AGIX si hay orquestador explícito")

    class DummyOrchestrator:
        def broadcast_state(self, state):
            return [{"state": state}]

    monkeypatch.setattr(planner_module, "_load_virtual_qualia", fail_load_virtual_qualia)

    planificador = planner_module.Planner(orchestrator=DummyOrchestrator())

    assert planificador.plan({"goal": "test"}) == [{"state": {"goal": "test"}}]
