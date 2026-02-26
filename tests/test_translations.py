import pytest
from pathlib import Path
from pysmt.shortcuts import is_sat, is_unsat
from pysmt.smtlib.parser import get_formula

SOLVER_NAME = "cvc5"
FORMULAS_DIR = Path(__file__).parent.parent / "formulas"

def _collect(expected_sat: bool):
    subdir = FORMULAS_DIR / ("sat" if expected_sat else "unsat")
    files = sorted(subdir.glob("*.smt2")) if subdir.is_dir() else []
    return pytest.mark.parametrize(
        "formula_path",
        files,
        ids=[f.stem for f in files],
    )

@_collect(expected_sat=True)
def test_sat(formula_path):
    formula = get_formula(formula_path.open())
    assert is_sat(formula, solver_name=SOLVER_NAME), \
        f"{formula_path.name} expected SAT but got UNSAT"

@_collect(expected_sat=False)
def test_unsat(formula_path):
    formula = get_formula(formula_path.open())
    assert is_unsat(formula, solver_name=SOLVER_NAME), \
        f"{formula_path.name} expected UNSAT but got SAT"