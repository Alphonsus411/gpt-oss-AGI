import pytest

from agicore_core.reasoning_kernel import (
    _MAX_AST_NODES,
    _MAX_NUMERIC_VALUE,
    _MAX_RECURSION_DEPTH,
    _safe_eval_condition,
)


def test_rejects_expression_with_too_many_nodes():
    expr = "+".join(["1"] * (_MAX_AST_NODES + 1))
    with pytest.raises(ValueError):
        _safe_eval_condition(expr, {})


def test_rejects_expression_with_large_numbers():
    expr = f"{int(_MAX_NUMERIC_VALUE) + 1} > 0"
    with pytest.raises(ValueError):
        _safe_eval_condition(expr, {})


def test_rejects_expression_with_excessive_depth():
    expr = "1"
    for _ in range(_MAX_RECURSION_DEPTH + 1):
        expr = f"-({expr})"
    with pytest.raises(ValueError):
        _safe_eval_condition(expr, {})
