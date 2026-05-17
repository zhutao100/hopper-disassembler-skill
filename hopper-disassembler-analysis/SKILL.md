---
name: hopper-disassembler-analysis
description: Use Hopper Disassembler on macOS to inspect binaries, app bundles, Mach-O files, Hopper databases, procedures, call graphs, strings, xrefs, pseudocode, and live Hopper MCP sessions. Trigger when the user asks for reverse engineering, static binary analysis, macOS app binary inspection, Hopper automation, Hopper Python scripting, Hopper MCP setup, or evidence-backed reports from local executables.
---

# Hopper Disassembler Analysis

Use Hopper as the evidence source for local binary analysis. Prefer reproducible exports first, then focused MCP or GUI inspection for questions that need live navigation, pseudocode, annotations, or current cursor state.

## Workflow

1. Verify the target and scope.
   - For `.app` bundles, resolve `Contents/MacOS/<CFBundleExecutable>`.
   - For universal Mach-O binaries, prefer ARM64 on Apple Silicon unless the user asks for another slice.
   - Keep installed apps, source trees, and fixtures read-only. Copy to `/tmp` before byte changes or produced executables.

2. Capture a bounded Hopper snapshot.

   ```bash
   scripts/run_hopper_export.sh --output /tmp/target.hopper-snapshot.json /path/to/Target.app
   ```

   Use focused options when needed:

   ```bash
   scripts/run_hopper_export.sh \
     --arch arm64 \
     --max-procedures 1000 \
     --max-strings 5000 \
     --output /tmp/target.arm64.hopper-snapshot.json \
     /path/to/Target.app
   ```

   Add `--include-pseudocode --max-procedures 50` only for focused decompiler review.

3. Inspect the exported JSON before making claims.
   - Start with `document`, `counts`, `truncated`, `segments`, `names`, and `strings`.
   - Triage procedures by address, name, signature, callers, callees, basic blocks, sampled instructions, comments, and tags.
   - If `document.background_analysis_active` or any `truncated` flag is true, disclose the limit and rerun with higher caps when the missing evidence matters.

4. Use Hopper MCP for live document queries.

   ```bash
   scripts/hopper_mcp_probe.py --json --call-tool list_documents
   scripts/install_codex_hopper_mcp.sh --replace
   ```

   Use MCP read tools for live documents (`list_procedures`, `procedure_info`, `procedure_assembly`, `procedure_pseudo_code`, `xrefs`, `search_strings`). Use write/navigation tools only when the user explicitly asks for live Hopper document edits.

5. Corroborate with local evidence.
   - Combine Hopper addresses, strings, xrefs, imports, and sampled assembly.
   - If source is available, map Hopper names/selectors/strings back to source files.
   - Treat pseudocode as a hypothesis until assembly, xrefs, strings, imports, or source support it.

6. Report with reproducibility.
   - Use `assets/hopper-analysis-report-template.md` for larger reports.
   - Cite concrete addresses, names, strings, xrefs, source paths, and exact export commands.
   - State caps, timeouts, architecture slice, Hopper version, and any unresolved evidence gaps.

## Scripts

- `scripts/run_hopper_export.sh`: Open a binary or `.app` in Hopper, run the bundled exporter, wait for JSON, and close the throwaway document by default.
- `scripts/hopper_export_snapshot.py`: Hopper Python script used by the wrapper. It exports document metadata, segments, sections, strings, names, procedures, call refs, basic blocks, and sampled instructions.
- `scripts/hopper_mcp_probe.py`: Probe Hopper's bundled JSON-lines MCP server and list tools.
- `scripts/install_codex_hopper_mcp.sh`: Register Hopper MCP with Codex CLI after probing the server.

## Assets

- `assets/codex-mcp-hopper.toml`: Codex MCP config snippet.
- `assets/generic-mcp-hopper.json`: Generic MCP client config snippet.
- `assets/hopper-analysis-report-template.md`: Evidence report template.
- `assets/hopper-annotation-payload-template.json`: Conservative annotation payload template.

## References

Load only the reference needed for the current task:

- `references/hopper-automation.md`: CLI launcher, AppleScript, MCP setup, tool surface, troubleshooting.
- `references/hopper-python-api.md`: Public Hopper Python API patterns for custom scripts, xrefs, annotations, and pseudocode discipline.
- `references/macos-binary-workflow.md`: macOS app bundle analysis, source correlation, triage, and modification boundaries.
