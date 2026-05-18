---
name: hopper-disassembler-analysis
description: Use Hopper Disassembler on macOS to inspect binaries, app bundles, Mach-O files, universal slices, Hopper databases, procedures, call graphs, strings, xrefs, pseudocode, annotations, source-to-binary correlation, and live Hopper MCP sessions. Trigger when the user asks for reverse engineering, static binary analysis, macOS app binary inspection, Hopper automation, Hopper Python scripting, Hopper MCP setup, source-backed binary analysis, or evidence-backed reports from local executables.
---

# Hopper Disassembler Analysis

Use Hopper as the evidence source for local binary analysis. Prefer bounded, reproducible JSON snapshots first; use live MCP or GUI navigation only for focused questions that need the current Hopper document, pseudocode, annotations, or cursor state.

## Operating Rules

- Keep installed apps, source checkouts, and fixtures read-only.
- Copy targets to `/tmp` before byte changes, produced executables, or write-back annotation experiments.
- Use the host Hopper installation for read-only disassembly when Hopper is licensed only on the host.
- Use a disposable VM/sandbox before running modified binaries or generated executables.
- Treat Hopper pseudocode as a hypothesis until assembly, xrefs, imports, strings, or source corroborate it.
- When source is available, analyze one narrow source snippet at a time and require at least two Hopper signals before mapping source behavior to binary behavior.

## Quick Workflow

1. Check the environment.

   ```bash
   command -v hopper
   command -v HopperMCPServer || true
   /usr/libexec/PlistBuddy -c 'Print :CFBundleShortVersionString' \
     "/Applications/Hopper Disassembler.app/Contents/Info.plist"
   scripts/hopper_mcp_probe.py --json --call-tool none
   ```

   If the `HopperMCPServer` symlink is not installed, pass `--server "/Applications/Hopper Disassembler.app/Contents/MacOS/HopperMCPServer"` to probe the bundled server directly.

2. Resolve the target.

   For `.app` bundles, analyze the main executable first:

   ```bash
   app="/Applications/Target.app"
   exe="$(/usr/libexec/PlistBuddy -c 'Print :CFBundleExecutable' "$app/Contents/Info.plist")"
   target="$app/Contents/MacOS/$exe"
   file "$target"
   ```

   For universal Mach-O files, prefer the native ARM slice on Apple Silicon. Hopper 6 may expose modern system tools as `arm64e`; the wrapper handles that automatically, and `--arch arm64e` is available when explicit selection is needed.

   If the source snippet lives in an embedded framework, helper app, XPC service, or plugin, analyze that Mach-O instead of forcing all evidence through the main executable.

3. Capture a bounded snapshot.

   ```bash
   scripts/run_hopper_export.sh \
     --output /tmp/target.hopper-snapshot.json \
     /path/to/Target.app
   ```

   Add a compact Markdown companion when an agent needs to ingest the result directly:

   ```bash
   scripts/run_hopper_export.sh \
     --summary-output /tmp/target.hopper-summary.md \
     --summary-filter 'SourceType|UniqueString|0x100003f50' \
     --output /tmp/target.hopper-snapshot.json \
     /path/to/Target.app
   ```

   Focus the export when the binary is large:

   ```bash
   scripts/run_hopper_export.sh \
     --arch arm64 \
     --max-procedures 1000 \
     --max-strings 5000 \
     --max-names 8000 \
     --output /tmp/target.arm64.hopper-snapshot.json \
     /path/to/target
   ```

   Include pseudocode only for a small function set:

   ```bash
   scripts/run_hopper_export.sh \
     --include-pseudocode \
     --max-pseudocode-chars 12000 \
     --procedure-pattern 'FunctionOrTypeName|0x100003f50' \
     --max-procedures 20 \
     --max-basic-blocks 32 \
     --output /tmp/target.focused-pseudo.hopper-snapshot.json \
     /path/to/target
   ```

