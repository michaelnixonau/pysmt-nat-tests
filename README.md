# PySMT Nat Tests

A test suite for our fork of PySMT designed to support natural numbers natively.

## Set up environment

Ensure `pysmt_nat` and this repo are co-located in the same parent directory.

```bash
conda create -n smt-nat python=3.12 -y
conda activate smt-nat

cd ../pysmt_nat
pip install -e .

cd ../pysmt-nat-tests
pip install -r requirements.txt
```

## Tests

Test formulas live in the `formulas` directory. There are two subdirectories:
- `sat`: For formulas that should resolve to `SAT`
- `unsat`: For formulas that should resolve to `UNSAT`

We grab all the formulas and test their solver output against the expectation.

Run `pytest` to execute test suite.