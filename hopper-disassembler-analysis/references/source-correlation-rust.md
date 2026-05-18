# Rust Source Correlation

Use this reference when a target is built from Rust sources or contains Rust standard-library/crate symbols.

## Contents

- [Workflow](#workflow)
- [Name Signals](#name-signals)
- [String Xref Signals](#string-xref-signals)
- [Rust Gotchas](#rust-gotchas)
- [Evidence Checklist](#evidence-checklist)

## Workflow

1. Pick one source function or module with a distinctive format string, error string, or public function name.
2. Export broad names and strings without pseudocode:

   ```bash
   scripts/run_hopper_export.sh \
     --max-procedures 4000 \
     --max-names 20000 \
     --max-strings 20000 \
     --max-string-xrefs 32 \
     --output /tmp/tool.rust-triage.hopper-snapshot.json \
     /path/to/tool
   ```

3. Search `names[].name` and `names[].demangled` for crate, module, and function fragments.
4. Search `strings[].value` for unique substrings, not only full source literals.
5. Use `strings[].xrefs_to[].procedure_demangled` and procedure callees to map source functions to binary procedures.
6. Rerun focused before reading large functions:

   ```bash
   scripts/run_hopper_export.sh \
     --procedure-pattern 'crate_name::module::run|0x100000978' \
     --max-procedures 10 \
     --max-basic-blocks 32 \
     --max-instructions-per-block 16 \
     --max-call-refs 64 \
     --output /tmp/tool.rust-focused.hopper-snapshot.json \
     /path/to/tool
   ```

## Name Signals

- Rust symbols commonly appear as Itanium-style mangled names such as `__ZN...`.
- Hopper demangling often preserves `crate::module::function::hash`; the hash suffix is compiler/build specific and should not be used as source evidence.
- Release binaries can still contain useful function symbols, but stripped binaries may require string xrefs, call structure, and imported/system calls instead.
- `main` is frequently a dispatch wrapper. Its callees can reveal module-level functions such as `fdx::run`, `rgx::run`, or `sedx::run`.

## String Xref Signals

Verified pattern from a Rust command-line wrapper:

- Source snippet: `rgx::run` emits metadata and truncation messages.
- Hopper name signal: `llm_inspect_wrappers::rgx::run::HASH` at a stable procedure address.
- Hopper string signal: a string row containing `@meta\ttool=rg-x` xrefed to the `rgx::run` procedure.
- Another row containing `rg-x truncated` was packed together with adjacent literals, but its xref still pointed to `rgx::run`.

Use substring matching because Rust/LLVM may pack adjacent literals or formatting fragments into one Hopper string row.

## Rust Gotchas

- Monomorphization and inlining can make one source function very large. In the verified CLI wrapper, one `run` function had hundreds of basic blocks; focused caps were required to keep snapshots usable.
- Decompiler output for optimized Rust can be poor for ownership, iterator, and formatting-heavy code. Prefer names, call edges, strings, and basic-block structure.
- Formatting macros split behavior across formatting machinery. A source `format!` or `eprintln!` may appear as partial strings plus calls into `core::fmt` or `std::io`.
- Panic and standard-library strings are noisy. Separate app-owned crate/module names from `std`, `core`, `alloc`, and dependency crates.
- Optional external demanglers such as `rustfilt` are useful for `nm` output, but Hopper `demangled` fields are the primary evidence inside snapshots.

## Evidence Checklist

Record:

- Source module/function and line span.
- Hopper procedure address, raw symbol, and demangled name.
- Matching string substrings, addresses, and xref addresses.
- Callees to app-owned functions or standard formatting/process APIs that match source behavior.
- Whether names are stripped, functions are inlined, or string rows are packed/truncated.
