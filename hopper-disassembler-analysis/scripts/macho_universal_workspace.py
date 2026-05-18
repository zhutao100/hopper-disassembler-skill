#!/usr/bin/env python3
"""Create a safe workspace for authorized universal Mach-O slice analysis/mutation.

The script copies the target executable, extracts requested thin slices with
`lipo`, captures full baseline metadata as files, writes compact plan previews,
and writes ready-to-run helper scripts. It does not patch bytes; use Hopper or
other reviewed tooling on the copied thin slices only.
"""

from __future__ import annotations

import argparse
import json
import os
import plistlib
import shutil
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

MAX_COMMAND_LOG_CHARS = 1200


@dataclass
class CommandLog:
    command: list[str]
    returncode: int | None
    stdout: str = ""
    stderr: str = ""
    error: str = ""
    stdout_bytes: int = 0
    stderr_bytes: int = 0
    stdout_truncated: bool = False
    stderr_truncated: bool = False
    output_file: str | None = None


@dataclass
class WorkspacePlan:
    input_path: str
    executable_path: str
    workspace: str
    original_copy: str
    architectures: list[str]
    slices: dict[str, str]
    slice_info: dict[str, dict[str, Any]]
    metadata_files: list[str]
    scripts: dict[str, str]
    notes: list[str] = field(default_factory=list)
    commands: list[CommandLog] = field(default_factory=list)


