# Hopper Disassembler Skill

Agent skill repository for repeatable, authorized Hopper Disassembler workflows on modern macOS.

## Contents

```text
README.md
AGENTS.md
hopper-disassembler-analysis/
├── SKILL.md
├── agents/openai.yaml
├── scripts/
├── references/
└── assets/
```

## Skill

`hopper-disassembler-analysis` helps agents inspect local binaries and macOS app bundles with Hopper Disassembler, Hopper Python scripts, Hopper's bundled MCP server, and deterministic snapshot artifacts.

Primary entrypoint:

```text
hopper-disassembler-analysis/SKILL.md
```

## Install

User-scoped install for current Codex/Open Agent Skills discovery:

```bash
hopper-disassembler-analysis/scripts/install_codex_skill.sh --replace
```

Repository-scoped install:

```bash
hopper-disassembler-analysis/scripts/install_codex_skill.sh --scope repo --replace
```

Legacy Codex install location for older builds:

```bash
hopper-disassembler-analysis/scripts/install_codex_skill.sh --scope legacy-codex --replace
```

Manual install:

```bash
mkdir -p "$HOME/.agents/skills"
cp -R hopper-disassembler-analysis "$HOME/.agents/skills/"
```

Optional Hopper UI script install:

```bash
hopper-disassembler-analysis/scripts/install_hopper_scripts.sh --replace
```

Optional Codex MCP integration with Hopper:

```bash
hopper-disassembler-analysis/scripts/install_codex_hopper_mcp.sh --replace
```

## Common Commands

Inventory available macOS analysis tools:

```bash
hopper-disassembler-analysis/scripts/macos_toolchain_inventory.py \
  --output /tmp/macos-toolchain.md
```

Inventory a target before Hopper:

```bash
hopper-disassembler-analysis/scripts/inspect_macho_targets.py \
  --include-deps \
  --output /tmp/target.inventory.md \
  /path/to/Target.app
```

Export a Hopper snapshot and LLM-oriented summary:

```bash
hopper-disassembler-analysis/scripts/run_hopper_export.sh \
  --summary-output /tmp/target.hopper-summary.md \
  --output /tmp/target.hopper-snapshot.json \
  /path/to/Target.app
```

Search an existing snapshot without reopening Hopper:

```bash
hopper-disassembler-analysis/scripts/hopper_evidence_search.py \
  --ignore-case \
  --output /tmp/target.evidence.md \
  /tmp/target.hopper-snapshot.json \
  'FunctionName|UniqueString|0x100003f50'
```

Map Hopper addresses to file offsets:

```bash
hopper-disassembler-analysis/scripts/macho_address_map.py \
  --arch arm64 \
  --queries-only \
  --address 0x100003f50 \
  /path/to/target
```

Create an authorized universal-slice workspace:

```bash
hopper-disassembler-analysis/scripts/macho_universal_workspace.py \
  --sign-ad-hoc \
  --output-dir /tmp/target.macho-workspace \
  /path/to/Target.app
```

For app-bundle inputs, modify copied slices under `patched/`, run `recombine.sh`, then use the generated `install_rebuilt_into_app.sh` only against a disposable app copy.

Probe Hopper MCP:

```bash
hopper-disassembler-analysis/scripts/hopper_mcp_probe.py --json --call-tool none
hopper-disassembler-analysis/scripts/hopper_mcp_probe.py --json --call-tool search_name --tool-args '{"pattern":"main"}'
```

## Validation

Portable validation that does not require Hopper:

```bash
hopper-disassembler-analysis/scripts/validate_skill_repo.py .
python3 -m py_compile hopper-disassembler-analysis/scripts/*.py
bash -n hopper-disassembler-analysis/scripts/*.sh
```

Optional validation on a licensed macOS host with Hopper installed:

```bash
hopper-disassembler-analysis/scripts/hopper_mcp_probe.py --json --call-tool none
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
hopper-disassembler-analysis/scripts/hopper_snapshot_summary.py \
  --filter 'EntryPoint|sub_' \
  /tmp/echo.hopper-snapshot.json \
  >/tmp/echo.hopper-summary.check.md
```

Write generated snapshots to `/tmp` unless a task explicitly asks for persistent artifacts.
