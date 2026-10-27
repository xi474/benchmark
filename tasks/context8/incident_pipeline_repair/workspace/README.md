# Incident pipeline compatibility repair

Three ingestion packages feed one incident view. Their public `parse` functions are stable, but legacy assumptions break mixed-version payloads.

* metrics accepts `value` or `samples`, drops non-finite values and reports min/max/mean with the source id.
* traces accepts flat spans or nested children, returns unique error services and the longest root-to-leaf duration.
* logs accepts plain lines and JSON lines, redacts token/password/secret values and counts severity case-insensitively.

See `*/examples.json` for concrete old/new inputs. `incident.py` is the already-correct root aggregator. Do not modify examples, `incident.py`, or `check.py`.


The repair spans stable helper interfaces used by other callers. Metrics owns `values.py`, `stats.py`, and `parser.py`; traces owns `graph.py`, `analysis.py`, and `parser.py`; logs owns `levels.py`, `redact.py`, and `parser.py`. Each package has a focused `check_module.py`; preserve these helper APIs and pass all checks.