def run(argv: list[str], timeout: float = 30.0) -> CommandLog:
    try:
        proc = subprocess.run(argv, check=False, capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError as exc:
        return CommandLog(argv, None, error=str(exc))
    except subprocess.TimeoutExpired as exc:
        return CommandLog(
            argv,
            None,
            stdout=exc.stdout or "",
            stderr=exc.stderr or "",
            error=f"timed out after {timeout:g}s",
        )
    stdout = proc.stdout.strip()
    stderr = proc.stderr.strip()
    return CommandLog(
        argv,
        proc.returncode,
        stdout,
        stderr,
        stdout_bytes=len(stdout.encode("utf-8")),
        stderr_bytes=len(stderr.encode("utf-8")),
    )


def compact_text(text: str, limit: int = MAX_COMMAND_LOG_CHARS) -> tuple[str, bool]:
    if len(text) <= limit:
        return text, False
    omitted = len(text) - limit
    return f"{text[:limit]}\n...[truncated {omitted} chars]", True


def compact_command_log(result: CommandLog, *, output_file: Path | None = None) -> CommandLog:
    stdout, stdout_truncated = compact_text(result.stdout)
    stderr, stderr_truncated = compact_text(result.stderr)
    return CommandLog(
        command=result.command,
        returncode=result.returncode,
        stdout=stdout,
        stderr=stderr,
        error=result.error,
        stdout_bytes=result.stdout_bytes or len(result.stdout.encode("utf-8")),
        stderr_bytes=result.stderr_bytes or len(result.stderr.encode("utf-8")),
        stdout_truncated=stdout_truncated,
        stderr_truncated=stderr_truncated,
        output_file=str(output_file) if output_file else None,
    )


def resolve_app_executable(path: Path) -> Path:
    if not (path.is_dir() and path.suffix == ".app"):
        return path
    plist_path = path / "Contents" / "Info.plist"
    if not plist_path.exists():
        raise ValueError(f"missing Info.plist in app bundle: {path}")
    with plist_path.open("rb") as handle:
        info = plistlib.load(handle)
    executable = info.get("CFBundleExecutable")
    if not isinstance(executable, str) or not executable:
        raise ValueError(f"missing CFBundleExecutable in {plist_path}")
    binary = path / "Contents" / "MacOS" / executable
    if not binary.is_file():
        raise ValueError(f"bundle executable does not exist: {binary}")
    return binary


def lipo_archs(path: Path) -> tuple[list[str], CommandLog]:
    result = run(["lipo", "-archs", str(path)])
    if result.returncode == 0 and result.stdout:
        return result.stdout.split(), result
    return [], result


def parse_lipo_detailed_info(text: str) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    current: dict[str, Any] | None = None
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line.startswith("architecture "):
            arch = line.split(None, 1)[1]
            current = {"arch": arch}
            rows[arch] = current
            continue
        if current is None:
            continue
        if line.startswith("cputype "):
            current["cputype"] = line.split(None, 1)[1]
        elif line.startswith("cpusubtype "):
            current["cpusubtype"] = line.split(None, 1)[1]
        elif line.startswith("capabilities "):
            current["capabilities"] = line.split(None, 1)[1]
        elif line.startswith("offset "):
            value = int(line.split()[1], 10)
            current["source_offset"] = value
            current["source_offset_hex"] = hex(value)
        elif line.startswith("size "):
            value = int(line.split()[1], 10)
            current["source_size"] = value
            current["source_size_hex"] = hex(value)
        elif line.startswith("align "):
            current["align"] = line.split(None, 1)[1]
    return rows


def lipo_slice_metadata(path: Path) -> dict[str, dict[str, Any]]:
    result = run(["lipo", "-detailed_info", str(path)])
    if result.returncode != 0:
        return {}
    return parse_lipo_detailed_info(result.stdout)


def safe_name(path: Path) -> str:
    text = path.name or "target"
    return "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in text)


def copy_executable(src: Path, dst: Path, *, read_only: bool = False) -> None:
    """Copy bytes and mode without preserving SIP flags or other host metadata."""
    shutil.copyfile(src, dst)
    mode = src.stat().st_mode & 0o777
    if read_only:
        mode &= ~0o222
    dst.chmod(mode)


def write_command_output(path: Path, result: CommandLog) -> None:
    lines = [
        "$ " + " ".join(json.dumps(part) if " " in part else part for part in result.command),
        "",
    ]
    if result.returncode is not None:
        lines.append(f"returncode: {result.returncode}")
    if result.error:
        lines.extend(["", "error:", result.error])
    if result.stdout:
        lines.extend(["", "stdout:", result.stdout])
    if result.stderr:
        lines.extend(["", "stderr:", result.stderr])
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def capture_metadata(binary: Path, metadata_dir: Path, plan: WorkspacePlan) -> None:
    commands = {
        "file.txt": ["file", str(binary)],
        "lipo-detailed-info.txt": ["lipo", "-detailed_info", str(binary)],
        "otool-load-commands.txt": ["otool", "-l", str(binary)],
        "otool-linked-libraries.txt": ["otool", "-L", str(binary)],
        "vtool-build.txt": ["vtool", "-show-build", str(binary)],
        "codesign-display.txt": ["codesign", "-dv", "--verbose=4", str(binary)],
    }
    for filename, argv in commands.items():
        result = run(argv, timeout=60.0)
        out_path = metadata_dir / filename
        write_command_output(out_path, result)
        plan.metadata_files.append(str(out_path))
        plan.commands.append(compact_command_log(result, output_file=out_path))


def shell_array(values: list[str]) -> str:
    return " ".join("'" + value.replace("'", "'\\''") + "'" for value in values)


def write_recombine_script(workspace: Path, base: str, archs: list[str], sign: bool) -> Path:
    script = workspace / "recombine.sh"
    arch_literals = shell_array(archs)
    sign_block = (
        'codesign --force --sign - "${out}"\n'
        if sign
        else 'echo "skip ad-hoc signing; pass --sign-ad-hoc when creating workspace to enable by default"\n'
    )
    script.write_text(
        f"""#!/usr/bin/env bash
set -euo pipefail
script_dir="$(cd "$(dirname "${{BASH_SOURCE[0]}}")" && pwd -P)"
base={json.dumps(base)}
archs=({arch_literals})
mkdir -p "${{script_dir}}/rebuilt"
out="${{script_dir}}/rebuilt/${{base}}"
inputs=()
for arch in "${{archs[@]}}"; do
    candidate="${{script_dir}}/patched/${{base}}.${{arch}}"
    if [[ ! -f "${{candidate}}" ]]; then
        candidate="${{script_dir}}/slices/${{base}}.${{arch}}"
    fi
    if [[ ! -f "${{candidate}}" ]]; then
        echo "error: missing slice for ${{arch}}: ${{candidate}}" >&2
        exit 2
    fi
    inputs+=("${{candidate}}")
done
if [[ "${{#inputs[@]}}" -eq 1 ]]; then
    cp "${{inputs[0]}}" "${{out}}"
else
    lipo -create "${{inputs[@]}}" -output "${{out}}"
fi
{sign_block}file "${{out}}"
lipo -detailed_info "${{out}}" || true
echo "rebuilt ${{out}}"
""",
        encoding="utf-8",
    )
    script.chmod(0o755)
    return script


def write_install_app_script(
    workspace: Path, base: str, app_path: Path, executable_path: Path, sign: bool
) -> Path:
    script = workspace / "install_rebuilt_into_app.sh"
    try:
        executable_rel = executable_path.relative_to(app_path)
    except ValueError:
        executable_rel = Path("Contents") / "MacOS" / base
    sign_block = (
        """
codesign_args=(--force --deep --options runtime --sign -)
if [[ -n "${ENTITLEMENTS_PLIST:-}" ]]; then
    codesign_args+=(--entitlements "${ENTITLEMENTS_PLIST}")
else
    echo "using ad-hoc app signature without explicit entitlements"
fi
codesign "${codesign_args[@]}" "${app_path}"
codesign --verify --deep --strict --verbose=2 "${app_path}"
"""
        if sign
        else """
echo "installed rebuilt executable; sign and verify the app bundle before launch"
"""
    )
    script.write_text(
        f"""#!/usr/bin/env bash
set -euo pipefail
script_dir="$(cd "$(dirname "${{BASH_SOURCE[0]}}")" && pwd -P)"
base={json.dumps(base)}
default_app_path={json.dumps(str(app_path))}
executable_rel={json.dumps(str(executable_rel))}
app_path="${{APP_COPY_PATH:-${{default_app_path}}}}"
executable_path="${{app_path}}/${{executable_rel}}"
rebuilt="${{script_dir}}/rebuilt/${{base}}"
if [[ "${{app_path}}" == /Applications/* && "${{ALLOW_INSTALLED_APP_WRITE:-0}}" != "1" ]]; then
    echo "error: refusing to install into /Applications without ALLOW_INSTALLED_APP_WRITE=1" >&2
    echo "use a disposable app copy for mutation experiments" >&2
    echo "example: APP_COPY_PATH=/tmp/Target.app ./install_rebuilt_into_app.sh" >&2
    exit 2
fi
if [[ ! -f "${{rebuilt}}" ]]; then
    echo "error: rebuilt executable not found: ${{rebuilt}}" >&2
    echo "run ./recombine.sh first" >&2
    exit 2
fi
if [[ ! -d "${{app_path}}" ]]; then
    echo "error: app bundle not found: ${{app_path}}" >&2
    exit 2
fi
if [[ ! -f "${{executable_path}}" ]]; then
    echo "error: app executable not found: ${{executable_path}}" >&2
    exit 2
fi
install -m 755 "${{rebuilt}}" "${{executable_path}}"
{sign_block}echo "installed ${{rebuilt}} -> ${{executable_path}}"
""",
        encoding="utf-8",
    )
    script.chmod(0o755)
    return script


def write_workflow(plan: WorkspacePlan, sign: bool) -> None:
    workspace = Path(plan.workspace)
    lines = ["# Universal Mach-O Workspace", ""]
    lines.append(
        "This workspace is for authorized analysis and mutation of copied thin slices only."
    )
    lines.append("")
    lines.append("## Baseline")
    lines.append(f"- Input: `{plan.input_path}`")
    lines.append(f"- Executable: `{plan.executable_path}`")
    lines.append(f"- Original copy: `{plan.original_copy}`")
    lines.append(f"- Architectures: `{', '.join(plan.architectures)}`")
    lines.append("")
    lines.append("## Directory Layout")
    lines.append("- `original/`: read-only copy of the original executable.")
    lines.append("- `slices/`: thin slices extracted from the original copy.")
    lines.append(
        "- `patched/`: place reviewed Hopper-produced or otherwise modified thin slices here, named `<binary>.<arch>`."
    )
    lines.append("- `rebuilt/`: output directory for `recombine.sh`.")
    lines.append("- `metadata/`: baseline `file`, `lipo`, `otool`, `vtool`, and `codesign` output.")
    lines.append("")
    lines.append("## Slice Files")
    for arch, path in plan.slices.items():
        info = plan.slice_info.get(arch, {})
        source_offset = info.get("source_offset_hex")
        source_size = info.get("source_size_hex")
        details = []
        if source_offset:
            details.append(f"source offset `{source_offset}`")
        if source_size:
            details.append(f"source size `{source_size}`")
        suffix = f" ({', '.join(details)})" if details else ""
        lines.append(f"- `{arch}`: `{path}`{suffix}")
    lines.append("")
    lines.append("## Recommended Flow")
    lines.append(
        "1. Open one copied thin slice in Hopper; do not open or modify the installed app copy."
    )
    lines.append(
        "2. Record the Hopper architecture, procedure address, file offset, original bytes, changed bytes, and rationale."
    )
    lines.append(
        "3. Copy the target slice into `patched/`, make it writable, then produce the reviewed modified executable using the same `<binary>.<arch>` name."
    )
    lines.append("4. Repeat for each architecture that must preserve identical behavior.")
    lines.append("5. Run `./recombine.sh` from this workspace.")
    if sign:
        lines.append(
            "6. `recombine.sh` ad-hoc signs the rebuilt executable. For distribution, use the project’s normal Developer ID/notarization path instead."
        )
    else:
        lines.append(
            "6. Re-sign the rebuilt executable with the identity appropriate for the authorized test or distribution path."
        )
    lines.append("")
    lines.append("## Recombine")
    lines.append("```bash")
    lines.append("./recombine.sh")
    lines.append("```")
    if "install_app" in plan.scripts:
        lines.append("")
        lines.append("## Install Into App Copy")
        lines.append(
            "For `.app` inputs, install the rebuilt executable into the input app bundle only when that input is a disposable copy:"
        )
        lines.append("")
        lines.append("```bash")
        lines.append("APP_COPY_PATH=/tmp/Target.app ./install_rebuilt_into_app.sh")
        lines.append("```")
        if sign:
            lines.append("")
            lines.append(
                "Set `ENTITLEMENTS_PLIST=/path/to/entitlements.plist` when the local test signature needs explicit entitlements. For ad-hoc app tests, use local test entitlements and do not preserve production team, application-identifier, iCloud, or push entitlements."
            )
    lines.append("")
    lines.append("## Address Mapping")
    lines.append("Use the skill’s address mapper against the original or rebuilt file:")
    lines.append("")
    lines.append("```bash")
    lines.append(
        "scripts/macho_address_map.py --queries-only --arch arm64 --address 0x100000000 /path/to/binary"
    )
    lines.append("```")
    lines.append("")
    lines.append("## Notes")
    for note in plan.notes:
        lines.append(f"- {note}")
    (workspace / "WORKFLOW.md").write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def create_workspace(args: argparse.Namespace) -> WorkspacePlan:
    input_path = args.target.expanduser().resolve(strict=False)
    binary = resolve_app_executable(input_path).resolve(strict=False)
    if not binary.is_file():
        raise ValueError(f"target executable is not a file: {binary}")
    base = safe_name(binary)
    workspace = args.output_dir
    if workspace is None:
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        workspace = Path("/tmp") / f"macho-workspace-{base}-{timestamp}"
    workspace = workspace.expanduser().resolve(strict=False)
    for subdir in ("original", "slices", "patched", "rebuilt", "metadata"):
        (workspace / subdir).mkdir(parents=True, exist_ok=True)

    original_copy = workspace / "original" / base
    copy_executable(binary, original_copy, read_only=True)

    detected_archs, arch_cmd = lipo_archs(original_copy)
    source_slice_info = lipo_slice_metadata(original_copy)
    archs = args.arch or detected_archs
    if not archs:
        raise ValueError(
            "could not determine architectures with lipo; pass --arch explicitly on a macOS host"
        )
    if not detected_archs and len(archs) > 1:
        raise ValueError(
            "lipo is required to extract multiple architectures; rerun on macOS with Xcode Command Line Tools"
        )

    plan = WorkspacePlan(
        input_path=str(input_path),
        executable_path=str(binary),
        workspace=str(workspace),
        original_copy=str(original_copy),
        architectures=archs,
        slices={},
        slice_info={},
        metadata_files=[],
        scripts={},
        notes=[],
        commands=[compact_command_log(arch_cmd)],
    )
    if len(detected_archs) <= 1:
        plan.notes.append(
            "Target appears thin or lipo reported one architecture; recombine.sh will copy a single selected slice."
        )
    if not detected_archs:
        plan.notes.append(
            "lipo did not report architectures. Assuming the explicit single --arch names a thin input copy."
        )
    if input_path.is_dir() and input_path.suffix == ".app":
        plan.notes.append(
            "Input was an app bundle. Rebuilt executable is not installed automatically; use install_rebuilt_into_app.sh only for disposable app copies."
        )

    for arch in archs:
        out = workspace / "slices" / f"{base}.{arch}"
        if not detected_archs and len(archs) == 1:
            copy_executable(original_copy, out, read_only=True)
        elif len(detected_archs) > 1 or arch not in detected_archs:
            result = run(
                ["lipo", "-thin", arch, str(original_copy), "-output", str(out)], timeout=60.0
            )
            plan.commands.append(compact_command_log(result))
            if result.returncode != 0:
                raise ValueError(
                    f"failed to extract {arch}: {result.stderr or result.stdout or result.error}"
                )
            out.chmod(out.stat().st_mode & ~0o222)
        else:
            copy_executable(original_copy, out, read_only=True)
        plan.slices[arch] = str(out)
        info = dict(source_slice_info.get(arch, {}))
        info.setdefault("arch", arch)
        info["path"] = str(out)
        info["thin_size"] = out.stat().st_size
        info["thin_size_hex"] = hex(out.stat().st_size)
        if len(detected_archs) <= 1:
            info.setdefault("source_offset", 0)
            info.setdefault("source_offset_hex", "0x0")
            info.setdefault("source_size", out.stat().st_size)
            info.setdefault("source_size_hex", hex(out.stat().st_size))
        plan.slice_info[arch] = info

    capture_metadata(original_copy, workspace / "metadata", plan)
    recombine = write_recombine_script(workspace, base, archs, sign=args.sign_ad_hoc)
    plan.scripts["recombine"] = str(recombine)
    if input_path.is_dir() and input_path.suffix == ".app":
        install_app = write_install_app_script(
            workspace, base, input_path, binary, sign=args.sign_ad_hoc
        )
        plan.scripts["install_app"] = str(install_app)
    write_workflow(plan, sign=args.sign_ad_hoc)
    plan.scripts["workflow"] = str(workspace / "WORKFLOW.md")
    (workspace / "plan.json").write_text(
        json.dumps(asdict(plan), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return plan


def render_markdown(plan: WorkspacePlan) -> str:
    lines = ["# Created Mach-O Workspace", ""]
    lines.append(f"- Workspace: `{plan.workspace}`")
    lines.append(f"- Executable: `{plan.executable_path}`")
    lines.append(f"- Original copy: `{plan.original_copy}`")
    lines.append(f"- Architectures: `{', '.join(plan.architectures)}`")
    lines.append("- Slices:")
    for arch, path in plan.slices.items():
        info = plan.slice_info.get(arch, {})
        details = []
        if info.get("source_offset_hex"):
            details.append(f"source offset `{info['source_offset_hex']}`")
        if info.get("source_size_hex"):
            details.append(f"source size `{info['source_size_hex']}`")
        if info.get("thin_size_hex"):
            details.append(f"thin size `{info['thin_size_hex']}`")
        suffix = f" ({', '.join(details)})" if details else ""
        lines.append(f"  - `{arch}`: `{path}`{suffix}")
    lines.append("- Scripts:")
    for name, path in plan.scripts.items():
        lines.append(f"  - `{name}`: `{path}`")
    if plan.notes:
        lines.append("- Notes:")
        for note in plan.notes:
            lines.append(f"  - {note}")
    return "\n".join(lines).rstrip() + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", type=Path, help="Mach-O file or .app bundle")
    parser.add_argument(
        "--arch",
        action="append",
        help="Architecture to extract. May be repeated. Defaults to all lipo-reported archs.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Workspace directory. Default: /tmp/macho-workspace-<binary>-<timestamp>",
    )
    parser.add_argument(
        "--sign-ad-hoc",
        action="store_true",
        help="Generate recombine.sh with `codesign --force --sign -`.",
    )
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    parser.add_argument("-o", "--output", type=Path, help="Write command summary to this path")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        plan = create_workspace(args)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    text = (
        json.dumps(asdict(plan), indent=2, sort_keys=True) + "\n"
        if args.format == "json"
        else render_markdown(plan)
    )
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
