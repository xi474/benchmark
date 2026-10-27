# Linux supply-chain recovery

Repair a supply-chain recovery repository whose independent verification packages become available only after the shared recovery manifest is materialized.

Start by reading `check.py` and `materialize.py`. Run `python3 materialize.py` to validate the shared input boundary and create the currently executable product packages. Inspect each generated package contract and focused check, implement every missing module, run the package checks, then run `python3 check.py`.

Do not change `check.py`, `materialize.py`, generated contracts, or generated focused checks. All validation is local and uses the Python standard library.
