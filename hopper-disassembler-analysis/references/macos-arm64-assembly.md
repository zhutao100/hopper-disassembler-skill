# macOS arm64 and arm64e Assembly

Use this reference when Hopper evidence requires instruction-level reasoning on Apple Silicon targets. Keep this as an analysis guide, not a target-specific patch recipe.

## Fast Orientation

|Concept|What to check|
|-|-|
|Slice|Confirm `arm64` vs `arm64e`; do not assume the active host slice is the only shipped slice.|
|Base address|Record Hopper virtual address, segment `vmaddr`, section, and file offset.|
|Function shape|Check prologue, epilogue, calls, xrefs, and basic-block boundaries before interpreting one instruction.|
|ABI|Use Apple platform ABI conventions; do not transplant generic Linux AArch64 assumptions blindly.|
|Pointer authentication|On `arm64e`, PAC instructions and authenticated branch/return behavior can be semantically important.|
|Mutation|Only change authorized copies, keep same-size instruction constraints unless rebuilding through a proper linker, and re-sign outputs.|

## Register and Calling-Convention Landmarks

Common AArch64/Apple-platform landmarks:

- `x0`-`x7`: integer/pointer arguments and return values; `x0` is also Objective-C `self` in `objc_msgSend`.
- `x1`: second argument; Objective-C selector (`_cmd`) in `objc_msgSend`.
- `x8`: indirect result location or scratch depending on call shape.
- `x9`-`x15`: caller-saved temporaries.
- `x16`/`x17`: intra-procedure-call scratch registers often used by stubs/veneers.
- `x18`: platform register on Apple platforms; treat as reserved unless you have ABI-specific proof.
- `x19`-`x28`: callee-saved registers.
- `x29`: frame pointer.
- `x30`: link register.
- `sp`: stack pointer; maintain 16-byte alignment at public call boundaries.
- `wN`: low 32 bits of `xN`; writes to `wN` zero-extend into `xN`.

Floating-point/SIMD arguments and returns use `v0`-`v7`/`q0`-`q7` according to ABI rules.

## Instruction Patterns Worth Recognizing

|Pattern|Meaning|Analysis cue|
|-|-|-|
|`adrp xN, ...` + `add xN, xN, ...`|Page-relative address materialization|Resolve both instructions and any relocation/stub context.|
|`ldr xN, [xM, #imm]`|Pointer/value load|Identify whether the base is stack, global, object, or GOT/stub.|
|`str xN, [sp, #imm]`|Save local/callee state|Do not infer behavior from stack traffic alone.|
|`bl target`|Call and set link register|Check target name, import stub, and callee side effects.|
|`blr xN`|Indirect call|Look for vtable, block, Swift witness table, callback, or function pointer setup.|
|`b target`|Unconditional branch|May be tail call, jump table branch, or local control flow.|
|`ret`|Return via link register|On arm64e, return authentication may be folded into surrounding instructions.|
|`cmp`/`subs` + `b.cond`|Conditional branch after comparison|Read flags producer and branch condition together.|
|`cbz`/`cbnz`|Compare register against zero and branch|Often used for nil/null or boolean checks.|
|`tbz`/`tbnz`|Test bit and branch|Common in flags, option sets, tagged values, Swift metadata, and Objective-C runtime state.|
|`ccmp`/`csel`/`csinc`|Conditional compare/select|Decompilers can obscure these; inspect flags and paths manually.|

## Common Branch Conditions

|Mnemonic|Condition|
|-|-|
|`b.eq`/`b.ne`|Equal/not equal, zero/nonzero after compare.|
|`b.cs`/`b.cc`|Unsigned carry set/clear; also `hs`/`lo`.|
|`b.mi`/`b.pl`|Negative/positive-or-zero.|
|`b.vs`/`b.vc`|Overflow set/clear.|
|`b.hi`/`b.ls`|Unsigned greater than / less-or-same.|
|`b.ge`/`b.lt`|Signed greater-or-equal / less-than.|
|`b.gt`/`b.le`|Signed greater-than / less-or-equal.|

When validating branch behavior, record:

- The flag-producing instruction.
- The condition mnemonic.
- Both target addresses.
- The side effects in each successor block.
- Any incoming xrefs that skip the branch.

## arm64e and Pointer Authentication Cautions

Pointer authentication changes how some code should be interpreted and modified:

- PAC instructions may appear in prologues/epilogues or around indirect calls.
- Return sequences can include authenticated return forms or explicit authenticate+return patterns.
- Function pointers, Objective-C/Swift metadata pointers, vtables, and callbacks can be signed or authenticated.
- Patching a branch or return near PAC code without understanding the signing context can create crashes that look unrelated to the patch site.
- Prefer semantic changes in source or at stable call boundaries when available. For binary-only authorized work, keep changes minimal and validate on the same architecture slice.

Useful instruction families to recognize include `pac*`, `aut*`, `xpac*`, `bra*`, `blr*` authenticated variants, and authenticated return forms. Hopper naming and decoding may vary by version.

## Objective-C and Swift Signals

Objective-C:

- `objc_msgSend` uses `x0` as receiver and `x1` as selector.
- Selector strings and Objective-C method lists are strong orientation signals.
- Message send side effects depend on dynamic dispatch; use class/method metadata and call-site context.

Swift:

- Prefer demangled names from Hopper, `swift-demangle`, `nm`, or `atos` output.
- Expect generic specialization, thunks, witness tables, metadata accessors, retain/release traffic, and bridge calls.
- Optimized Swift can inline closures and split source-level logic across runtime helpers.
- Use unique strings and xrefs to locate source behavior before reading pseudocode.

Rust/C/C++:

- Rust names may appear as Itanium-style mangled symbols or demangled crate paths.
- C++ uses ABI-specific mangling; use `c++filt`, `llvm-cxxfilt`, or Hopper demangling.
- Stripped binaries require more reliance on string xrefs, imports, call graph, and section data.

## Assembly Modification Discipline

For authorized mutation only:

1. Work on a copied thin slice or a generated workspace, never the installed original.
2. Determine whether a change is instruction-local, same-size, and architecture-specific.
3. Preserve instruction alignment and branch reach constraints.
4. Avoid creating new literal references unless a proper assembler/linker workflow relocates them.
5. Re-run disassembly after modification and compare the specific basic block.
6. Recompute address/file-offset mapping for the final output.
7. Re-sign the output according to the test or distribution path.
8. Run in a disposable sandbox/VM before any broader execution.

## Evidence Template

```text
Architecture: arm64 or arm64e
Hopper VA: 0x...
Slice-relative file offset: 0x...
Fat-file absolute offset: 0x... or n/a
Segment/section: __TEXT,__text
Procedure: raw + demangled name
Instruction(s): exact mnemonic + operands
Flag producer: address + instruction, if branch-dependent
Successor blocks: addresses + observed side effects
Corroboration: strings/xrefs/imports/callees/source lines
Confidence: high/medium/low + reason
```
