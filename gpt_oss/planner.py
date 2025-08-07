"""Planificador de alto nivel para ``gpt_oss``.

Este módulo ofrece la clase :class:`Planner`, la cual gestiona la intención
global, la lista de metas y el estado del modo activo del agente. El
planificador se integra con el flujo de razonamiento y orquestación
compartiendo esta información con componentes como ``ReasoningKernel``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


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
    goals: List[str] = field(default_factory=list)
    active_mode: bool = False
