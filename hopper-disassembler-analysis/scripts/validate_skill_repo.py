#!/usr/bin/env python3
"""Validate the local skill repository layout without external dependencies."""

from __future__ import annotations

import argparse
import json
import re
import stat
import sys

try:
    import tomllib
except ModuleNotFoundError:  # Python < 3.11
    tomllib = None  # type: ignore[assignment]
from pathlib import Path
from typing import Any

NAME_PATTERN = re.compile(r"^[a-z0-9-]+$")
FRONTMATTER_PATTERN = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)
REQUIRED_ROOT_FILES = ("README.md", "AGENTS.md")
OPTIONAL_DIRS = ("scripts", "references", "assets", "agents")


class ValidationError(Exception):
    pass


def parse_frontmatter(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    match = FRONTMATTER_PATTERN.match(text)
    if not match:
        raise ValidationError(f"{path}: missing YAML frontmatter")
    data: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if not line.strip():
            continue
        if ":" not in line:
            raise ValidationError(f"{path}: unsupported frontmatter line: {line!r}")
        key, value = line.split(":", 1)
        data[key.strip()] = value.strip().strip("\"'")
    return data


def check_json(path: Path) -> None:
    with path.open(encoding="utf-8") as handle:
        json.load(handle)


def check_toml(path: Path) -> None:
    if tomllib is None:
        return
    with path.open("rb") as handle:
        tomllib.load(handle)


def executable(path: Path) -> bool:
    return bool(path.stat().st_mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH))


def validate_skill_dir(skill_dir: Path) -> list[str]:
    errors: list[str] = []
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        return [f"{skill_dir}: missing SKILL.md"]

    try:
        metadata = parse_frontmatter(skill_md)
    except Exception as exc:
        errors.append(str(exc))
        metadata = {}

    name = metadata.get("name", "")
    description = metadata.get("description", "")
    if not name:
        errors.append(f"{skill_md}: missing name")
    elif not NAME_PATTERN.fullmatch(name):
        errors.append(
            f"{skill_md}: invalid name {name!r}; use lowercase letters, digits, and hyphens"
        )
    elif name != skill_dir.name:
        errors.append(f"{skill_md}: name {name!r} must match directory {skill_dir.name!r}")
    if not description:
        errors.append(f"{skill_md}: missing description")
    elif len(description) > 700:
        errors.append(f"{skill_md}: description is too long for reliable implicit matching")

    line_count = len(skill_md.read_text(encoding="utf-8").splitlines())
    if line_count > 500:
        errors.append(f"{skill_md}: {line_count} lines; keep SKILL.md <= 500 lines")

    for dirname in OPTIONAL_DIRS:
        path = skill_dir / dirname
        if path.exists() and not path.is_dir():
            errors.append(f"{path}: expected directory")

    scripts = skill_dir / "scripts"
    if scripts.exists():
        for path in sorted(scripts.iterdir()):
            if path.is_file() and path.suffix in {".py", ".sh"} and not executable(path):
                errors.append(f"{path}: script is not executable")

    assets = skill_dir / "assets"
    if assets.exists():
        for path in sorted(assets.iterdir()):
            if not path.is_file():
                continue
            try:
                if path.suffix == ".json":
                    check_json(path)
                elif path.suffix == ".toml":
                    check_toml(path)
            except Exception as exc:
                errors.append(f"{path}: parse failed: {exc}")

    agents = skill_dir / "agents"
    if agents.exists() and (agents / "openai.yaml").exists():
        text = (agents / "openai.yaml").read_text(encoding="utf-8")
        if "interface:" not in text:
            errors.append(f"{agents / 'openai.yaml'}: expected interface metadata")
    return errors


def find_skill_dirs(root: Path) -> list[Path]:
    if (root / "SKILL.md").exists():
        return [root]
    return sorted(path.parent for path in root.glob("*/SKILL.md"))


def validate_root(root: Path) -> list[str]:
    errors: list[str] = []
    if not (root / "SKILL.md").exists():
        for name in REQUIRED_ROOT_FILES:
            if not (root / name).exists():
                errors.append(f"{root / name}: missing root file")
    skill_dirs = find_skill_dirs(root)
    if not skill_dirs:
        errors.append(f"{root}: no skill directory with SKILL.md found")
    for skill_dir in skill_dirs:
        errors.extend(validate_skill_dir(skill_dir))
    return errors


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "path", nargs="?", default=".", type=Path, help="Repository root or skill directory."
    )
    parser.add_argument(
        "--json", action="store_true", help="Emit machine-readable validation result."
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = args.path.resolve(strict=False)
    errors = validate_root(root)
    result: dict[str, Any] = {
        "path": str(root),
        "ok": not errors,
        "errors": errors,
    }
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        status = "ok" if result["ok"] else "failed"
        print(f"skill validation: {status}")
        for error in errors:
            print(f"- {error}")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
