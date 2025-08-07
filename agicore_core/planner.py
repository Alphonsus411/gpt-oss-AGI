"""Herramientas de planificación usando `agix`.

Este módulo expone la clase :class:`Planner` que genera planes
sencillos mediante la API de `agix`. Su objetivo es mostrar cómo
integrar las capacidades de orquestación de `agix` en componentes
de planificación.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from agix.orchestrator import VirtualQualia


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

        return self.orchestrator.broadcast_state(state)
