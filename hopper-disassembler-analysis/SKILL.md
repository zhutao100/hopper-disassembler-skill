---
name: hopper-disassembler-analysis
description: Use Hopper Disassembler on macOS for authorized local binary analysis, static Mach-O analysis, arm64/arm64e/x86_64 assembly inspection, universal-binary slice workflows, Hopper Python snapshots, Hopper MCP queries, source correlation, and evidence-backed reports. Trigger for Hopper automation, macOS binary triage, app-bundle target selection, address/file-offset mapping, or authorized mutation planning.
---

# Hopper Disassembler Analysis

Use Hopper as an evidence source for authorized local binary analysis. Prefer deterministic command-line triage and bounded Hopper snapshots before live UI/MCP work. Use live MCP or GUI navigation only for focused questions that need the active Hopper document, pseudocode, annotations, or cursor state.

## Operating Rules

- Keep installed apps, source checkouts, and fixtures read-only.
- Write generated snapshots, summaries, workspaces, and rebuilt test binaries to `/tmp` unless the task requests persistent artifacts.
- Copy targets into a throwaway workspace before annotation write-back, byte changes, load-command edits, produced executables, or patch validation.
- For long-running or repeated analysis, avoid reopening the same binary from scratch: keep the Hopper document open for MCP follow-up, or save a reusable `.hop` database under `/tmp` and reopen it later.
- Use a disposable VM/sandbox before running modified binaries or generated executables.
- Treat Hopper pseudocode as a hypothesis until assembly, xrefs, imports, strings, names, or source corroborate it.
- When source is available, analyze one narrow snippet at a time and require at least two Hopper signals before mapping source behavior to binary behavior.

## Quick Workflow

1. Check the host and toolchain.

   ```bash
   scripts/macos_toolchain_inventory.py --output /tmp/macos-toolchain.md
   command -v hopper || true
   command -v HopperMCPServer || true
   /usr/libexec/PlistBuddy -c 'Print :CFBundleShortVersionString' \
     "/Applications/Hopper Disassembler.app/Contents/Info.plist" 2>/dev/null || true
   scripts/hopper_mcp_probe.py --json --call-tool none
   ```

2. Inventory the target before opening Hopper.

   ```bash
   scripts/inspect_macho_targets.py \
     --include-deps \
     --output /tmp/target.inventory.md \
     /path/to/Target.app
   ```

   For `.app` bundles, analyze the main executable first, then helpers, embedded frameworks, XPC services, login items, and plugins when evidence points there. If a source snippet lives in an embedded component, analyze that Mach-O instead of forcing all evidence through the main executable.

3. Capture a bounded Hopper snapshot.

   ```bash
   scripts/run_hopper_export.sh \
     --summary-output /tmp/target.hopper-summary.md \
     --output /tmp/target.hopper-snapshot.json \
     /path/to/Target.app
   ```

   Focus large binaries with caps and architecture selection:

   ```bash
   scripts/run_hopper_export.sh \
     --arch arm64 \
     --max-procedures 1000 \
     --max-strings 5000 \
     --max-names 8000 \
     --summary-output /tmp/target.arm64.hopper-summary.md \
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
     --summary-output /tmp/target.focused-pseudo.md \
     --output /tmp/target.focused-pseudo.json \
     /path/to/target
   ```

   For costly targets that will need repeated passes, choose a reuse mode before the first Hopper run:

   ```bash
   # Leave the analyzed document open for live Hopper MCP queries.
   scripts/run_hopper_export.sh \
     --keep-open \
     --summary-output /tmp/target.hopper-summary.md \
     --output /tmp/target.hopper-snapshot.json \
     /path/to/target

   # Or save the Hopper database and reopen it on later passes.
   scripts/run_hopper_export.sh \
     --wait-for-analysis \
     --save-hop /tmp/target.hop \
     --summary-output /tmp/target.hopper-summary.md \
     --output /tmp/target.hopper-snapshot.json \
     /path/to/target
   scripts/run_hopper_export.sh \
     --database /tmp/target.hop \
     --output /tmp/target.reuse.hopper-snapshot.json
   ```

   `--database` only accepts Hopper `.hop` databases. Snapshot JSON files are evidence artifacts, not databases; pass the original binary/app again or create a `.hop` with `--save-hop`.

4. Search evidence before making claims.

   ```bash
   scripts/hopper_evidence_search.py \
     --ignore-case \
     --output /tmp/target.evidence.md \
     /tmp/target.hopper-snapshot.json \
     'FunctionOrTypeName|UniqueString|0x100003f50'
   ```

   Also inspect `document`, `counts`, `truncated`, `segments`, `names`, `strings`, and `procedures`. If `document.background_analysis_active` or a `truncated` flag matters to the question, rerun with higher caps or a narrower pattern.

5. Map addresses and offsets when assembly or byte-level reasoning matters.

   ```bash
   scripts/macho_address_map.py \
     --arch arm64 \
     --queries-only \
     --address 0x100003f50 \
     --offset 0x3f50 \
     /path/to/target
   ```

   For universal files, keep three coordinates distinct: Hopper virtual address, slice-relative file offset, and absolute fat-file offset.

   For a small symbol or address range in a large binary, prefer focused LLDB disassembly before broad `objdump` output:

   ```bash
   scripts/macho_lldb_disassemble.py \
     --arch arm64 \
     --address 0x100003f50 \
     --size 0x180 \
     /path/to/target
   ```

