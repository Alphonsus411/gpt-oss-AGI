"""Herramientas de planificación usando `agix`.

Este módulo expone la clase :class:`Planner` que genera planes
sencillos mediante la API de `agix`. Su objetivo es mostrar cómo
integrar las capacidades de orquestación de `agix` en componentes
de planificación.
"""

from __future__ import annotations

import importlib
from typing import Any, Dict, List, Optional

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def _load_virtual_qualia() -> type[Any]:
    """Carga ``VirtualQualia`` de AGIX solo cuando el planificador lo necesita."""

    try:
        orchestrator = importlib.import_module("agix.orchestrator")
    except ImportError as exc:
        raise RuntimeError(
            "AGIX 1.9.0 es necesario para crear Planner sin un orquestador "
            "explícito. Instala 'agix==1.9.0' o proporciona un objeto con "
            "'broadcast_state'."
        ) from exc
    virtual_qualia = getattr(orchestrator, "VirtualQualia", None)
    if virtual_qualia is None:
        raise RuntimeError(
            "No se encontró 'agix.orchestrator.VirtualQualia'. Verifica que "
            "la instalación de AGIX sea compatible con la versión 1.9.0."
        )
    return virtual_qualia


class Planner:
    """Genera planes utilizando la API de :mod:`agix`.

    Parameters
    ----------
    orchestrator:
        Instancia compatible con :class:`agix.orchestrator.VirtualQualia`
        utilizada para coordinar la difusión de estados. Si no se proporciona,
        se crea una instancia sin clientes registrados.
    """

    def __init__(self, orchestrator: Optional[Any] = None, qualia_node: Optional[Any] = None) -> None:
        self.orchestrator = orchestrator or _load_virtual_qualia()()
        self.qualia_node = qualia_node

        config_path = Path(__file__).resolve().parent / "config" / "agent_profile.json"
        try:
            with config_path.open("r", encoding="utf-8") as f:
                self.agent_profile = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as exc:
            logger.warning("Failed to load agent profile: %s", exc)
            self.agent_profile = {}

    def plan(self, state: Dict[str, Any]) -> List[Any]:
        """Genera un plan basado en el ``state`` dado.

        El estado se difunde a través del orquestador de `agix` y las
        respuestas obtenidas representan el plan resultante.

        Parameters
        ----------
        state:
            Descripción del objetivo o estado inicial.

        Returns
        -------
        list
            Lista de respuestas proporcionadas por los clientes del
            orquestador.
        """
        planning_state = dict(state)
        if self.qualia_node is not None:
            planning_state = self.qualia_node.enrich_request(
                planning_state, phase="planning"
            )
            if planning_state.get("qualia", {}).get("blocked"):
                blocked_plan = [{
                    "blocked": True,
                    "reason": planning_state["qualia"]["policy_action"],
                    "ethical_classification": planning_state["qualia"]["ethical_classification"],
                    "violated_constraints": planning_state["qualia"].get("violated_constraints", []),
                }]
                self.qualia_node.integrate_response(
                    blocked_plan, planning_state, phase="planning"
                )
                return blocked_plan
        try:
            plan = self.orchestrator.broadcast_state(planning_state)
            if self.qualia_node is not None:
                self.qualia_node.integrate_response(plan, planning_state, phase="planning")
            return plan
        except Exception:  # pragma: no cover - logging side effect
            logger.exception("Error al difundir el estado")
            return []

    def aplicar_sugerencias(self, sugerencias: Dict[str, Any]) -> None:
        """Ajusta el perfil del planificador según recomendaciones externas."""

        if not sugerencias:
            return
        self.agent_profile.update(sugerencias)
