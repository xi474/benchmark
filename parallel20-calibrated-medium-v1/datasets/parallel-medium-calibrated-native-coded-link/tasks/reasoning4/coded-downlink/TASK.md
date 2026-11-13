# Coded Downlink

Implement the business report defined in `engines/analysis/SPEC.md` using Python's standard library. The public input and worked output are `inputs/request.json` and `public_expected.json`.

The evaluator calls `transform(payload, contract)` in `engines/analysis/engine.py`. The input object described in the business specification is `payload["request"]`. Return the complete JSON-compatible report and leave caller inputs intact. Implement the work in any modules you choose. The included loader, clean-root builder and root delivery command work once the transform is implemented. You can edit the engine, add helpers, and edit run_all.py; retain all other supplied files. Run `python check.py` for the public example.

Independent builds must load the supplied root's input and write outputs/analysis.json. The root command must additionally produce outputs/final_report.json with task "L114", result, and results.analysis. The scorer compares parsed JSON. Object-key order and file whitespace are immaterial. All input cases follow the domain described in the specification.
