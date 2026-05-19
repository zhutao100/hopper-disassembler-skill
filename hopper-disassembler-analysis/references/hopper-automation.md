# Hopper Automation

Use this reference when the task needs command-line Hopper runs, MCP setup, or repeatable evidence capture.

## Contents

- [Quick Environment Checks](#quick-environment-checks)
- [Pre-Hopper Target Inventory](#pre-hopper-target-inventory)
- [Batch Snapshot Export](#batch-snapshot-export)
- [Repeated Analysis Reuse](#repeated-analysis-reuse)
- [Compact Snapshot Summaries](#compact-snapshot-summaries)
- [Snapshot Evidence Search](#snapshot-evidence-search)
- [Direct Hopper CLI](#direct-hopper-cli)
- [Focused Procedure Exports](#focused-procedure-exports)
- [AppleScript Automation](#applescript-automation)
- [Official Hopper MCP Server](#official-hopper-mcp-server)
- [Troubleshooting](#troubleshooting)

## Quick Environment Checks

```bash
command -v hopper || true
command -v HopperMCPServer || true
/usr/libexec/PlistBuddy -c 'Print :CFBundleShortVersionString' "/Applications/Hopper Disassembler.app/Contents/Info.plist"
scripts/hopper_mcp_probe.py --json --call-tool none
```

Expected paths on a standard macOS install:

- Hopper app: `/Applications/Hopper Disassembler.app`
- Hopper CLI launcher: `/Applications/Hopper Disassembler.app/Contents/MacOS/hopper` or a `hopper` symlink in `PATH`
- Bundled MCP binary: `/Applications/Hopper Disassembler.app/Contents/MacOS/HopperMCPServer`
- Optional MCP server symlink: `/usr/local/bin/HopperMCPServer`


## Pre-Hopper Target Inventory

Run target inventory before opening Hopper. This avoids wasting analysis time on the wrong Mach-O inside an app bundle.

```bash
scripts/inspect_macho_targets.py \
  --include-deps \
  --output /tmp/target.inventory.md \
  /path/to/Target.app
```

Use the inventory to choose the binary to pass to Hopper:

- Main executable for lifecycle and app-owned command handling.
- XPC service for privileged/helper IPC flows.
- App-owned framework when source symbols or strings live outside the main executable.
- Login item or nested helper app when state retention, menu-bar, updater, or background behavior is the question.

The script can also emit JSON for machine processing:

```bash
scripts/inspect_macho_targets.py --include-deps --format json /path/to/Target.app \
  >/tmp/target.inventory.json
```

## Batch Snapshot Export

Prefer the bundled wrapper for first-pass evidence because it sets safe caps, handles `.app` bundles, chooses a native ARM slice from universal Mach-O inputs, runs Hopper's Python exporter with Hopper's injected API globals intact, waits for the JSON artifact, and closes the throwaway Hopper document by default.

```bash
scripts/run_hopper_export.sh \
  --summary-output /tmp/target.hopper-summary.md \
  --output /tmp/target.hopper-snapshot.json \
  /path/to/Target.app
scripts/run_hopper_export.sh --output /tmp/tool.hopper-snapshot.json /path/to/tool
```

Useful options:

```bash
scripts/run_hopper_export.sh \
  --arch arm64 \
  --max-procedures 1000 \
  --max-strings 5000 \
  --max-string-xrefs 32 \
  --output /tmp/target.hopper-snapshot.json \
  /path/to/Target.app

scripts/run_hopper_export.sh \
  --arch arm64e \
  --max-procedures 1000 \
  --output /tmp/system-tool.arm64e.hopper-snapshot.json \
  /bin/echo

scripts/run_hopper_export.sh \
  --include-pseudocode \
  --max-pseudocode-chars 12000 \
  --procedure-pattern 'FunctionOrTypeName|0x100003f50' \
  --max-procedures 50 \
  --max-basic-blocks 32 \
  --max-instructions-per-block 16 \
  --output /tmp/target.pseudo.hopper-snapshot.json \
  /path/to/Target.app
```

Use `--include-pseudocode` only for focused exports. Hopper decompilation can be slow and pseudocode must be treated as a hypothesis. Keep `--max-pseudocode-chars` bounded; optimized Rust and Swift generics can produce megabytes of decompiler text for one source function.

Use `--keep-open` when the user wants the Hopper GUI left open for interactive inspection after the export. Use `--wait-for-analysis` only when the task needs a completed analysis database or snapshot; it can block on large targets.

Implementation notes for future maintenance:

- Hopper 6 presents some Apple system universal binaries as `AArch64e` in the FAT picker. The wrapper uses `-l FAT -s AArch64e -l Mach-O` for `arm64e` instead of relying on `--aarch64`.
- Hopper injects `Document`, `Segment`, and related API classes into the script's global namespace. Wrapper scripts that dispatch to another Python file must preserve `globals()`; running the exporter through `runpy.run_path()` loses those injected classes.
- The wrapper writes the generated dispatch script to the process temp directory and removes it after the export completes.
- String rows include bounded `xrefs_to` entries. Use `--max-string-xrefs 0` to suppress this when a target has many string references, or increase it when string-to-code correlation is the main task.
- Procedure rows include virtual addresses and file offsets for the entry point, sampled instructions, and call references when Hopper can map the address to a file offset. Procedure rows also report `basic_blocks_truncated`, each block reports `instructions_truncated`, and pseudocode rows report `pseudocode_length` plus `pseudocode_truncated`.
- Use `--procedure-pattern` after string/name triage to export only matching procedure addresses, names, demangled names, or signatures.
- For `--database`, the wrapper launches a small no-analysis bootstrap executable and has the Hopper Python exporter create a fresh document and call `loadDocumentAt(...)`, because Hopper's AppleScript `open database` command does not accept an `execute Python script` parameter. Override the bootstrap binary with `HOPPER_SKILL_DATABASE_BOOTSTRAP=/path/to/tiny-mach-o` only when `/bin/echo` is unavailable.

## Repeated Analysis Reuse

For large apps, decide reuse strategy before the first costly Hopper run:

1. Keep Hopper open when the next step is live GUI/MCP exploration in the same session.
2. Save a `.hop` database when follow-up passes may happen later or in another agent turn.
3. Reopen the `.hop` database for focused exports instead of reopening the original Mach-O.

Leave the active document open for MCP:

```bash
scripts/run_hopper_export.sh \
  --keep-open \
  --summary-output /tmp/target.hopper-summary.md \
  --output /tmp/target.hopper-snapshot.json \
  /path/to/target

scripts/hopper_mcp_probe.py --json --call-tool list_documents
scripts/hopper_mcp_probe.py --json --call-tool search_name --tool-args '{"pattern":"FunctionOrType"}'
```

Save and later reopen a Hopper database:

```bash
scripts/run_hopper_export.sh \
  --wait-for-analysis \
  --save-hop /tmp/target.hop \
  --summary-output /tmp/target.hopper-summary.md \
  --output /tmp/target.hopper-snapshot.json \
  /path/to/target

scripts/run_hopper_export.sh \
  --database /tmp/target.hop \
  --procedure-pattern 'FunctionOrType|0x100003f50' \
  --max-procedures 20 \
  --summary-output /tmp/target.focused-summary.md \
  --output /tmp/target.focused-snapshot.json
```

Rules:

- Store `.hop` databases in `/tmp` unless the user asks for a persistent artifact.
- Save after `--wait-for-analysis` when the cost being avoided is full background analysis.
- Skip `--wait-for-analysis` when a quick partial snapshot is enough; saved databases then contain the current partial analysis state.
- Reopened `.hop` exports save the database before closing by default to avoid Hopper's unsaved-modifications prompt.
- Do not pass `--arch` when reopening `.hop`; the database already encodes the selected slice.

## Compact Snapshot Summaries

Use the summary script when the raw JSON is too large for direct review:

```bash
scripts/hopper_snapshot_summary.py \
  --filter 'FunctionOrTypeName|UniqueString|0x100003f50' \
  --max-procedures 8 \
  --max-strings 20 \
  --max-names 20 \
  --output /tmp/target.hopper-summary.md \
  /tmp/target.hopper-snapshot.json
```

The wrapper can generate this summary after export:

```bash
scripts/run_hopper_export.sh \
  --summary-output /tmp/target.hopper-summary.md \
  --summary-filter 'FunctionOrTypeName|UniqueString|0x100003f50' \
  --output /tmp/target.hopper-snapshot.json \
  /path/to/target
```

Summary filters match procedure identities, names, strings, signatures, addresses, and string-xref procedure text. A string can appear in the summary because one of its xrefs lands in the matched procedure; re-check the string value before treating it as a literal match.


## Snapshot Evidence Search

Use this after exporting a snapshot when the raw JSON is too large or when an agent needs a narrow evidence surface.

```bash
scripts/hopper_evidence_search.py \
  --ignore-case \
  --output /tmp/target.evidence.md \
  /tmp/target.hopper-snapshot.json \
  'FunctionOrTypeName|UniqueString|0x100003f50'
```

Multiple patterns are ANDed, so use one broad alternation for alternatives and separate patterns for required co-occurrence:

```bash
scripts/hopper_evidence_search.py /tmp/target.hopper-snapshot.json 'SettingsController' 'FeatureState'
```

For downstream tools, request JSON:

```bash
scripts/hopper_evidence_search.py --format json /tmp/target.hopper-snapshot.json 'URLSession|SecItem'
```

## Direct Hopper CLI

Hopper's launcher accepts loader chains and script execution:

```bash
hopper -l Mach-O -e /path/to/binary -Y /path/to/script.py
hopper -l FAT --aarch64 -l Mach-O -e /path/to/universal-binary -Y /path/to/script.py
hopper -l FAT -s AArch64e -l Mach-O -e /path/to/arm64e-universal-binary -Y /path/to/script.py
```

Important flags:

- `-e` / `--executable`: create a new Hopper document for a binary.
- `-d` / `--database`: open an existing `.hop` database. For scripted exports from `.hop`, prefer `scripts/run_hopper_export.sh --database`; Hopper's AppleScript `open database` path does not accept `execute Python script`.
- `-Y` / `--python`: execute a Python script after initial analysis.
- `-y` / `--python-command`: execute a Python command after initial analysis.
- `-a`, `-o`, `-f`, `-z`: enable analysis, Objective-C metadata, Swift metadata, and exception metadata.
- `-l FAT --aarch64 -l Mach-O`: select the ARM64 Mach-O slice from a universal binary.
- `-l FAT -s AArch64e -l Mach-O`: select the ARM64e Mach-O slice when the FAT loader names it `AArch64e`.

## Focused Procedure Exports

Use a two-pass workflow for large Swift, Rust, or C++ binaries:

1. Export names and strings with broad caps and no pseudocode.
2. Search the snapshot for source identifiers, demangled names, selectors, or unique strings.
3. Rerun with `--procedure-pattern` and tighter basic-block/instruction caps.

```bash
scripts/run_hopper_export.sh \
  --procedure-pattern 'ConfigureContextMenu|rgx::run|0x100000978' \
  --max-procedures 20 \
  --max-basic-blocks 24 \
  --max-instructions-per-block 12 \
  --max-call-refs 32 \
  --output /tmp/target.focused.hopper-snapshot.json \
  /path/to/target
```

Add `--include-pseudocode --max-pseudocode-functions 5` only when the matched function set is small. For large optimized functions, prefer assembly/basic blocks, callers/callees, and string xrefs over decompiler output.

## AppleScript Automation

Use AppleScript when a workflow needs Hopper's scripting dictionary directly. Prefer `scripts/run_hopper_export.sh` for batch exports because AppleScript can return before an artifact exists and universal binaries can still surface loader option dialogs.

```bash
osascript <<'APPLESCRIPT'
tell application "Hopper Disassembler"
  open executable POSIX file "/path/to/Target" analysis true parse objectivec true parse swift true parse exceptions true
end tell
APPLESCRIPT
```

With a Python script:

```bash
osascript <<'APPLESCRIPT'
tell application "Hopper Disassembler"
  open executable POSIX file "/path/to/Target" analysis true execute Python script POSIX file "/path/to/hopper_export_snapshot.py"
end tell
APPLESCRIPT
```

If macOS prompts for Automation permission, grant it for the terminal or agent host process that launched `osascript` or `hopper`.

The Hopper CLI launcher drives the Hopper app through AppleEvents. In unattended VMs or CI, seed or grant Automation permission for the launcher client to control Hopper's bundle identifier before running batch exports. Without that grant, the launcher can fail with an AppleEvents authorization error before the Python exporter runs.

## Official Hopper MCP Server

Hopper 6 exposes a stdio JSON-lines MCP server. Probe it before relying on it:

```bash
scripts/hopper_mcp_probe.py
scripts/hopper_mcp_probe.py --json --call-tool list_documents
scripts/hopper_mcp_probe.py --json --call-tool search_strings --tool-args '{"pattern":"settings|feature"}'
scripts/hopper_mcp_probe.py --json --call-tool procedure_assembly --tool-args '{"procedure":"0x100003f50"}'
scripts/hopper_mcp_probe.py --json --include-tool-schemas --call-tool none
```

If `/usr/local/bin/HopperMCPServer` is not installed, point the probe at the bundled binary:

```bash
scripts/hopper_mcp_probe.py \
  --server "/Applications/Hopper Disassembler.app/Contents/MacOS/HopperMCPServer" \
  --json \
  --call-tool none
```

Install it for Codex CLI:

```bash
scripts/install_codex_hopper_mcp.sh --replace
```

Generic MCP clients can use `assets/generic-mcp-hopper-direct.json` for the bundled server path or `assets/generic-mcp-hopper.json` for a symlink path. Codex TOML users can merge `assets/codex-mcp-hopper-direct.toml` or `assets/codex-mcp-hopper.toml` into their MCP config.

Observed official tool surface:

- Document state: `list_documents`, `current_document`, `set_current_document`
- Structure: `list_segments`, `list_procedures`, `list_procedure_size`, `list_procedure_info`
- Search: `list_strings`, `search_strings`, `search_procedures`, `list_names`, `search_name`
- Procedure detail: `procedure_info`, `procedure_address`, `procedure_assembly`, `procedure_pseudo_code`, `procedure_callers`, `procedure_callees`
- Navigation and xrefs: `current_address`, `current_procedure`, `goto_address`, `xrefs`, `next_address`, `prev_address`
- Annotations: `comment`, `inline_comment`, `set_comment`, `set_inline_comment`, `address_name`, `set_address_name`, `set_addresses_names`, `list_bookmarks`, `set_bookmark`, `unset_bookmark`

Use read tools freely. Use write/navigation tools only when the user explicitly asks for live Hopper document edits and you can describe exactly what will change.

Tool argument gotchas:

- Procedure tools take `{"procedure":"name-or-0xaddress"}`. Passing `{"address":"0x..."}` is ignored by official procedure tools and can accidentally query the current procedure.
- `xrefs` and `goto_address` take `{"address":"0x..."}`.
- `search_strings`, `search_procedures`, and `search_name` take a regular-expression `pattern` plus optional `case_sensitive`.
- `hopper_mcp_probe.py` blocks navigation/write tools unless `--allow-state-change` is supplied.

## Troubleshooting

- **No export file:** check the wrapper log path printed by `run_hopper_export.sh`; increase `--timeout`.
- **FAT archive picker appears:** rerun with `--arch arm64e`, `--arch arm64`, or `--arch x86_64` based on `file /path/to/binary`. Hopper's picker may show `AArch64e` for Apple system binaries.
- **Empty export with an exporter error log:** inspect `<snapshot>.error.log`; a custom wrapper may have lost Hopper's injected `Document` global.
- **MCP server path with spaces:** use the direct-path JSON/TOML assets first; if a client mishandles spaces, create a symlink such as `/usr/local/bin/HopperMCPServer` and use the symlink assets.
- **Automation prompt blocked the run:** open System Settings and allow the terminal, agent host process, or Hopper CLI launcher to automate Hopper. In disposable VM workflows, bake that grant into the automation snapshot.
- **Stale documents in Hopper:** close them manually or rerun the wrapper without `--keep-open`.
