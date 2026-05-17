# Agent Development Notes

This repository contains one installable skill: `hopper-disassembler-analysis`.

Prefer `scripts/run_hopper_export.sh` for validation runs. Write generated snapshots to `/tmp` unless a task explicitly asks for persistent artifacts.

## Standards

Maintain compatibility with:

- Codex CLI skills: required `SKILL.md` with `name` and `description`, optional `agents/openai.yaml`, `scripts/`, `references/`, and `assets/`.
- Open Agent Skills: skill folder name must match `SKILL.md` `name`; `name` uses lowercase letters, digits, and hyphens; `description` describes both behavior and triggers.

Do not add process notes or ephemeral research logs to the skill. Put durable operational knowledge in `SKILL.md` or a focused reference file.
