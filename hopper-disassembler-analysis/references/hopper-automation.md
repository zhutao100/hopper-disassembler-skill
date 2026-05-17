# Hopper Automation

Use this reference when the task needs command-line Hopper runs, MCP setup, or repeatable evidence capture.

## Quick Environment Checks

```bash
command -v hopper
command -v HopperMCPServer
/usr/libexec/PlistBuddy -c 'Print :CFBundleShortVersionString' "/Applications/Hopper Disassembler.app/Contents/Info.plist"
scripts/hopper_mcp_probe.py --json --call-tool none
```

Expected local paths on a standard install:

- Hopper app: `/Applications/Hopper Disassembler.app`
- Hopper CLI launcher: `/usr/local/bin/hopper`
- MCP server symlink: `/usr/local/bin/HopperMCPServer`
- Bundled MCP binary: `/Applications/Hopper Disassembler.app/Contents/MacOS/HopperMCPServer`

## Batch Snapshot Export

Prefer the bundled wrapper for first-pass evidence because it sets safe caps, handles `.app` bundles, chooses the ARM64 slice from universal Mach-O inputs, runs Hopper's Python exporter, waits for the JSON artifact, and closes the throwaway Hopper document by default.

```bash
scripts/run_hopper_export.sh --output /tmp/target.hopper-snapshot.json /path/to/Target.app
scripts/run_hopper_export.sh --output /tmp/tool.hopper-snapshot.json /path/to/tool
```

Useful options:

```bash
scripts/run_hopper_export.sh \
  --arch arm64 \
  --max-procedures 1000 \
  --max-strings 5000 \
  --output /tmp/target.hopper-snapshot.json \
  /path/to/Target.app

scripts/run_hopper_export.sh \
  --include-pseudocode \
  --max-procedures 50 \
  --output /tmp/target.pseudo.hopper-snapshot.json \
  /path/to/Target.app
```

Use `--include-pseudocode` only for focused exports. Hopper decompilation can be slow and pseudocode must be treated as a hypothesis.

Use `--keep-open` when the user wants the Hopper GUI left open for interactive inspection after the export.

## Direct Hopper CLI

Hopper's launcher accepts loader chains and script execution:

```bash
hopper -l Mach-O -e /path/to/binary -Y /path/to/script.py
hopper -l FAT --aarch64 -l Mach-O -e /path/to/universal-binary -Y /path/to/script.py
```

Important flags:

- `-e` / `--executable`: create a new Hopper document for a binary.
- `-d` / `--database`: open an existing `.hop` database.
- `-Y` / `--python`: execute a Python script after initial analysis.
- `-y` / `--python-command`: execute a Python command after initial analysis.
- `-a`, `-o`, `-f`, `-z`: enable analysis, Objective-C metadata, Swift metadata, and exception metadata.
- `-l FAT --aarch64 -l Mach-O`: select the ARM64 Mach-O slice from a universal binary.

## AppleScript Automation

Use AppleScript when a workflow needs Hopper's scripting dictionary directly.

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

## Official Hopper MCP Server

Hopper 6 exposes a stdio JSON-lines MCP server. Probe it before relying on it:

```bash
scripts/hopper_mcp_probe.py
scripts/hopper_mcp_probe.py --json --call-tool list_documents
```

Install it for Codex CLI:

```bash
scripts/install_codex_hopper_mcp.sh --replace
```

Generic MCP clients can use `assets/generic-mcp-hopper.json`. Codex TOML users can merge `assets/codex-mcp-hopper.toml` into `~/.codex/config.toml`.

Observed official tool surface:

- Document state: `list_documents`, `current_document`, `set_current_document`
- Structure: `list_segments`, `list_procedures`, `list_procedure_size`, `list_procedure_info`
- Search: `list_strings`, `search_strings`, `search_procedures`, `list_names`, `search_name`
- Procedure detail: `procedure_info`, `procedure_address`, `procedure_assembly`, `procedure_pseudo_code`, `procedure_callers`, `procedure_callees`
- Navigation and xrefs: `current_address`, `current_procedure`, `goto_address`, `xrefs`, `next_address`, `prev_address`
- Annotations: `comment`, `inline_comment`, `set_comment`, `set_inline_comment`, `address_name`, `set_address_name`, `set_addresses_names`, `list_bookmarks`, `set_bookmark`, `unset_bookmark`

Use read tools freely. Use write/navigation tools only when the user explicitly asks for live Hopper document edits and you can describe exactly what will change.

## Troubleshooting

- **No export file:** check the wrapper log path printed by `run_hopper_export.sh`; increase `--timeout`.
- **Architecture picker or empty export:** rerun with `--arch arm64` or `--arch x86_64` for universal Mach-O binaries.
- **MCP server path with spaces:** use `/usr/local/bin/HopperMCPServer` or the generic JSON asset that points to the symlink.
- **Automation prompt blocked the run:** open System Settings and allow the terminal or agent host to automate Hopper.
- **Stale documents in Hopper:** close them manually or rerun the wrapper without `--keep-open`.
