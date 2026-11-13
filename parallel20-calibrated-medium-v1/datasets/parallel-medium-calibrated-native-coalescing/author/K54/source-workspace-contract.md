# Synthetic single-assignment CFG register allocation

Implement `python -m project.cli INPUT_DIRECTORY OUTPUT_JSON` using `config.json` and `cfg.json`. Write the exact certificate below. All rules here are project-defined; no real ISA or compiler ABI is implied. Input bytes must remain unchanged; repeated output must be byte-identical. Hidden CFGs vary IDs, branches, backedges, phi relationships, calls, registers and precolors. No Agent decomposition is prescribed.

## Strict input schema

All objects/rows have exactly the stated keys. Missing or extra fields, duplicate IDs/definitions, malformed references and unreachable blocks are invalid and must exit nonzero. JSON booleans are not integers. Order of blocks, successor arrays and phi arrays is arbitrary; instruction order *within* a block is significant.

`config.json` is exactly `{registers,call_clobbered,precolors}`. `registers` is a nonempty ordered list of unique nonempty register strings. `call_clobbered` is a unique list of registers from that list. `precolors` maps any globally defined variable ID to one register. A precolor may conflict with another precolor or a call; such a well-formed input produces `UNSAT_PRECOLOR` output, rather than input failure.

`cfg.json` is exactly `{entry,parameters,blocks}`. `entry` is an existing block ID. `parameters` is a unique list of nonempty variable IDs, defined before the entry block. `blocks` is a nonempty list of unique-ID blocks, each exactly `{id,successors,phis,instructions}`. Every successor names a block, successors are unique, and all blocks must be reachable from entry. Each phi is exactly `{def,inputs}`: its `def` is a unique global variable definition, and `inputs` maps **exactly every predecessor block ID** to one already/globally defined variable ID. A backedge may therefore refer to a variable defined later in array order. Each instruction is exactly `{id,uses,def,call}`. Instruction IDs are globally unique nonempty strings. `uses` is a list of existing variable IDs (duplicates have set semantics for liveness); `def` is either null or a globally unique variable ID; `call` is a JSON boolean. All variables are parameters or exactly one phi/instruction definition. This contract checks single definition and phi predecessor completeness; it does not add a dominance-validity test.

## Phi-aware block liveness

For each block B, `phi_defs[B]` is its phi definitions. Traverse instructions forward with those defs already seen. `use[B]` contains every instruction-used variable not previously defined in B; `def[B]` contains phi and instruction definitions. Let `edge_use(B,S)` contain phi input variables in successor S selected by predecessor B. Repeatedly solve the least fixed point:

`out[B] = union over successors S of ((in[S] - phi_defs[S]) union edge_use(B,S))`

`in[B] = use[B] union (out[B] - def[B])`

Output `live_in`/`live_out` maps every block ID to a sorted unique variable list. Phi inputs belong to the **predecessor edge**, while phi results are defined in the successor.

## Conservative interference and call restriction

Start each block with `live=out[B]` and add an undirected edge for every pair simultaneously live. Traverse instructions in reverse order. Before processing a call instruction, add every `call_clobbered` register to `call_forbidden[v]` for each variable in `live_after`, excluding the instruction's own `def` if present. Then, for a non-null definition d, add interference edges between d and all other variables in `live_after`, remove d from live; add all instruction uses to live; add every pair in the updated live set as an interference edge. After all instructions, add pairwise edges within that live set and within `in[B]`. This is intentionally conservative at control-flow joins. Interference edges are sorted pairs `[smaller_ID,larger_ID]`, unique and sorted by pair; all variables including unused definitions receive locations. `call_forbidden` contains only variables with nonempty forbidden sets, with register lists sorted lexicographically.

## Allocation, spills and phi-edge copies

First reject any precolored variable whose assigned register is forbidden by a call: `status=UNSAT_PRECOLOR`, `reason=PRECOLOR_CALL_CLOBBER`. If none, reject any interfering pair assigned the same precolored register: `reason=PRECOLOR_INTERFERENCE`. Call rejection has priority. For either rejection still report liveness, interference and call_forbidden, but set `allocation_order=[]`, `locations={}`, `spills=[]`, `stack_slots=0`, `edge_moves=[]`.

Otherwise assign precolored variables first, sorted by variable ID. For all remaining variables, sort by descending interference degree, then variable ID ascending. This full sequence is `allocation_order`. For each remaining variable, choose the **first** register in `registers` input order that is neither call-forbidden nor already assigned to an interfering neighbor. If none exists, mark the variable spilled. After all register decisions, allocate spill slots in spilled-variable ID order: choose the smallest nonnegative slot not used by an already slotted interfering spilled neighbor. This permits reuse for noninterfering spills. `locations` maps all variables to `reg:REGISTER` or `stack:INDEX`, sorted by variable ID. `spills` is sorted variable IDs; `stack_slots` is one plus the maximum assigned slot, or zero if none.

For every CFG edge `(pred,succ)` sorted first by predecessor and then successor ID, generate an `edge_moves` row `{pred,succ,moves,cycle}`. For each phi in succ sorted by its `def`, its selected source is `inputs[pred]`. If source and phi-result locations differ, append `{def,source,from,to}` to `moves`; equal locations require no move. All moves on an edge are **parallel**; no sequential move schedule is requested. `cycle` is true iff the directed graph of distinct location transitions `from -> to` in these moves contains a directed cycle; otherwise false. Every CFG edge appears even with empty moves.

## Exact output

One JSON object exactly `{status,reason,live_in,live_out,interference,call_forbidden,allocation_order,locations,spills,stack_slots,edge_moves}`. `status` is `ALLOCATED` with JSON null reason when precolors are feasible, or `UNSAT_PRECOLOR` with one of the reasons above. Lists and maps follow the sorting rules given here. No actual machine code, spill load/store rewriting, or register move scheduling is needed.
