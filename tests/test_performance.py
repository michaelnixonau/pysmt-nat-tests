import logging
from glob import glob
from pysmt.shortcuts import reset_env, read_smtlib, Solver
from pysmt.walkers.nat_func_global_defn_lift_dag import NatFuncGlobalDefnLiftDagWalker
from pysmt.exceptions import SolverReturnedUnknownResultError
from time import time
from pathlib import Path

# Parameters
TIMEOUT = 30 # Timeout for cvc5 in seconds
INPUT_DIR = "seventeen_provers"
OUTPUT_FILE = "test_results.csv"
LOG_FILE = "test_errors.log"

# Logging setup
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.ERROR,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

files = glob(f"{INPUT_DIR}/**/*.smt2", recursive=True)

"""
Takes in a file and returns the lifted formula.
"""
def preprocess(file):
    reset_env()
    formula = read_smtlib(file)
    lifted_formula = NatFuncGlobalDefnLiftDagWalker(env=env).walk(formula)
    return lifted_formula

    
with open(OUTPUT_FILE, "x") as test_results:
    test_results.write("file,preprocess_time,solve_time,total_time,solve_result\n")

    for f in files:
        env = reset_env()

        # 1. PREPROCESSING
        start_preproc = time()
        try:
            lifted_formula = preprocess(f)
        except Exception:
            logging.exception("Preprocessing failed for file: %s", f)
            test_results.write(f"{f},error,NA,NA,NA\n")
            continue    
        preprocess_time = time() - start_preproc

        # 2. SOLVING (In-Memory)
        start_solve = time()
        solve_result = "error"
        
        try:
            # We pass the timeout to cvc5 in milliseconds via solver_options
            cvc5_options = {'tlimit': str(TIMEOUT * 1000)}
            
            with Solver(name="cvc5", solver_options=cvc5_options) as solver:
                solver.add_assertion(lifted_formula)
                
                # solve() returns True (sat) or False (unsat)
                is_sat = solver.solve()
                solve_result = "sat" if is_sat else "unsat"

        except SolverReturnedUnknownResultError:
            # This is typically thrown if the solver times out or gives up
            solve_result = "timeout_or_unknown"
            logging.warning("Solver returned unknown/timeout for %s", f)
        except Exception:
            logging.exception("Solver execution failed natively for %s", f)
            solve_result = "solver_error"
        finally:
            solve_time = time() - start_solve

        total_time = preprocess_time + solve_time

        # Write the test results
        test_results.write(f"{f},{preprocess_time},{solve_time},{total_time},{solve_result}\n")