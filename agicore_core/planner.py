"""Herramientas de planificación usando `agix`.

Este módulo expone la clase :class:`Planner` que genera planes
sencillos mediante la API de `agix`. Su objetivo es mostrar cómo
integrar las capacidades de orquestación de `agix` en componentes
de planificación.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import json
import logging
from pathlib import Path

from agix.orchestrator import VirtualQualia

logger = logging.getLogger(__name__)


class Planner:
    """Genera planes utilizando la API de :mod:`agix`.

    Parameters
    ----------
    orchestrator:
        Instancia de :class:`agix.orchestrator.VirtualQualia` utilizada para
        coordinar la difusión de estados. Si no se proporciona, se crea una
        instancia sin clientes registrados.
    """

    def __init__(self, orchestrator: Optional[VirtualQualia] = None) -> None:
        self.orchestrator = orchestrator or VirtualQualia()

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
        try:
            return self.orchestrator.broadcast_state(state)
        except Exception:  # pragma: no cover - logging side effect
            logger.exception("Error al difundir el estado")
            return []

    def aplicar_sugerencias(self, sugerencias: Dict[str, Any]) -> None:
        """Ajusta el perfil del planificador según recomendaciones externas."""

        if not sugerencias:
            return
        self.agent_profile.update(sugerencias)
