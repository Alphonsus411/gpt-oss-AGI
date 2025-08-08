"""Núcleo de razonamiento con gestión de estado."""

from __future__ import annotations

from typing import Any, Dict, Iterator, List
import time
from datetime import datetime
import ast
import operator as op

from meta_router import MetaRouter
from gpt_oss.strategic_memory import Episode, StrategicMemory

from .planner import Planner
from .meta_evaluator import MetaEvaluator


_BIN_OPS = {
    ast.Add: op.add,
    ast.Sub: op.sub,
    ast.Mult: op.mul,
    ast.Div: op.truediv,
    ast.Mod: op.mod,
    ast.Pow: op.pow,
}

_CMP_OPS = {
    ast.Eq: op.eq,
    ast.NotEq: op.ne,
    ast.Lt: op.lt,
    ast.LtE: op.le,
    ast.Gt: op.gt,
    ast.GtE: op.ge,
}

_UNARY_OPS = {
    ast.Not: op.not_,
    ast.USub: op.neg,
}

# Límites de seguridad para la evaluación de expresiones
_MAX_AST_NODES = 100
_MAX_NUMERIC_VALUE = 1e6
_MAX_RECURSION_DEPTH = 50

# Claves de metadata permitidas para hidratar el estado desde la memoria
_ALLOWED_METADATA_KEYS = {
    "context",
    "mode",
    "temperature",
    "goals",
    "result",
    "last_token",
}


def _safe_eval_condition(expr: str, variables: Dict[str, Any]) -> bool:
    """Evalúa ``expr`` de forma segura.

    Operadores permitidos: ``and``, ``or``, ``not``; ``+``, ``-``, ``*``, ``/``,
    ``%`` y ``**``; comparaciones ``==``, ``!=``, ``<``, ``<=``, ``>`` y ``>=``.
    Solo pueden usarse variables presentes en ``variables``. No se permiten
    llamadas a funciones ni acceso a atributos. Además, se limita la complejidad
    de la expresión, la magnitud de los valores numéricos y la profundidad de
    la recursión durante la evaluación.
    """

    tree = ast.parse(expr, mode="eval")
    if sum(1 for _ in ast.walk(tree)) > _MAX_AST_NODES:
        raise ValueError("Expresión demasiado compleja")

    def _check_number(value: Any) -> Any:
        if isinstance(value, (int, float)) and abs(value) > _MAX_NUMERIC_VALUE:
            raise ValueError("Valor numérico fuera de rango")
        return value

    def _eval(node: ast.AST, depth: int = 0):  # type: ignore[return-type]
        if depth > _MAX_RECURSION_DEPTH:
            raise ValueError("Expresión demasiado profunda")
        if isinstance(node, ast.Expression):
            return _eval(node.body, depth + 1)
        if isinstance(node, ast.BoolOp):
            if isinstance(node.op, ast.And):
                return all(_eval(v, depth + 1) for v in node.values)
            if isinstance(node.op, ast.Or):
                return any(_eval(v, depth + 1) for v in node.values)
            raise ValueError("Operador booleano no permitido")
        if isinstance(node, ast.BinOp) and type(node.op) in _BIN_OPS:
            result = _BIN_OPS[type(node.op)](
                _eval(node.left, depth + 1), _eval(node.right, depth + 1)
            )
            return _check_number(result)
        if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPS:
            result = _UNARY_OPS[type(node.op)](_eval(node.operand, depth + 1))
            return _check_number(result)
        if isinstance(node, ast.Compare):
            left = _eval(node.left, depth + 1)
            for op_node, comp in zip(node.ops, node.comparators):
                if type(op_node) not in _CMP_OPS:
                    raise ValueError("Operador de comparación no permitido")
                right = _eval(comp, depth + 1)
                if not _CMP_OPS[type(op_node)](left, right):
                    return False
                left = right
            return True
        if isinstance(node, ast.Name):
            if node.id in variables:
                return variables[node.id]
            raise ValueError(f"Variable no permitida: {node.id}")
        if isinstance(node, ast.Constant):
            return _check_number(node.value)
        raise ValueError("Expresión no permitida")

    return bool(_eval(tree))