4. Read the snapshot before making claims.

   ```bash
   python3 - <<'PY' /tmp/target.hopper-snapshot.json
   import json, sys
   data = json.load(open(sys.argv[1], encoding="utf-8"))
   print(data["document"])
   print(data["counts"])
   print(data["truncated"])
   for proc in data["procedures"][:10]:
       print(proc["address"], proc["name"], proc["signature"])
   PY
   ```

   Inspect `document`, `counts`, `truncated`, `segments`, `names`, `strings`, and `procedures`. If `document.background_analysis_active` or a `truncated` flag matters to the question, rerun with higher caps or a narrower target. For a bounded review surface, summarize an existing snapshot:

   ```bash
   scripts/hopper_snapshot_summary.py \
     --filter 'FunctionOrTypeName|UniqueString|0x100003f50' \
     --output /tmp/target.hopper-summary.md \
     /tmp/target.hopper-snapshot.json
   ```

5. Corroborate with source and platform metadata.

   ```bash
   codesign -dv --verbose=4 "$target" 2>&1
   otool -L "$target"
   strings -a "$target" | grep -E "http|keychain|token|license|login|xpc|socket" | head
   grep -R --line-number "StringOrSymbolFromHopper" /path/to/source
   ```

   With source available, pick a small snippet and verify it through at least two Hopper signals: a demangled name or selector, a string plus xrefs, callee/import evidence, basic-block/branch structure, or focused pseudocode. Load language-specific gotchas on demand:

   - Swift or SwiftUI/AppKit target: `references/source-correlation-swift.md`
   - Rust target: `references/source-correlation-rust.md`

6. Use Hopper MCP for live document queries.

   ```bash
   scripts/hopper_mcp_probe.py --json --call-tool list_documents
   scripts/hopper_mcp_probe.py --json --call-tool search_name --tool-args '{"pattern":"parseBytes"}'
   scripts/hopper_mcp_probe.py --json --call-tool procedure_info --tool-args '{"procedure":"0x100003f50"}'
   scripts/install_codex_hopper_mcp.sh --replace
   ```

   Prefer read tools such as `list_procedures`, `procedure_info`, `procedure_assembly`, `procedure_pseudo_code`, `xrefs`, and `search_strings`. Official procedure tools use the `procedure` argument for either a name or address; `xrefs` uses `address`. Use write/navigation tools only when the user explicitly asks for live Hopper document edits.

7. Report with reproducibility.

   Use `assets/hopper-analysis-report-template.md` for larger reports. Include exact export commands, Hopper version, architecture slice, caps, timeout, snapshot path, addresses, names, strings, xrefs, and unresolved evidence gaps.

## Bundled Scripts

- `scripts/install_codex_skill.sh`: Copy this skill folder into a Codex CLI skills directory.
- `scripts/run_hopper_export.sh`: Open a binary or `.app` in Hopper, run the bundled exporter, optionally write an LLM-oriented Markdown summary, wait for JSON, and close the throwaway Hopper document by default.
- `scripts/hopper_export_snapshot.py`: Hopper Python script used by the wrapper. It exports metadata, segments, sections, strings with bounded xrefs, names, procedures, call refs, basic blocks, sampled instructions, comments, tags, file offsets, and bounded optional pseudocode.
- `scripts/hopper_snapshot_summary.py`: Summarize a snapshot as compact Markdown or compact JSON, with optional regex filtering across procedure, name, string, and xref text.
- `scripts/hopper_mcp_probe.py`: Probe Hopper's JSON-lines MCP server, list tools, inspect schemas, and call read tools with JSON arguments.
- `scripts/install_codex_hopper_mcp.sh`: Register Hopper MCP with Codex CLI after probing the server.

## Bundled Assets

- `assets/codex-mcp-hopper.toml`: Codex MCP config snippet.
- `assets/generic-mcp-hopper.json`: Generic MCP client config snippet.
- `assets/hopper-analysis-report-template.md`: Evidence report template.
- `assets/hopper-annotation-payload-template.json`: Conservative annotation payload template.

## References

Load only the reference needed for the current task:

- `references/hopper-automation.md`: Hopper CLI launcher, universal-slice selection, MCP setup, tool surface, and troubleshooting.
- `references/hopper-python-api.md`: Hopper Python API patterns, custom script templates, xrefs, annotations, and pseudocode discipline.
- `references/macos-binary-workflow.md`: macOS app bundle analysis, source correlation, Swift gotchas, triage, and modification boundaries.
- `references/source-correlation-swift.md`: Swift/AppKit/SwiftUI source-to-binary correlation workflow and gotchas.
- `references/source-correlation-rust.md`: Rust source-to-binary correlation workflow and gotchas.
