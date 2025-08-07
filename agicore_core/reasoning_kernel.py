"""Núcleo de razonamiento con gestión de estado."""

from __future__ import annotations

from typing import Any, Dict

from meta_router import MetaRouter

from .planner import Planner


class ReasoningKernel:
    """Coordina un planificador y un enrutador manteniendo estado interno."""

    def __init__(self, planner: Planner, router: MetaRouter) -> None:
        self.planner = planner
        self.router = router
        self._state: Dict[str, Any] = {}

    def set_state(self, state: Dict[str, Any]) -> None:
        """Establece el ``state`` inicial para el planificador."""

        self._state = state

    def get_state(self) -> Dict[str, Any]:
        """Devuelve el estado interno actual."""

        return self._state