class ReasoningKernel:
    """Coordina un planificador y un enrutador manteniendo estado interno."""

    def __init__(
        self,
        planner: Planner,
        router: MetaRouter,
        evaluator: MetaEvaluator | None = None,
        memory: StrategicMemory | None = None,
    ) -> None:
        self.planner = planner
        self.router = router
        self.evaluator = evaluator
        self.memory = memory
        self._state: Dict[str, Any] = {}
        self.history: List[Dict[str, Any]] = []
        self._token_generator: Iterator[Any] | None = None

    def set_state(self, state: Dict[str, Any]) -> None:
        """Establece el ``state`` inicial para el planificador."""

        self._state = state

    def get_state(self) -> Dict[str, Any]:
        """Devuelve el estado interno actual."""

        return self._state

    def evaluate_step(self, step: Dict[str, Any]) -> Any:
        """Evalúa un ``step`` con ramificación condicional.

        Cada ``step`` puede incluir las claves opcionales ``if``, ``then`` y
        ``else``. La condición indicada en ``if`` se analiza de forma segura en
        el contexto del estado actual. Se admiten operadores aritméticos básicos
        (``+``, ``-``, ``*``, ``/``, ``%``, ``**``), comparaciones (``==``, ``!=``,
        ``<``, ``<=``, ``>``, ``>=``) y operadores booleanos (``and``, ``or``,
        ``not``). Solo pueden referenciarse variables presentes en ``state``; no
        se permiten llamadas a funciones ni acceso a atributos. Dependiendo del
        resultado, se selecciona la rama ``then`` o ``else`` y se fusiona con el
        resto del paso y con el estado antes de delegar la ejecución al
        :class:`MetaRouter`.

        El resultado devuelto por el enrutador se incorpora al estado: si es un
        ``dict`` se combina mediante :py:meth:`dict.update`; en caso contrario se
        almacena bajo la clave ``"result"``.
        """

        step = dict(step)  # evitar mutaciones externas
        condition = step.pop("if", None)
        then_branch = step.pop("then", {})
        else_branch = step.pop("else", {})

        if condition is not None:
            if isinstance(condition, str):
                try:
                    condition_value = _safe_eval_condition(condition, self._state)
                except Exception:
                    condition_value = False
            else:
                condition_value = bool(condition)
            branch = then_branch if condition_value else else_branch
            step.update(branch)

        request: Dict[str, Any] = {**self._state, **step}
        result = self.router.route(request)

        if isinstance(result, dict):
            self._state.update(result)
        else:
            self._state["result"] = result

        introspeccion = None
        if self.evaluator is not None:
            introspeccion = self.evaluator.evaluar_ciclo(
                {"result": result, "state": self._state}
            )
        # Registrar paso e introspección para reflexiones futuras
        self.history.append({
            "step": step,
            "result": result,
            "introspeccion": introspeccion,
        })

        if self.memory is not None:
            episodio = Episode(
                timestamp=datetime.utcnow(),
                input=step,
                action="step",
                outcome=result,
                metadata=dict(self._state),
            )
            self.memory.add_episode(episodio)

        return result

    def run_token_cycle(
        self,
        token: Any,
        metas: Dict[str, Any],
        *,
        max_tokens: int | None = None,
    ) -> Iterator[Any]:
        """Genera tokens sucesivos delegando en ``MetaRouter``.

        Parameters
        ----------
        token:
            Token inicial recibido del :class:`Planner`.
        metas:
            Metadatos que incluyen las metas a satisfacer.
        max_tokens:
            Número máximo de tokens a generar. Si es ``None`` no hay límite.

        Yields
        ------
        Any
            Tokens producidos por el enrutador.
        """

        count = 0
        while max_tokens is None or count < max_tokens:
            if self.memory is not None:
                for episodio in self.memory.query(self._state):
                    metadata_filtrada = {
                        k: v
                        for k, v in episodio.metadata.items()
                        if k in _ALLOWED_METADATA_KEYS
                    }
                    self._state.update(metadata_filtrada)
            request: Dict[str, Any] = {**self._state, **metas, "token": token}
            siguiente = self.router.route(request)
            if siguiente is None:
                break
            if self.memory is not None:
                episodio = Episode(
                    timestamp=datetime.utcnow(),
                    input=token,
                    action="token",
                    outcome=siguiente,
                    metadata=dict(self._state),
                )
                self.memory.add_episode(episodio)
            self._state["last_token"] = siguiente
            yield siguiente
            count += 1
            token = siguiente

    def start_token_cycle(self, token: Any, metas: Dict[str, Any]) -> None:
        """Inicializa un ciclo de generación de tokens."""

        self._token_generator = self.run_token_cycle(token, metas)

    def continue_token_cycle(self) -> Any:
        """Avanza un paso en el ciclo de tokens iniciado."""

        if self._token_generator is None:
            raise ValueError("El ciclo de tokens no ha sido iniciado")
        start = time.perf_counter()
        try:
            token = next(self._token_generator)
        except StopIteration:
            self._token_generator = None
            return None
        latency = time.perf_counter() - start
        metricas = {"latencia": latency, "exito": True}
        introspeccion = None
        if self.evaluator is not None:
            introspeccion = self.evaluator.evaluar_ciclo(metricas)
        self.history.append({
            "token": token,
            "metricas": metricas,
            "introspeccion": introspeccion,
        })
        return token

    def run(self, max_iterations: int = 10) -> Dict[str, Any]:
        """Genera planes y ejecuta pasos hasta cumplir las metas.

        En cada iteración se obtiene un plan del :class:`Planner` utilizando el
        estado actual. Los pasos del plan se ejecutan mediante
        :meth:`evaluate_step` y se registran en ``history`` junto con el
        resultado o el error producido. El bucle finaliza si todas las metas
        están satisfechas o si se alcanza ``max_iterations``.

        Parameters
        ----------
        max_iterations:
            Número máximo de iteraciones del ciclo de planificación y
            ejecución.

        Returns
        -------
        dict
            El estado interno tras finalizar la ejecución.
        """

        if self.planner is None:
            raise ValueError("Se requiere un Planner para ejecutar 'run'")

        for _ in range(max_iterations):
            try:
                plan = self.planner.plan(self._state)
            except Exception as exc:  # pragma: no cover - planificación fallida
                self.history.append({"error": str(exc)})
                return self._state

            if isinstance(plan, dict) and "token" in plan:
                token = plan["token"]
                metas = {k: v for k, v in plan.items() if k != "token"}
                self.start_token_cycle(token, metas)
                for _ in range(max_iterations):
                    if self.continue_token_cycle() is None:
                        break
                if self.evaluator is not None:
                    sugerencia = self.evaluator.sugerir_reconfiguracion(self.history)
                    if sugerencia:
                        self._state.update(sugerencia)
                        if self.planner is not None and hasattr(self.planner, "aplicar_sugerencias"):
                            self.planner.aplicar_sugerencias(sugerencia)
                    self.evaluator.reflexionar(self.history)
                return self._state

            for step in plan:
                try:
                    self.evaluate_step(step)
                except Exception as exc:  # pragma: no cover - error del experto
                    self.history.append({"step": step, "error": str(exc)})
                    if self.evaluator is not None:
                        sugerencia = self.evaluator.sugerir_reconfiguracion(self.history)
                        if sugerencia:
                            self._state.update(sugerencia)
                            if self.planner is not None and hasattr(self.planner, "aplicar_sugerencias"):
                                self.planner.aplicar_sugerencias(sugerencia)
                        self.evaluator.reflexionar(self.history)
                    return self._state

                goals = self._state.get("goals", [])
                if isinstance(goals, list) and all(self._state.get(g) for g in goals):
                    if self.evaluator is not None:
                        sugerencia = self.evaluator.sugerir_reconfiguracion(self.history)
                        if sugerencia:
                            self._state.update(sugerencia)
                            if self.planner is not None and hasattr(self.planner, "aplicar_sugerencias"):
                                self.planner.aplicar_sugerencias(sugerencia)
                        self.evaluator.reflexionar(self.history)
                    return self._state

        if self.evaluator is not None:
            sugerencia = self.evaluator.sugerir_reconfiguracion(self.history)
            if sugerencia:
                self._state.update(sugerencia)
                if self.planner is not None and hasattr(self.planner, "aplicar_sugerencias"):
                    self.planner.aplicar_sugerencias(sugerencia)
            self.evaluator.reflexionar(self.history)

        return self._state
