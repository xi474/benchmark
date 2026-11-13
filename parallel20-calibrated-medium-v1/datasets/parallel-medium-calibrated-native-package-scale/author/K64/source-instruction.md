# Synthetic package constraint solver

Implement `/app/workspace/project` to satisfy the complete project-defined contract in `/app/workspace/README.md`. Run `python -m project.cli --input DIR --output FILE`. The public example is under `/app/workspace/fixtures/public/input`. You may choose your own implementation and work division; no Agent DAG or parallel call count is required.

All package IDs, versions and constraints are synthetic. No package registry, network, GPU or external solver is needed. Invalid top-level input must fail without output. Valid input must yield a deterministic lockfile or conflict evidence and must leave the input bytes unchanged.
