#!/usr/bin/env python3
"""Inventory Mach-O targets in a macOS executable, framework, or app bundle."""

from __future__ import annotations

import argparse
import json
import os
import plistlib
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

MACHO_MARKERS = (
    "Mach-O",
    "Mach-O universal binary",
)
CODE_DIRS = (
    "Contents/MacOS",
    "Contents/Frameworks",
    "Contents/XPCServices",
    "Contents/PlugIns",
    "Contents/Library/LoginItems",
    "Contents/Helpers",
)


@dataclass
class CommandResult:
    command: list[str]
    returncode: int | None
    stdout: str = ""
    stderr: str = ""
    error: str = ""


@dataclass
class MachOTarget:
    path: str
    role: str
    exists: bool
    executable: bool
    file_type: str = ""
    architectures: list[str] = field(default_factory=list)
    install_names: list[str] = field(default_factory=list)
    codesign_summary: list[str] = field(default_factory=list)
    error: str = ""


@dataclass
class Inventory:
    input_path: str
    kind: str
    bundle_identifier: str = ""
    bundle_executable: str = ""
    bundle_version: str = ""
    main_executable: str = ""
    targets: list[MachOTarget] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def run(argv: list[str], timeout: float = 10.0) -> CommandResult:
    try:
        proc = subprocess.run(
            argv,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except FileNotFoundError as exc:
        return CommandResult(argv, None, error=str(exc))
    except subprocess.TimeoutExpired as exc:
        return CommandResult(
            argv,
            None,
            stdout=exc.stdout or "",
            stderr=exc.stderr or "",
            error=f"timed out after {timeout:g}s",
        )
    return CommandResult(argv, proc.returncode, proc.stdout.strip(), proc.stderr.strip())


def read_plist(path: Path) -> dict[str, Any]:
    with path.open("rb") as handle:
        value = plistlib.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"plist root is not a dictionary: {path}")
    return value


def is_probably_executable_file(path: Path) -> bool:
    try:
        mode = path.stat().st_mode
    except OSError:
        return False
    return path.is_file() and bool(mode & 0o111)


def file_type(path: Path) -> str:
    result = run(["file", "-b", str(path)])
    return result.stdout if result.returncode == 0 else result.error or result.stderr


def is_macho_file(path: Path) -> tuple[bool, str]:
    text = file_type(path)
    return any(marker in text for marker in MACHO_MARKERS), text


def lipo_archs(path: Path) -> list[str]:
    result = run(["lipo", "-archs", str(path)])
    if result.returncode != 0 or not result.stdout:
        return []
    return result.stdout.split()


def dylib_refs(path: Path, max_lines: int) -> list[str]:
    result = run(["otool", "-L", str(path)], timeout=20.0)
    if result.returncode != 0:
        return []
    lines = []
    seen = set()
    for raw_line in result.stdout.splitlines()[1:]:
        line = raw_line.strip()
        if not line:
            continue
        if line.endswith(":") and "architecture" in line:
            continue
        if line in seen:
            continue
        seen.add(line)
        lines.append(line)
    return lines[:max_lines]


def codesign_summary(path: Path, max_lines: int) -> list[str]:
    result = run(["codesign", "-dv", "--verbose=4", str(path)], timeout=20.0)
    text = result.stderr or result.stdout
    if result.returncode != 0 and not text:
        return []
    prefixes = (
        "Executable=",
        "Identifier=",
        "Format=",
        "CodeDirectory",
        "Signature=",
        "Authority=",
        "TeamIdentifier=",
        "Runtime Version=",
        "Sealed Resources",
        "Internal requirements",
    )
    rows = [line.strip() for line in text.splitlines() if line.strip().startswith(prefixes)]
    return rows[:max_lines]


def make_target(
    path: Path, role: str, file_text: str = "", include_deps: bool = False
) -> MachOTarget:
    exists = path.exists()
    executable = is_probably_executable_file(path) if exists else False
    if exists and not file_text:
        _, file_text = is_macho_file(path)
    target = MachOTarget(
        path=str(path),
        role=role,
        exists=exists,
        executable=executable,
        file_type=file_text,
    )
    if not exists:
        target.error = "missing"
        return target
    target.architectures = lipo_archs(path)
    if include_deps:
        target.install_names = dylib_refs(path, max_lines=80)
        target.codesign_summary = codesign_summary(path, max_lines=40)
    return target


def candidate_paths_for_app(app: Path, max_files: int) -> tuple[list[tuple[Path, str]], list[str]]:
    warnings: list[str] = []
    candidates: list[tuple[Path, str]] = []
    plist = app / "Contents" / "Info.plist"
    main_executable = ""
    if plist.exists():
        try:
            info = read_plist(plist)
            exe_name = str(info.get("CFBundleExecutable") or "")
            if exe_name:
                main = app / "Contents" / "MacOS" / exe_name
                candidates.append((main, "main_executable"))
                main_executable = str(main)
        except Exception as exc:
            warnings.append(f"failed to read Info.plist: {exc}")
    else:
        warnings.append(f"missing Info.plist: {plist}")

    seen = {Path(path).resolve(strict=False) for path, _ in candidates}
    scanned = 0
    for rel in CODE_DIRS:
        root = app / rel
        if not root.exists():
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [name for name in dirnames if name not in {"_CodeSignature", "Resources"}]
            for filename in filenames:
                if scanned >= max_files:
                    warnings.append(f"stopped scanning after {max_files} files")
                    return candidates, warnings
                path = Path(dirpath) / filename
                scanned += 1
                try:
                    resolved = path.resolve(strict=False)
                except OSError:
                    resolved = path
                if resolved in seen:
                    continue
                if not is_probably_executable_file(path):
                    continue
                is_macho, text = is_macho_file(path)
                if not is_macho:
                    continue
                seen.add(resolved)
                if str(path) == main_executable:
                    continue
                role = "embedded_code"
                if ".framework/" in str(path):
                    role = "framework_executable"
                elif ".xpc/" in str(path):
                    role = "xpc_service_executable"
                elif ".appex/" in str(path):
                    role = "extension_executable"
                elif ".app/" in str(path.relative_to(app)):
                    role = "nested_app_executable"
                candidates.append((path, role))
    return candidates, warnings


