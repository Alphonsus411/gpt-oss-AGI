"""Ejecución de planes paso a paso mediante `agix`.

Este módulo proporciona la clase :class:`ReasoningKernel` que
interpreta un plan y difunde cada paso a través del orquestador de
`agix`.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from agix.orchestrator import VirtualQualia


class ReasoningKernel:
    """Ejecuta pasos de razonamiento usando la API de :mod:`agix`.

    Parameters
    ----------
    orchestrator:
        Instancia de :class:`agix.orchestrator.VirtualQualia` utilizada para
        coordinar la difusión de cada paso. Si no se proporciona, se crea una
        instancia sin clientes registrados.
    """

    def __init__(self, orchestrator: Optional[VirtualQualia] = None) -> None:
        self.orchestrator = orchestrator or VirtualQualia()

    def execute_step(self, state: Dict[str, Any]) -> List[Any]:
        """Difunde un único paso del plan y devuelve la respuesta.

        Parameters
        ----------
        state:
            Descripción del paso a ejecutar.

        Returns
        -------
        list
            Respuestas proporcionadas por los clientes registrados.
        """

        return self.orchestrator.broadcast_state(state)

    def execute_plan(self, plan: List[Dict[str, Any]]) -> List[List[Any]]:
        """Ejecuta secuencialmente todos los pasos de ``plan``.

        Parameters
        ----------
        plan:
            Lista de descripciones de pasos a ejecutar.

        Returns
        -------
        list of lists
            Cada elemento contiene las respuestas obtenidas para un paso.
        """

        return [self.execute_step(step) for step in plan]
