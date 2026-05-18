# macOS Binary Analysis and Mutation Toolchains

Use this reference when deciding which tools to run before Hopper, alongside Hopper, or after an authorized change.

## Start With Host Inventory

Run the bundled inventory script first:

```bash
scripts/macos_toolchain_inventory.py --output /tmp/macos-toolchain.md
scripts/macos_toolchain_inventory.py --format json --output /tmp/macos-toolchain.json
```

The script records common Apple, LLVM, Hopper, and third-party tools without requiring them to be installed. On macOS, prefer `xcrun --find TOOL` for Apple developer tools and use `command -v TOOL` for Homebrew or standalone tools.

## Built-In and Apple Developer Tools

|Tool|Primary use|Mutation role|Notes|
|-|-|-|-|
|`file`|Fast file type and universal/thin hints|None|Good first check for app executables, dylibs, and helpers.|
|`lipo`|List, extract, thin, and create universal files|Recombine modified thin slices|Use `-info`, `-archs`, `-extract`, `-thin`, and `-create`.|
|`otool`|Mach-O headers, load commands, sections, symbols, disassembly|Verification|Use with `-hv`, `-l`, `-L`, `-Iv`, `-tV`, `-s`.|
|`vtool`|Build-version/source-version load commands|Narrow load-command edits|Writes only when `-output` is supplied; verify signatures afterwards.|
|`dyld_info`|Dyld binds, exports, fixups, chained fixups|Verification|Useful on modern dyld chained-fixups binaries.|
|`nm`|Symbols|Verification|Pipe through demanglers when useful.|
|`strings`|Printable strings|Triage|Use as a fast pre-Hopper string search; not authoritative.|
|`dwarfdump`|DWARF debug info and UUIDs|Source correlation|Useful for dSYM/source correlation when available.|
|`atos`|Address-to-symbol lookup|Verification|Requires correct load address and dSYM/symbol availability.|
|`codesign`|Inspect, verify, and create signatures|Required after mutation|Ad-hoc signing is for local tests; distribution requires proper identity/notarization path.|
|`install_name_tool`|Change dylib IDs and load paths|Load-command mutation|Changing load commands can alter signatures and runtime behavior.|
|`plutil`|Inspect/validate plists|Bundle triage|Use for `Info.plist`, entitlements plists, launch services data.|
|`security`|Certificates/keychains|Signing support|Useful when verifying identities; avoid exposing keychain-sensitive data.|
|`lldb`|Debugging|Runtime verification|Use only in authorized, isolated contexts.|
|`clang`/`swiftc`|Compile source or minimal repros|Source-level rebuilds|Prefer source rebuilds to binary patching when source is available.|
|`swift-demangle`|Swift symbol demangling|Verification|Useful for names from `nm`, Hopper, or snapshots.|

## LLVM Tools

|Tool|Primary use|Mutation role|Notes|
|-|-|-|-|
|`llvm-objdump`|Cross-platform disassembly and headers|Verification|Good fallback when Apple `otool` output is insufficient or unavailable.|
|`llvm-otool`|Mach-O `otool`-style output|Verification|Useful on hosts with LLVM packages.|
|`llvm-nm`|Symbols|Verification|Can supplement Apple `nm`.|
|`llvm-dwarfdump`|Debug info|Source correlation|Can supplement Apple `dwarfdump`.|
|`llvm-cxxfilt`|C++ demangling|Verification|Use with C++ symbols.|

## Hopper

|Component|Use|Notes|
|-|-|-|
|Hopper GUI|Interactive disassembly, pseudocode, annotations, binary modification UI|Use for focused inspection after CLI triage.|
|Hopper Python scripts|Batch snapshots and custom extraction|This skill provides bounded snapshot scripts.|
|Hopper MCP server|Live document queries and annotations over stdio JSON-RPC|Use `hopper_mcp_probe.py` for tool discovery and read calls.|

Suggested order:

1. `inspect_macho_targets.py` for app bundle and component inventory.
2. Apple/LLVM CLI tools for headers, slices, signatures, symbols, and deps.
3. `run_hopper_export.sh` for a bounded JSON snapshot.
4. `hopper_evidence_search.py` for repeatable evidence search.
5. Hopper GUI/MCP for narrow pseudocode, xrefs, or annotation work.

## Popular Third-Party Tools

|Tool|Primary use|Mutation role|Notes|
|-|-|-|-|
|Ghidra|Large-scale static analysis and decompilation|Patch planning/verification|Good cross-check against Hopper; startup and project setup are heavier.|
|radare2 / rizin|CLI binary analysis, disassembly, scripting, patching|Patch planning/verification|Powerful but command syntax is dense; record exact commands.|
|jtool2|Mach-O inspection, load commands, signatures, exports, binds|Verification|Useful when Apple tools disagree or omit detail.|
|ipsw|Mach-O helpers, Apple firmware/app analysis utilities|Verification|Useful for `macho` subcommands and arm64e-heavy work.|
|MachOView / MachOExplorer|Visual Mach-O structure|Verification|Good for load-command/section orientation.|
|class-dump derivatives|Objective-C runtime metadata|Orientation|Availability and compatibility vary; use metadata as orientation, not behavior proof.|
|Frida|Dynamic instrumentation|Runtime research|Use only for authorized targets in isolated environments.|

## Tool Choice Matrix

|Question|First tool|Next tool|Evidence to record|
|-|-|-|-|
|Which binary inside an `.app` should I inspect?|`inspect_macho_targets.py`|`file`, `otool -l`, Hopper snapshot|Bundle path, CFBundleExecutable, helpers/frameworks/XPCs.|
|Which slices exist?|`lipo -info` or `lipo -archs`|`macho_address_map.py`|Architectures, offsets, sizes, alignment.|
|What dylibs/frameworks are loaded?|`otool -L`|`dyld_info`, Hopper imports|Install names and weak/reexport status.|
|Where is this source string used?|`strings`, Hopper snapshot|`hopper_evidence_search.py`, MCP `search_strings`|String address, xref procedure, call path.|
|What does this address mean?|`macho_address_map.py`|`otool -l`, Hopper segment view|VA, segment/section, slice offset, fat offset.|
|Can this authorized patch be recombined?|`macho_universal_workspace.py`|`lipo -create`, `codesign`, `spctl` if appropriate|Slice plan, before/after hashes, signing result.|
|Did signing survive?|`codesign --verify --verbose`|`codesign -dv --verbose=4`, `spctl` for distribution workflows|Identity, entitlements, verification output.|

## Minimal Command Set

For a target executable:

```bash
file /path/to/target
lipo -info /path/to/target 2>/dev/null || true
otool -hv /path/to/target
otool -l /path/to/target | sed -n '1,220p'
otool -L /path/to/target 2>/dev/null || true
codesign -dv --verbose=4 /path/to/target 2>&1 || true
codesign --verify --verbose=4 /path/to/target 2>&1 || true
```

For a target app:

```bash
scripts/inspect_macho_targets.py --include-deps --output /tmp/target.inventory.md /path/to/Target.app
```

For Hopper evidence:

```bash
scripts/run_hopper_export.sh --summary-output /tmp/target.summary.md --output /tmp/target.snapshot.json /path/to/target
scripts/hopper_evidence_search.py --ignore-case /tmp/target.snapshot.json 'needle|0x1000'
```

## Reporting Discipline

Record tool versions and command outputs that materially affect conclusions. Do not say “the binary is signed” or “this offset is patched” without showing the command that established it.
