# Hopper Disassembler Skill

Agent skill repository for repeatable Hopper Disassembler workflows on macOS.

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

`hopper-disassembler-analysis` helps agents inspect local binaries and macOS app bundles with Hopper Disassembler, Hopper Python scripts, and Hopper's bundled MCP server.

Primary entrypoint:

```text
hopper-disassembler-analysis/SKILL.md
```

Useful scripts:

```bash
hopper-disassembler-analysis/scripts/install_codex_skill.sh --replace
hopper-disassembler-analysis/scripts/run_hopper_export.sh --output /tmp/target.hopper-snapshot.json /path/to/Target.app
hopper-disassembler-analysis/scripts/hopper_mcp_probe.py --json --call-tool none
hopper-disassembler-analysis/scripts/hopper_mcp_probe.py --json --call-tool search_name --tool-args '{"pattern":"main"}'
hopper-disassembler-analysis/scripts/install_codex_hopper_mcp.sh --replace
```

## Install

Install the `hopper-disassembler-analysis/` directory as a skill directory in an agent client that supports Codex CLI skills or the Open Agent Skills layout.

Codex CLI:

```bash
hopper-disassembler-analysis/scripts/install_codex_skill.sh --replace
```

Manual install:

```bash
mkdir -p "${CODEX_HOME:-$HOME/.codex}/skills"
cp -R hopper-disassembler-analysis "${CODEX_HOME:-$HOME/.codex}/skills/"
```

For Codex CLI MCP integration with Hopper:

```bash
hopper-disassembler-analysis/scripts/install_codex_hopper_mcp.sh --replace
```

## Validation

```bash
python3 "$HOME/.codex/skills/.system/skill-creator/scripts/quick_validate.py" hopper-disassembler-analysis
python3 -m py_compile hopper-disassembler-analysis/scripts/hopper_mcp_probe.py hopper-disassembler-analysis/scripts/hopper_export_snapshot.py
hopper-disassembler-analysis/scripts/hopper_mcp_probe.py --json --call-tool none
hopper-disassembler-analysis/scripts/run_hopper_export.sh --timeout 180 --max-procedures 5 --max-strings 10 --max-string-xrefs 4 --output /tmp/echo.hopper-snapshot.json /bin/echo
```

Write generated snapshots to `/tmp` unless a task explicitly asks for persistent artifacts.
