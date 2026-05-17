# Agent Development Notes

This repository contains one installable skill: `hopper-disassembler-analysis`.

Prefer `scripts/run_hopper_export.sh` for validation runs. Write generated snapshots to `/tmp` unless a task explicitly asks for persistent artifacts.
Use the host Hopper installation for read-only exports; use a disposable VM/sandbox before running modified binaries or generated executables.

## Standards

Maintain compatibility with:

- Codex CLI skills: required `SKILL.md` with `name` and `description`, optional `agents/openai.yaml`, `scripts/`, `references/`, and `assets/`.
- Open Agent Skills: skill folder name must match `SKILL.md` `name`; `name` uses lowercase letters, digits, and hyphens; `description` describes both behavior and triggers.

Do not add process notes or ephemeral research logs to the skill. Put durable operational knowledge in `SKILL.md` or a focused reference file.

## Validation

Run these after script or skill metadata changes:

```bash
python3 "$HOME/.codex/skills/.system/skill-creator/scripts/quick_validate.py" hopper-disassembler-analysis
python3 -m py_compile hopper-disassembler-analysis/scripts/hopper_export_snapshot.py hopper-disassembler-analysis/scripts/hopper_mcp_probe.py
bash -n hopper-disassembler-analysis/scripts/run_hopper_export.sh hopper-disassembler-analysis/scripts/install_codex_hopper_mcp.sh hopper-disassembler-analysis/scripts/install_codex_skill.sh
hopper-disassembler-analysis/scripts/hopper_mcp_probe.py --json --call-tool none
hopper-disassembler-analysis/scripts/run_hopper_export.sh --timeout 180 --max-procedures 5 --max-strings 10 --max-string-xrefs 4 --output /tmp/echo.hopper-snapshot.json /bin/echo
```
