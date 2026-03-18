import gc
import pytest
from pathlib import Path
from pysmt.environment import Environment
from pysmt.oracles import get_logic
from pysmt.smtlib.parser import get_formula
from pysmt.walkers.nat_func_global_defn_lift_dag import NatFuncGlobalDefnLiftDagWalker
from pysmt.walkers.nat_func_partial_defn_lift_dag import NatFuncPartialDefnLiftDagWalker

SOLVER_NAME = "cvc5"
FORMULAS_DIR = Path(__file__).parent.parent / "formulas"
LIFTERS = [
    pytest.param(NatFuncGlobalDefnLiftDagWalker, id="global_defn"),
    pytest.param(NatFuncPartialDefnLiftDagWalker, id="partial_defn"),
]
SAT_FORMULAS = sorted((FORMULAS_DIR / "sat").glob("*.smt2"))
UNSAT_FORMULAS = sorted((FORMULAS_DIR / "unsat").glob("*.smt2"))
BENCHMARK_FORMULAS = SAT_FORMULAS + UNSAT_FORMULAS

def _collect(formulas):
    return pytest.mark.parametrize(
        "formula_path",
        formulas,
        ids=[f.stem for f in formulas],
    )

def _translate_and_solve(formula_path: Path, walker_cls) -> bool:
    with Environment() as env:
        with formula_path.open() as stream:
            formula = get_formula(stream, environment=env)
        walker = walker_cls(env=env)
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

@pytest.mark.parametrize("formula_path", BENCHMARK_FORMULAS, ids=[f.stem for f in BENCHMARK_FORMULAS])
def test_lifters_agree_on_benchmarks(formula_path):
    global_result = _translate_and_solve(formula_path, NatFuncGlobalDefnLiftDagWalker)
    partial_result = _translate_and_solve(formula_path, NatFuncPartialDefnLiftDagWalker)
    assert partial_result == global_result, \
        f"{formula_path.name} disagreed: global={global_result}, partial={partial_result}"

@pytest.mark.parametrize("walker_cls", LIFTERS)
@_collect(SAT_FORMULAS)
def test_sat(formula_path, walker_cls):
    assert _translate_and_solve(formula_path, walker_cls), \
        f"{formula_path.name} expected SAT but got UNSAT for {walker_cls.__name__}"

@pytest.mark.parametrize("walker_cls", LIFTERS)
@_collect(UNSAT_FORMULAS)
def test_unsat(formula_path, walker_cls):
    assert not _translate_and_solve(formula_path, walker_cls), \
        f"{formula_path.name} expected UNSAT but got SAT for {walker_cls.__name__}"
