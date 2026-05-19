# Agent Development Notes

This repository contains one installable skill: `hopper-disassembler-analysis`.

Use the toolchain inventory → target inventory → bounded snapshot → evidence search loop as the default. Use address mapping before byte-level reasoning. Use the universal workspace generator for authorized slice mutation. For long-running/repeated Hopper work, keep the document open for live MCP follow-up or save a reusable `.hop` database. Use live Hopper MCP only when a task needs the active Hopper document, focused pseudocode, live cursor state, or reviewed annotations.

## Standards

Maintain compatibility with current Codex CLI skills and the Open Agent Skills layout:

- Root repository: `README.md`, `AGENTS.md`, and one or more skill directories.
- Skill directory name must match `SKILL.md` frontmatter `name`.
- `SKILL.md` must include `name` and `description` and should stay under 500 lines.
- Put deterministic tooling in `scripts/`.
- Put reusable templates and config snippets in `assets/`.
- Put focused, conditionally loaded documentation in `references/`.
- Keep file references one level deep from `SKILL.md`.
- Keep bundled `references/`, `scripts/`, and `assets/` files reachable from `SKILL.md`/reference instructions or from used scripts; the validator fails orphaned resources.

## Development Workflow

After changing scripts, metadata, assets, or references, run:

```bash
hopper-disassembler-analysis/scripts/validate_skill_repo.py .
python3 -m py_compile hopper-disassembler-analysis/scripts/*.py
bash -n hopper-disassembler-analysis/scripts/*.sh
```

On a macOS host with Hopper installed, also run:

```bash
hopper-disassembler-analysis/scripts/hopper_mcp_probe.py --json --call-tool none
hopper-disassembler-analysis/scripts/macos_toolchain_inventory.py --output /tmp/macos-toolchain.md
hopper-disassembler-analysis/scripts/inspect_macho_targets.py --include-deps --output /tmp/echo.inventory.md /bin/echo
hopper-disassembler-analysis/scripts/macho_address_map.py --queries-only --address 0x100000000 /bin/echo >/tmp/echo.address-map.txt || true
hopper-disassembler-analysis/scripts/run_hopper_export.sh \
  --timeout 180 \
  --procedure-pattern 'EntryPoint|sub_' \
  --max-procedures 5 \
  --max-basic-blocks 2 \
  --max-strings 10 \
  --max-string-xrefs 4 \
  --summary-output /tmp/echo.hopper-summary.md \
  --output /tmp/echo.hopper-snapshot.json \
  /bin/echo
hopper-disassembler-analysis/scripts/hopper_evidence_search.py /tmp/echo.hopper-snapshot.json 'EntryPoint|sub_' >/tmp/echo.evidence.md
```
