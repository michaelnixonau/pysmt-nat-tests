import gc
import pytest
from pathlib import Path
from pysmt.environment import Environment
from pysmt.oracles import get_logic
from pysmt.smtlib.parser import get_formula
from pysmt.typing import NAT
from pysmt.walkers.nat_func_global_defn_lift_dag import NatFuncGlobalDefnLiftDagWalker

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

def _translate_and_solve(formula_path: Path) -> bool:
    with Environment() as env:
        with formula_path.open() as stream:
            formula = get_formula(stream, environment=env)

        walker = NatFuncGlobalDefnLiftDagWalker(env=env)
        translated = walker.walk(formula)

        logic = get_logic(translated, env)
        with env.factory.Solver(
            name=SOLVER_NAME,
            logic=logic,
            generate_models=False,
            incremental=False,
        ) as solver:
            solver.add_assertion(translated)
            result = solver.solve()

        gc.collect()  # Manual garbage collection to prevent segfaults

        return result

@_collect(expected_sat=True)
def test_sat(formula_path):
    assert _translate_and_solve(formula_path), \
        f"{formula_path.name} expected SAT but got UNSAT"

@_collect(expected_sat=False)
def test_unsat(formula_path):
    assert not _translate_and_solve(formula_path), \
        f"{formula_path.name} expected UNSAT but got SAT"
