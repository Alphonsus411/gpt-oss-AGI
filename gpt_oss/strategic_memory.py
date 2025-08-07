"""Utilities for managing strategic memory."""

from typing import Any, Dict


class StrategicMemory:
    """Almacena y gestiona información estratégica en memoria.

    Ofrece operaciones básicas para guardar, recuperar y actualizar
    entradas identificadas por una clave.
    """

    def __init__(self) -> None:
        """Inicializa la estructura de almacenamiento interna."""
        self._storage: Dict[str, Any] = {}

    def save(self, key: str, value: Any) -> None:
        """Guarda una nueva entrada en la memoria.

        Parameters
        ----------
        key:
            Clave con la que se identificará la entrada.
        value:
            Valor asociado a la clave.

        Raises
        ------
        ValueError
            Si la clave ya existe en la memoria.
        """
        if key in self._storage:
            raise ValueError(f"La clave '{key}' ya existe en la memoria.")
        self._storage[key] = value

    def get(self, key: str, default: Any | None = None) -> Any:
        """Recupera la entrada asociada a ``key``.

        Parameters
        ----------
        key:
            Clave de la entrada a recuperar.
        default:
            Valor por defecto a devolver si la clave no existe.

        Returns
        -------
        Any
            El valor asociado a la clave o ``default`` si no se encuentra.
        """
        return self._storage.get(key, default)

    def update(self, key: str, value: Any) -> None:
        """Actualiza una entrada existente en la memoria.

        Parameters
        ----------
        key:
            Clave de la entrada a actualizar.
        value:
            Nuevo valor para la entrada.

        Raises
        ------
        KeyError
            Si la clave no existe en la memoria.
        """
        if key not in self._storage:
            raise KeyError(f"La clave '{key}' no se encuentra en la memoria.")
        self._storage[key] = value
