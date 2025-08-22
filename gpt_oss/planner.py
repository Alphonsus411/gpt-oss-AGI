"""Planificador de alto nivel para ``gpt_oss``.

Este módulo ofrece la clase :class:`Planner`, la cual gestiona la intención
global, la lista de metas y el estado del modo activo del agente. El
planificador se integra con el flujo de razonamiento y orquestación
compartiendo esta información con componentes como ``ReasoningKernel``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import heapq

from .strategic_memory import Episode, StrategicMemory


@dataclass
class Planner:
    """Mantiene el estado de planificación del agente.

    Attributes
    ----------
    global_intent:
        Intención general u objetivo principal del agente.
    goals:
        Lista de metas específicas que se deben alcanzar.
    mode:
        Modo operativo actualmente activo (`creative`, `analytic` o `deductive`).
    mode_parameters:
        Conjunto de parámetros asociados al modo activo (temperatura, heurísticas, etc.).
    """

    global_intent: Optional[str] = None
    goals: List[Tuple[int, str]] = field(default_factory=list)
    mode: Optional[str] = None
    mode_parameters: Dict[str, Any] = field(default_factory=dict)
    memory: Optional[StrategicMemory] = None

    def set_intention(self, intent: str) -> None:
        """Define la intención global del agente.

        Parámetros
        ----------
        intent:
            Descripción de la intención u objetivo general.
        """

        self.global_intent = intent

    def add_goal(self, goal: str, prioridad: int) -> None:
        """Agrega una meta con una prioridad dada.

        Las metas se gestionan internamente con una cola de prioridad para
        facilitar la extracción de la próxima meta más importante.

        Parámetros
        ----------
        goal:
            Descripción de la meta a añadir.
        prioridad:
            Valor numérico que indica la importancia de la meta. Valores más
            altos representan mayor prioridad.

        Errores
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

        Devuelve
        -------
        str or None
            La descripción de la meta más prioritaria o ``None`` si no hay
            metas registradas.
        """

        if not self.goals:
            return None
        _, goal = heapq.heappop(self.goals)
        return goal

    def list_goals(self) -> List[str]:
        """Devuelve las metas ordenadas por prioridad sin modificarlas.

        Devuelve
        -------
        List[str]
            Lista de metas pendientes de alcanzar, ordenadas de la más a la
            menos prioritaria.
        """

        return [goal for _, goal in sorted(self.goals)]

    def get_intention(self) -> Optional[str]:
        """Recupera la intención global actualmente definida."""

        return self.global_intent

    # --- Gestión de modos -------------------------------------------------
    def activate_mode(self, tipo: str) -> None:
        """Activa un modo de operación y configura sus parámetros.

        Si existe memoria estratégica, consulta episodios previos exitosos del
        mismo modo para ajustar parámetros como la temperatura en función de los
        resultados observados.

        Parámetros
        ----------
        tipo:
            Cadena que identifica el modo a activar. Los valores aceptados son
            ``"creative"``, ``"analytic"`` y ``"deductive"``.

        Errores
        ------
        ValueError
            Si el modo solicitado no está soportado.
        """

        estrategias = {
            "creative": {"temperature": 1.0, "heuristic": "divergent"},
            "analytic": {"temperature": 0.5, "heuristic": "critical"},
            "deductive": {"temperature": 0.2, "heuristic": "logical"},
        }

        if tipo not in estrategias:
            raise ValueError(f"Modo no soportado: {tipo}")

        self.mode = tipo
        parametros = estrategias[tipo].copy()
        if self.memory is not None:
            episodios = self.memory.query({"mode": tipo, "outcome": "success"})
            temps = []
            for ep in episodios:
                valor = ep.metadata.get("temperature")
                if isinstance(valor, (int, float)):
                    temps.append(valor)
            if temps:
                parametros["temperature"] = sum(temps) / len(temps)
        self.mode_parameters = parametros

    def attach_memory(self, memory: StrategicMemory) -> None:
        """Asocia una memoria estratégica al planificador."""

        self.memory = memory

    def record_episode(self, entrada: Any, accion: Any, resultado: Any) -> None:
        """Registra un episodio del modo actual en la memoria.

        El episodio incluye el modo activo y sus parámetros para que futuras
        activaciones puedan ajustar dichos valores según el desempeño previo.

        Parámetros
        ----------
        entrada:
            Información de entrada procesada.
        accion:
            Acción realizada.
        resultado:
            Desempeño obtenido (``success``, ``failure``, etc.).
        """

        if self.memory is None:
            return
        episodio = Episode(
            timestamp=datetime.now(),
            input=entrada,
            action=accion,
            outcome=resultado,
            metadata={
                "mode": self.mode,
                "temperature": self.mode_parameters.get("temperature"),
            },
        )
        self.memory.add_episode(episodio)

    def current_mode(self) -> Optional[str]:
        """Devuelve el modo actualmente activo, o ``None`` si no hay modo."""

        return self.mode

    def get_mode_parameters(self) -> Dict[str, Any]:
        """Obtiene los parámetros asociados al modo activo.

        Devuelve
        -------
        Dict[str, Any]
            Diccionario con los parámetros del modo actual (vacío si no hay
            modo activo).
        """

        return self.mode_parameters
