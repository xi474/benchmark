# SDK compatibility upgrade

The SDK must accept both v1 and v2 clients while producing canonical v2 data.

* `config/loader.py::load_config` merges defaults, file data, environment overrides and explicit overrides in that precedence order; nested dictionaries merge recursively and known scalar types are coerced.
* `cli/adapter.py::adapt_args` accepts legacy flags and new names, detects conflicting aliases, and returns a canonical dictionary without mutating input.
* `reports/serializer.py::serialize_report` upgrades v1 records, preserves unknown metadata under `extensions`, sorts records deterministically, and emits canonical compact JSON bytes.

Examples and defaults are adjacent to each module. Do not modify them or `check.py`.


Stable internal SDK helpers are tested independently. Config owns `coerce.py`, `merge.py`, and `loader.py`; CLI owns `names.py`, `values.py`, and `adapter.py`; reports owns `upgrade.py`, `canonical.py`, and `serializer.py`. Each package includes a focused check that must pass without changing test or schema files.
