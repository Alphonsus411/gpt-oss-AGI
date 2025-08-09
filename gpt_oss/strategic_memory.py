"""Utilities for managing strategic memory and episodic data."""

from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List


@dataclass
class Episode:
    """Representa una interacción con información contextual.

    Attributes
    ----------
    timestamp:
        Momento en el que ocurrió el episodio.
    input:
        Datos de entrada proporcionados por el usuario u otra fuente.
    action:
        Acción realizada en respuesta a la entrada.
    outcome:
        Resultado de la acción realizada.
    metadata:
        Información adicional asociada al episodio.
    """

    timestamp: datetime
    input: Any
    action: Any
    outcome: Any
    metadata: Dict[str, Any] = field(default_factory=dict)


class StrategicMemory:
    """Almacena y gestiona información estratégica y episodios.

    Proporciona operaciones para guardar, recuperar y actualizar
    entradas identificadas por una clave, así como registrar
    interacciones o episodios que se pueden consultar posteriormente.
    """

    def __init__(self, max_episodes: int | None = None) -> None:
        """Inicializa las estructuras de almacenamiento internas.

        Parameters
        ----------
        max_episodes:
            Número máximo de episodios a conservar. Si es ``None``,
            la cantidad de episodios es ilimitada.
        """
        self._storage: Dict[str, Any] = {}
        self._episodes: List[Episode] = []
        self._max_episodes = max_episodes

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

    def add_episode(self, data: Episode) -> None:
        """Añade un nuevo episodio a la memoria.

        Parameters
        ----------
        data:
            Instancia de :class:`Episode` que contiene la información
            del episodio a almacenar.
        """

        if self._max_episodes is not None:
            while len(self._episodes) >= self._max_episodes:
                self._episodes.pop(0)
        self._episodes.append(data)

    def query(self, pattern: Dict[str, Any]) -> List[Episode]:
        """Busca episodios que coincidan con los campos proporcionados.

        Cada par clave-valor de ``pattern`` se compara con los atributos
        del episodio y con su metadato homónimo si el atributo no existe.

        Parameters
        ----------
        pattern:
            Diccionario con los campos y valores a buscar.

        Returns
        -------
        list[Episode]
            Lista de episodios que cumplen con el patrón.
        """

        resultados: List[Episode] = []
        for episodio in self._episodes:
            coincide = True
            for clave, valor in pattern.items():
                attr = getattr(episodio, clave, episodio.metadata.get(clave))
                if attr != valor:
                    coincide = False
                    break
            if coincide:
                resultados.append(episodio)
        return resultados

    def summarize(self) -> Dict[str, Any]:
        """Obtiene estadísticas generales de los episodios almacenados.

        Returns
        -------
        dict
            Diccionario con el total de episodios y las acciones y
            resultados más frecuentes.
        """

        acciones = Counter(ep.action for ep in self._episodes)
        resultados = Counter(ep.outcome for ep in self._episodes)
        return {
            "total": len(self._episodes),
            "actions": acciones.most_common(),
            "outcomes": resultados.most_common(),
        }
