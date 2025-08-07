"""Planificador de alto nivel para ``gpt_oss``.

Este módulo ofrece la clase :class:`Planner`, la cual gestiona la intención
global, la lista de metas y el estado del modo activo del agente. El
planificador se integra con el flujo de razonamiento y orquestación
compartiendo esta información con componentes como ``ReasoningKernel``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import heapq


@dataclass
class Planner:
    """Mantiene el estado de planificación del agente.

    Attributes
    ----------
    global_intent:
        Intención general u objetivo principal del agente.
    goals:
        Lista de metas específicas que se deben alcanzar.
    active_mode:
        Indica si el planificador está actualmente en modo activo.
    """

    global_intent: Optional[str] = None
    goals: List[Tuple[int, str]] = field(default_factory=list)
    active_mode: bool = False

    def set_intention(self, intent: str) -> None:
        """Define la intención global del agente.

        Parameters
        ----------
        intent:
            Descripción de la intención u objetivo general.
        """

        self.global_intent = intent

    def add_goal(self, goal: str, prioridad: int) -> None:
        """Agrega una meta con una prioridad dada.

        Las metas se gestionan internamente con una cola de prioridad para
        facilitar la extracción de la próxima meta más importante.

        Parameters
        ----------
        goal:
            Descripción de la meta a añadir.
        prioridad:
            Valor numérico que indica la importancia de la meta. Valores más
            altos representan mayor prioridad.

        Raises
        ------
        ValueError
            Si ``prioridad`` es negativa.
        """

        if prioridad < 0:
            raise ValueError("La prioridad no puede ser negativa")
        # heapq implementa una cola de prioridad mínima, por lo que se usa el
        # negativo de ``prioridad`` para que los números más altos se extraigan
        # primero.
        heapq.heappush(self.goals, (-prioridad, goal))

    def get_next_goal(self) -> Optional[str]:
        """Obtiene la siguiente meta con mayor prioridad.

        Returns
        -------
        str or None
            La descripción de la meta más prioritaria o ``None`` si no hay
            metas registradas.
        """

        if not self.goals:
            return None
        _, goal = heapq.heappop(self.goals)
        return goal
