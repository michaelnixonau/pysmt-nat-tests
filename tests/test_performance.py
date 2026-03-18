import gc
import csv
import logging
import multiprocessing
import os
import concurrent.futures
from pathlib import Path
from time import time

from pysmt.solvers.cvcfive import CVC5Solver
from pysmt.oracles import get_logic
from pysmt.exceptions import SolverReturnedUnknownResultError
from pysmt.shortcuts import read_smtlib, reset_env
from pysmt.walkers.nat_func_global_defn_lift_dag import NatFuncGlobalDefnLiftDagWalker
from tqdm import tqdm


BASE_DIR = Path(__file__).resolve().parents[1]
TIMEOUT = int(os.environ.get("BENCHMARK_TIMEOUT", "60"))
# Use mostly all cores, leaving one free for system stability
MAX_WORKERS = int(os.environ.get("BENCHMARK_WORKERS", max(1, multiprocessing.cpu_count() - 1)))
INPUT_DIR = Path(os.environ.get("BENCHMARK_INPUT_DIR", str(BASE_DIR / "smt-comp-sample1500")))
OUTPUT_FILE = Path(os.environ.get("BENCHMARK_OUTPUT_FILE", str(BASE_DIR / "test_results.csv")))
LOG_FILE = Path(os.environ.get("BENCHMARK_LOG_FILE", str(BASE_DIR / "test_errors.log")))


logging.basicConfig(
    filename=LOG_FILE,
    filemode="w",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)


def iter_smt2_files():
    return sorted(INPUT_DIR.rglob("*.smt2"))


def display_path(file_path):
    try:
        return file_path.relative_to(BASE_DIR).as_posix()
    except ValueError:
        return str(file_path)


def classify_preprocess_error(exc):
    message = str(exc).lower()
    if "not well-formed" in message:
        return "invalid_input_formula"
    return "preprocess_error"


def classify_solver_error(exc):
    message = str(exc).lower()
    if "argument type is not the type of the function's argument type" in message:
        return "solver_conversion_error"
    return "solver_error"


def classify_unknown_result(exc):
    message = str(exc).lower()
    timeout_markers = ("timeout", "time limit", "tlimit", "resource limit")
    if any(marker in message for marker in timeout_markers):
        return "timeout"
    return "unknown"


def solve_file(file_path, timeout_seconds, conn):
    try:
        start_preproc = time()
        env = reset_env()
        
        try:
            formula = read_smtlib(str(file_path))
            walker = NatFuncGlobalDefnLiftDagWalker(env=env)
            lifted_formula = walker.walk(formula)
        except Exception as exc:
            conn.send({
                "solve_result": classify_preprocess_error(exc),
                "preprocess_time": "error",
                "solve_time": "NA",
                "error": repr(exc)
            })
            return
            
        preprocess_time = time() - start_preproc

        logic = get_logic(lifted_formula, env)
        logic = logic.get_quantified_version() if not logic.is_quantified() else logic
        
        start_solve = time()
        unknown_detail = None
        try:
            with CVC5Solver(
                environment=env,
                logic=logic,
                solver_options={"tlimit": str(timeout_seconds * 1000)},
            ) as solver:
                solver.add_assertion(lifted_formula)
                solve_result = "sat" if solver.solve() else "unsat"
        except SolverReturnedUnknownResultError as exc:
            solve_result = classify_unknown_result(exc)
            unknown_detail = repr(exc)
        except Exception as exc:
            solve_result = classify_solver_error(exc)
            conn.send({
                "solve_result": solve_result,
                "preprocess_time": preprocess_time,
                "solve_time": time() - start_solve,
                "error": repr(exc),
            })
            return

        result = {
            "solve_result": solve_result, 
            "preprocess_time": preprocess_time,
            "solve_time": time() - start_solve
        }
        if unknown_detail is not None:
            result["error"] = unknown_detail
        conn.send(result)
    except Exception as exc:
        conn.send({
            "solve_result": "solver_process_error", 
            "preprocess_time": "NA", 
            "solve_time": "NA", 
            "error": repr(exc)
        })
    finally:
        conn.close()


def run_solver_with_timeout(file_path):
    ctx = multiprocessing.get_context("spawn")
    parent_conn, child_conn = ctx.Pipe(duplex=False)
    process = ctx.Process(target=solve_file, args=(str(file_path), TIMEOUT, child_conn))
    process.start()
    child_conn.close()
    process.join(TIMEOUT + 1)

    if process.is_alive():
        process.terminate()
        process.join()
        parent_conn.close()
        return {
            "solve_result": "wallclock_timeout",
            "preprocess_time": "NA", 
            "solve_time": float(TIMEOUT)
        }

    result = {"solve_result": "solver_process_error", "preprocess_time": "NA", "solve_time": "NA"}
    if parent_conn.poll():
        result.update(parent_conn.recv())
    parent_conn.close()
    gc.collect()  
    return result


def main():
    files = iter_smt2_files()

    with OUTPUT_FILE.open("w", newline="") as test_results:
        writer = csv.writer(test_results)
        writer.writerow(
            ["file", "preprocess_time", "solve_time", "total_time", "solve_result"]
        )

        # ThreadPoolExecutor to spawn processes concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            # Map the execution future to its file path so we can retrieve it later
            future_to_file = {
                executor.submit(run_solver_with_timeout, file_path): display_path(file_path)
                for file_path in files
            }

            # as_completed yields tasks as they finish, updating tqdm in real-time
            for future in tqdm(concurrent.futures.as_completed(future_to_file), total=len(files), desc="Processing SMT files", unit="file"):
                relative_file = future_to_file[future]
                
                try:
                    result = future.result()
                except Exception as exc:
                    # Catch catastrophic thread failures (highly unlikely)
                    logging.error("Thread execution failed for %s: %s", relative_file, repr(exc))
                    writer.writerow([relative_file, "error", "error", "error", "thread_executor_error"])
                    continue

                solve_result = result["solve_result"]
                preprocess_time = result.get("preprocess_time", "NA")
                solve_time = result.get("solve_time", "NA")

                if solve_result in ("invalid_input_formula", "preprocess_error"):
                    logging.error(
                        "Preprocessing failed for file: %s. Error: %s", 
                        relative_file, 
                        result.get("error", "unknown")
                    )
                    writer.writerow([relative_file, "error", "NA", "NA", solve_result])
                    continue

                if solve_result == "timeout":
                    logging.warning("Solver timed out internally for %s", relative_file)
                elif solve_result == "wallclock_timeout":
                    logging.warning("Wallclock timeout reached for %s", relative_file)
                elif solve_result == "unknown":
                    logging.warning(
                        "Solver returned unknown for %s: %s",
                        relative_file,
                        result.get("error", "no details"),
                    )
                elif solve_result not in {"sat", "unsat"}:
                    logging.error(
                        "Solver execution failed for %s: %s",
                        relative_file,
                        result.get("error", "no error details"),
                    )

                try:
                    total_time = preprocess_time + solve_time
                except TypeError:
                    total_time = "NA"

                writer.writerow([
                    relative_file,
                    preprocess_time,
                    solve_time,
                    total_time,
                    solve_result,
                ])


if __name__ == "__main__":
    main()