6. Use Hopper MCP for live document queries.

   ```bash
   scripts/hopper_mcp_probe.py --json --call-tool list_documents
   scripts/hopper_mcp_probe.py --json --call-tool search_name --tool-args '{"pattern":"parseBytes"}'
   scripts/hopper_mcp_probe.py --json --call-tool procedure_info --tool-args '{"procedure":"0x100003f50"}'
   scripts/install_codex_hopper_mcp.sh --replace
   ```

   Prefer read tools such as `list_procedures`, `procedure_info`, `procedure_assembly`, `procedure_pseudo_code`, `xrefs`, `search_strings`, and `search_name`. Use write/navigation tools only when the user explicitly asks for live Hopper document edits.

7. Plan authorized universal Mach-O mutation in a copy-only workspace.

   ```bash
   scripts/macho_universal_workspace.py \
     --sign-ad-hoc \
     --output-dir /tmp/target.macho-workspace \
     /path/to/Target.app
   ```

   Copy target slices into `patched/`, make those copies writable, run the generated `recombine.sh`, and install only into a disposable app copy:

   ```bash
   APP_COPY_PATH=/tmp/Target.app /tmp/target.macho-workspace/install_rebuilt_into_app.sh
   ```

   For local ad-hoc app signatures, use local test entitlements only; do not preserve production team, application-identifier, iCloud, or push entitlements. Use `assets/authorized-mutation-checklist.md` and `assets/macho-slice-plan-template.json` for change review.

8. Report with reproducibility.

   Use `assets/hopper-analysis-report-template.md` for larger reports. Include exact commands, Hopper version, architecture slice, export caps, timeout, snapshot path, addresses, names, strings, xrefs, file-offset calculations, and unresolved evidence gaps.

## Bundled Scripts

- `scripts/macos_toolchain_inventory.py`: Inventory built-in and popular macOS binary-analysis/mutation tools.
- `scripts/inspect_macho_targets.py`: Inventory app-bundle and Mach-O analysis targets before Hopper runs.
- `scripts/macho_address_map.py`: Parse thin/universal Mach-O files and map virtual addresses to slice-relative and absolute file offsets; use `--queries-only` for compact LLM-facing output.
- `scripts/macho_lldb_disassemble.py`: Run bounded LLDB batch disassembly for focused symbols or address ranges without dumping a whole large binary.
- `scripts/macho_universal_workspace.py`: Create a copy-only universal-slice workspace with compact plan metadata, full metadata files, generated recombine script, and app-copy install helper.
- `scripts/run_hopper_export.sh`: Open a binary, `.app`, or existing `.hop` database in Hopper; run the bundled exporter; optionally write a compact Markdown summary; optionally save a `.hop`; and close the throwaway Hopper document by default.
- `scripts/hopper_export_snapshot.py`: Hopper Python script that optionally waits for analysis and saves the active database, then exports metadata, segments, sections, strings with bounded xrefs, names, procedures, call refs, basic blocks, sampled instructions, comments, tags, file offsets, and bounded optional pseudocode.
- `scripts/hopper_snapshot_summary.py`: Summarize a snapshot as compact Markdown or compact JSON, with optional regex filtering.
- `scripts/hopper_evidence_search.py`: Search existing snapshots for procedures, strings, names, xrefs, and comments without reopening Hopper.
- `scripts/hopper_mcp_probe.py`: Probe Hopper's JSON-lines MCP server, list tools, inspect schemas, and call read tools with JSON arguments.
- `scripts/install_codex_skill.sh`, `scripts/install_hopper_scripts.sh`, `scripts/install_codex_hopper_mcp.sh`: Install the skill, Hopper UI script, and Codex MCP configuration.
- `scripts/validate_skill_repo.py`: Validate this repo layout, frontmatter, script executability, asset syntax, and orphaned bundled resources without external dependencies.

## Bundled Assets

- `assets/hopper-analysis-report-template.md`: Evidence report template.
- `assets/authorized-mutation-checklist.md`: Review checklist for authorized changes.
- `assets/macho-slice-plan-template.json`: Structured universal-slice mutation plan.
- `assets/toolchain-inventory-template.json`: Toolchain baseline groups.
- `assets/hopper-annotation-payload-template.json`, `assets/hopper-evidence-query-template.json`, `assets/hopper-target-inventory-template.json`: Reusable payload/query/inventory templates.
- `assets/codex-mcp-hopper*.toml` and `assets/generic-mcp-hopper*.json`: MCP config snippets.

## References

Load only the reference needed for the current task:

- `references/macos-arm64-assembly.md`: macOS arm64/arm64e assembly analysis, ABI, branch/return patterns, and PAC cautions.
- `references/macos-toolchains.md`: Built-in and popular macOS analysis/mutation toolchains and when to use each.
- `references/universal-mach-o-modification.md`: Authorized universal Mach-O slice extraction, offset mapping, recombine, and signing workflow.
- `references/mach-o-addressing.md`: Mach-O address spaces, load commands, file offsets, and script usage.
- `references/hopper-automation.md`: Hopper CLI launcher, universal-slice selection, MCP setup, tool surface, and troubleshooting.
- `references/hopper-python-api.md`: Hopper Python API patterns, custom script templates, xrefs, annotations, and pseudocode discipline.
- `references/macos-binary-workflow.md`: macOS app-bundle analysis, source correlation, triage, and modification boundaries.
- `references/source-correlation-swift.md`: Swift/AppKit/SwiftUI source-to-binary correlation workflow and gotchas.
- `references/source-correlation-rust.md`: Rust source-to-binary correlation workflow and gotchas.
