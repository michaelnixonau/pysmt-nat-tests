import subprocess

from glob import glob
from pysmt.shortcuts import reset_env, read_smtlib, write_smtlib
from pysmt.walkers.nat_func_global_defn_lift_dag import NatFuncGlobalDefnLiftDagWalker
from time import time

# Parameters
CVC5_PATH = "cvc5" # TODO: Change this to your cvc5 path if not in PATH
TIMEOUT = 30 # Timeout for cvc5 in seconds
INPUT_DIR = "performance_benchmarks"
OUTPUT_FILE = "test_results.csv"

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
        # Reset the global environment to avoid interference between tests
        env = reset_env()

        # Start preprocessing and record time
        start_preproc = time()
        try:
            lifted_formula = preprocess(f)
        except Exception:
            # Record preprocessing error
            test_results.write(f"{f},error,NA,NA,NA\n")
            continue    

        end_preproc = time()
        preprocess_time = end_preproc - start_preproc


        # Write file to disk
        new_fname = f"lifted_{f}"
        new_script = write_smtlib(lifted_formula, new_fname)

        # Start solving and record time
        start_solve = time()

        # Capture result and check for timeout
        try: 
            # Running cvc5 with q just to make sure only the result is printed to stdout
            solve_result = subprocess.run([CVC5_PATH, new_fname, "-q"], timeout=TIMEOUT, stdout=subprocess.PIPE, text=True).stdout
        except subprocess.TimeoutExpired:
            solve_result = "timeout"
        finally:
            end_solve = time()
        solve_time = end_solve - start_solve
        total_time = preprocess_time + solve_time

        # Write the test results to csv
        test_results.write(f"{f},{preprocess_time},{solve_time},{total_time},{solve_result}\n")



            

        

        

    
    




        

    
