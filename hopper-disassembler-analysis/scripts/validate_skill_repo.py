#!/usr/bin/env python3
"""Validate the local skill repository layout without external dependencies."""

from __future__ import annotations

import argparse
import fnmatch
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
GENERATED_PARTS = {"__pycache__"}
GENERATED_FILENAMES = {".DS_Store"}
GENERATED_SUFFIXES = {".pyc", ".pyo"}
RESOURCE_PATH_PATTERN = re.compile(
    r"(?<![A-Za-z0-9_.-])(?:references|scripts|assets)/[A-Za-z0-9_./*?\[\]-]+"
)
MARKDOWN_LINK_PATTERN = re.compile(r"!?\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")


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


def is_generated(path: Path) -> bool:
    return (
        any(part in GENERATED_PARTS for part in path.parts)
        or path.name in GENERATED_FILENAMES
        or path.suffix in GENERATED_SUFFIXES
    )


def resource_files(skill_dir: Path, dirname: str) -> set[Path]:
    root = skill_dir / dirname
    if not root.exists():
        return set()
    return {
        path.relative_to(skill_dir)
        for path in root.rglob("*")
        if path.is_file() and not is_generated(path.relative_to(skill_dir))
    }


def normalize_markdown_target(source_rel: Path, target: str) -> Path | None:
    target = target.strip().strip("<>").strip("\"'")
    if not target or "://" in target or target.startswith(("#", "mailto:", "tel:", "/")):
        return None
    target = target.split("#", 1)[0].split("?", 1)[0]
    if not target:
        return None
    base = source_rel.parent if source_rel.name != "SKILL.md" else Path(".")
    parts: list[str] = []
    for part in (base / target).parts:
        if part in {"", "."}:
            continue
        if part == "..":
            if not parts:
                return None
            parts.pop()
            continue
        parts.append(part)
    return Path(*parts) if parts else None


def path_tokens(text: str) -> set[str]:
    tokens: set[str] = set()
    for match in RESOURCE_PATH_PATTERN.finditer(text):
        tokens.add(match.group(0).rstrip(".,;:"))
    return tokens


def referenced_by_text(text: str, rel: Path) -> bool:
    rel_text = rel.as_posix()
    if rel_text in text or f"./{rel_text}" in text:
        return True
    for token in path_tokens(text):
        token = token.split("#", 1)[0]
        if any(char in token for char in "*?[") and fnmatch.fnmatch(rel_text, token):
            return True
    return False


def referenced_by_markdown_link(text: str, source_rel: Path, rel: Path) -> bool:
    for match in MARKDOWN_LINK_PATTERN.finditer(text):
        target = normalize_markdown_target(source_rel, match.group(1))
        if target == rel:
            return True
    return False


def referenced_by_basename(text: str, name: str) -> bool:
    return bool(re.search(rf"(?<![A-Za-z0-9_.-]){re.escape(name)}(?![A-Za-z0-9_.-])", text))


def referenced_from_markdown(text: str, source_rel: Path, rel: Path) -> bool:
    return referenced_by_text(text, rel) or referenced_by_markdown_link(text, source_rel, rel)


def orphaned_skill_files(skill_dir: Path) -> list[Path]:
    """Return bundled resource files not reached from instructions or used scripts."""

    references = resource_files(skill_dir, "references")
    scripts = resource_files(skill_dir, "scripts")
    assets = resource_files(skill_dir, "assets")

    markdown_seen: set[Path] = {Path("SKILL.md")}
    markdown_queue: list[Path] = [Path("SKILL.md")]
    used_references: set[Path] = set()
    used_scripts: set[Path] = set()
    used_assets: set[Path] = set()

    while markdown_queue:
        source_rel = markdown_queue.pop(0)
        text = (skill_dir / source_rel).read_text(encoding="utf-8")

        for rel in sorted(references):
            if referenced_from_markdown(text, source_rel, rel):
                if rel not in used_references:
                    used_references.add(rel)
                if rel.suffix.lower() == ".md" and rel not in markdown_seen:
                    markdown_seen.add(rel)
                    markdown_queue.append(rel)

        for rel in sorted(scripts):
            if referenced_from_markdown(text, source_rel, rel):
                used_scripts.add(rel)

        for rel in sorted(assets):
            if referenced_from_markdown(text, source_rel, rel):
                used_assets.add(rel)

    script_queue = list(sorted(used_scripts))
    script_seen: set[Path] = set()
    while script_queue:
        source_rel = script_queue.pop(0)
        if source_rel in script_seen:
            continue
        script_seen.add(source_rel)
        text = (skill_dir / source_rel).read_text(encoding="utf-8", errors="ignore")

        for rel in sorted(scripts):
            if rel == source_rel:
                continue
            if referenced_by_text(text, rel) or referenced_by_basename(text, rel.name):
                if rel not in used_scripts:
                    used_scripts.add(rel)
                    script_queue.append(rel)

        for rel in sorted(assets):
            if referenced_by_text(text, rel) or referenced_by_basename(text, rel.name):
                used_assets.add(rel)

    used = used_references | used_scripts | used_assets
    resources = references | scripts | assets
    return sorted(resources - used)


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

    for path in orphaned_skill_files(skill_dir):
        errors.append(
            f"{skill_dir / path}: orphaned skill file; reference it from SKILL.md or "
            "reachable markdown instructions, reference it from a used script, or remove it"
        )
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