def inspect_path(path: Path, include_deps: bool, max_files: int) -> Inventory:
    path = path.expanduser().resolve(strict=False)
    if path.is_dir() and path.suffix == ".app":
        inventory = Inventory(input_path=str(path), kind="app_bundle")
        plist = path / "Contents" / "Info.plist"
        if plist.exists():
            try:
                info = read_plist(plist)
                inventory.bundle_identifier = str(info.get("CFBundleIdentifier") or "")
                inventory.bundle_executable = str(info.get("CFBundleExecutable") or "")
                inventory.bundle_version = str(
                    info.get("CFBundleShortVersionString") or info.get("CFBundleVersion") or ""
                )
                if inventory.bundle_executable:
                    inventory.main_executable = str(
                        path / "Contents" / "MacOS" / inventory.bundle_executable
                    )
            except Exception as exc:
                inventory.warnings.append(f"failed to read bundle metadata: {exc}")
        candidates, warnings = candidate_paths_for_app(path, max_files=max_files)
        inventory.warnings.extend(warnings)
        for candidate, role in candidates:
            is_macho, text = is_macho_file(candidate) if candidate.exists() else (False, "")
            if is_macho or role == "main_executable":
                inventory.targets.append(
                    make_target(candidate, role, text, include_deps=include_deps)
                )
        return inventory

    if path.is_dir() and path.suffix == ".framework":
        inventory = Inventory(input_path=str(path), kind="framework_bundle")
        binary_name = path.stem
        candidate = path / binary_name
        if not candidate.exists():
            versions_current = path / "Versions" / "Current" / binary_name
            candidate = versions_current if versions_current.exists() else candidate
        inventory.targets.append(
            make_target(candidate, "framework_executable", include_deps=include_deps)
        )
        return inventory

    inventory = Inventory(input_path=str(path), kind="file")
    inventory.targets.append(make_target(path, "input_file", include_deps=include_deps))
    return inventory


def redact_home(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    home = str(Path.home())
    if value == home:
        return "~"
    if value.startswith(home + "/"):
        return "~/" + value[len(home) + 1 :]
    return value


def redact_tree(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: redact_tree(item) for key, item in value.items()}
    if isinstance(value, list):
        return [redact_tree(item) for item in value]
    return redact_home(value)


def render_markdown(data: dict[str, Any]) -> str:
    lines = ["# Mach-O Target Inventory", ""]
    lines.append(f"- Input: `{data['input_path']}`")
    lines.append(f"- Kind: `{data['kind']}`")
    if data.get("bundle_identifier"):
        lines.append(f"- Bundle ID: `{data['bundle_identifier']}`")
    if data.get("bundle_version"):
        lines.append(f"- Bundle version: `{data['bundle_version']}`")
    if data.get("main_executable"):
        lines.append(f"- Main executable: `{data['main_executable']}`")
    if data.get("warnings"):
        lines.append("- Warnings:")
        for warning in data["warnings"]:
            lines.append(f"  - {warning}")
    lines.append("")
    lines.append("## Targets")
    lines.append("")
    for index, target in enumerate(data.get("targets") or [], start=1):
        lines.append(f"### {index}. `{target.get('role')}`")
        lines.append("")
        lines.append(f"- Path: `{target.get('path')}`")
        lines.append(f"- Exists: `{target.get('exists')}`")
        lines.append(f"- Executable bit: `{target.get('executable')}`")
        lines.append(f"- File type: `{target.get('file_type')}`")
        archs = ", ".join(target.get("architectures") or [])
        lines.append(f"- Architectures: `{archs}`")
        if target.get("codesign_summary"):
            lines.append("- Code signature:")
            for row in target["codesign_summary"]:
                lines.append(f"  - `{row}`")
        if target.get("install_names"):
            lines.append("- Linked libraries:")
            for row in target["install_names"]:
                lines.append(f"  - `{row}`")
        if target.get("error"):
            lines.append(f"- Error: `{target['error']}`")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", type=Path, help="Mach-O file, .framework, or .app bundle.")
    parser.add_argument("-o", "--output", type=Path, help="Write output to this path.")
    parser.add_argument("--format", choices=("json", "markdown"), default="markdown")
    parser.add_argument(
        "--include-deps", action="store_true", help="Include otool -L and codesign summaries."
    )
    parser.add_argument(
        "--max-files", type=int, default=2000, help="Maximum app-bundle files to inspect."
    )
    parser.add_argument(
        "--redact-home", action="store_true", help="Redact the current user's home directory."
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    inventory = inspect_path(args.target, include_deps=args.include_deps, max_files=args.max_files)
    data = asdict(inventory)
    if args.redact_home:
        data = redact_tree(data)
    text = (
        json.dumps(data, indent=2, sort_keys=True) + "\n"
        if args.format == "json"
        else render_markdown(data)
    )
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
