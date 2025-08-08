"""Evaluador metacognitivo para los ciclos del núcleo AGI."""

from __future__ import annotations

from typing import Any, Dict, List


class MetaEvaluator:
    """Evalúa el desempeño general y propone mejoras estructurales."""

    def __init__(self) -> None:
        """Inicializa el evaluador sin historial previo."""
        self.historial_metricas: List[Dict[str, Any]] = []
        self.sugerencias: List[Dict[str, Any]] = []

    def evaluar_ciclo(self, resultados: Dict[str, Any]) -> Dict[str, Any]:
        """Procesa las métricas de un ciclo de ejecución.

        Parameters
        ----------
        resultados:
            Métricas generadas por los componentes internos durante la iteración.

        Returns
        -------
        dict
            Resumen numérico de las métricas procesadas.
        """
        resumen: Dict[str, Any] = {}
        for clave, valor in resultados.items():
            if isinstance(valor, (int, float)):
                resumen[clave] = valor
        self.historial_metricas.append(resumen)
        return {"resumen": resumen}

    def sugerir_reconfiguracion(self, historial: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Genera sugerencias de ajuste basadas en métricas previas.

        Parameters
        ----------
        historial:
            Lista cronológica de métricas de iteraciones anteriores.

        Returns
        -------
        dict
            Recomendaciones de cambios en la configuración interna.
        """
        if not historial:
            return {}

        recomendaciones: Dict[str, Any] = {}
        promedio_error = sum(d.get("error", 0.0) for d in historial) / len(historial)
        if promedio_error > 0.5:
            recomendaciones["error"] = "disminuir tasa de aprendizaje"
        promedio_tiempo = sum(d.get("tiempo", 0.0) for d in historial) / len(historial)
        if promedio_tiempo > 1.0:
            recomendaciones["tiempo"] = "optimizar componentes críticos"
        return recomendaciones

    def reflexionar(self, historial: List[Dict[str, Any]]) -> None:
        """Actualiza el estado del evaluador con aprendizaje estructural.

        Parameters
        ----------
        historial:
            Registro de métricas sobre el que se desea reflexionar.
        """
        sugerencia = self.sugerir_reconfiguracion(historial)
        if sugerencia:
            self.sugerencias.append(sugerencia)
