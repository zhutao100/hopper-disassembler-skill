#!/usr/bin/env python3
"""Inventory macOS binary-analysis and mutation tools for Hopper workflows."""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass
class Probe:
    name: str
    category: str
    command: str
    path: str = ""
    available: bool = False
    version: str = ""
    notes: list[str] = field(default_factory=list)


@dataclass
class Inventory:
    host: dict[str, str]
    developer_dir: str = ""
    probes: list[Probe] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def run(argv: list[str], timeout: float = 5.0) -> tuple[int | None, str, str]:
    try:
        proc = subprocess.run(argv, check=False, capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError:
        return None, "", "not found"
    except subprocess.TimeoutExpired as exc:
        return None, exc.stdout or "", f"timed out after {timeout:g}s"
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


def first_line(text: str, limit: int = 180) -> str:
    for line in text.splitlines():
        line = line.strip()
        if line:
            return line[:limit]
    return ""


def which(command: str) -> str:
    if "/" in command:
        path = Path(command).expanduser()
        return str(path) if path.exists() else ""
    return shutil.which(command) or ""


def xcrun_find(tool: str) -> str:
    xcrun = shutil.which("xcrun")
    if not xcrun:
        return ""
    rc, out, _err = run([xcrun, "--find", tool])
    return out if rc == 0 and out else ""


def command_version(command: str, path: str) -> str:
    base = Path(command).name
    darwin = platform.system() == "Darwin"
    if darwin and base in {
        "lipo",
        "otool",
        "install_name_tool",
        "atos",
        "dwarfdump",
        "nm",
        "strings",
        "dyld_info",
        "vtool",
    }:
        # Apple developer tools commonly lack a stable --version. Report their family instead.
        return "Apple developer tool"
    if base == "codesign":
        rc, out, err = run([path, "-h"])
        return first_line(err or out) if rc is not None else ""
    if base == "file":
        rc, out, err = run([path, "--version"])
        return first_line(out or err) if rc is not None else ""
    if base == "hopper":
        # Hopper CLI may launch the app for normal arguments; avoid that here.
        return "Hopper CLI launcher"
    if base == "HopperMCPServer":
        return "Hopper MCP stdio server"
    for flag in ("--version", "-version", "version"):
        rc, out, err = run([path, flag])
        text = first_line(out or err)
        if rc == 0 and text:
            return text
    return ""


def probe(name: str, category: str, command: str, notes: list[str] | None = None) -> Probe:
    path = which(command)
    if not path:
        xcrun_path = xcrun_find(command)
        if xcrun_path:
            path = xcrun_path
    available = bool(path)
    return Probe(
        name=name,
        category=category,
        command=command,
        path=path,
        available=available,
        version=command_version(command, path) if available else "",
        notes=notes or [],
    )


def default_probes() -> list[Probe]:
    rows = [
        probe(
            "file",
            "built-in triage",
            "file",
            ["Identify Mach-O, universal, archive, and text files."],
        ),
        probe(
            "lipo",
            "built-in universal Mach-O",
            "lipo",
            ["List, thin, and create universal/fat files."],
        ),
        probe(
            "otool",
            "built-in Mach-O inspection",
            "otool",
            ["Inspect load commands, linked dylibs, symbols, and sections."],
        ),
        probe(
            "vtool",
            "built-in Mach-O inspection/mutation",
            "vtool",
            ["Show/edit LC_BUILD_VERSION and source version load commands."],
        ),
        probe(
            "codesign",
            "built-in signing",
            "codesign",
            ["Display, verify, and create code signatures; `-` is ad-hoc identity."],
        ),
        probe(
            "install_name_tool",
            "built-in dynamic-library mutation",
            "install_name_tool",
            ["Edit install names and dependency paths."],
        ),
        probe(
            "nm",
            "built-in symbols",
            "nm",
            ["List symbols; pair with swift-demangle or rustfilt when available."],
        ),
        probe("strings", "built-in strings", "strings", ["Fast literal triage before Hopper."]),
        probe(
            "dyld_info",
            "built-in dyld metadata",
            "dyld_info",
            ["Inspect rebase/bind/export/chained-fixup metadata when installed."],
        ),
        probe(
            "dwarfdump",
            "built-in debug metadata",
            "dwarfdump",
            ["Inspect DWARF and dSYM metadata."],
        ),
        probe(
            "atos",
            "built-in symbolication",
            "atos",
            ["Map addresses to symbols when symbols/dSYM are available."],
        ),
        probe(
            "lldb",
            "built-in debugger",
            "lldb",
            ["Dynamic validation; use only in a sandbox/VM for modified binaries."],
        ),
        probe(
            "clang",
            "built-in compiler/assembler",
            "clang",
            ["Assemble test snippets and generate comparison Mach-O fixtures."],
        ),
        probe(
            "swift-demangle",
            "built-in Swift",
            "swift-demangle",
            ["Demangle Swift names from nm/Hopper output."],
        ),
        probe(
            "llvm-objdump",
            "LLVM disassembly",
            "llvm-objdump",
            ["Alternative disassembler with Mach-O options."],
        ),
        probe(
            "llvm-otool",
            "LLVM Mach-O inspection",
            "llvm-otool",
            ["LLVM otool-compatible Mach-O dumper."],
        ),
        probe(
            "Hopper CLI", "Hopper", "hopper", ["Batch-open binaries and run Hopper Python scripts."]
        ),
        probe(
            "Hopper MCP",
            "Hopper",
            "HopperMCPServer",
            ["Official stdio MCP server, usually inside Hopper.app."],
        ),
        probe(
            "Hopper MCP bundled",
            "Hopper",
            "/Applications/Hopper Disassembler.app/Contents/MacOS/HopperMCPServer",
            [],
        ),
        probe("rustfilt", "popular demangling", "rustfilt", ["Optional Rust demangler."]),
        probe(
            "radare2", "popular binary analysis", "r2", ["CLI disassembly/debug/patching suite."]
        ),
        probe("rabin2", "popular binary analysis", "rabin2", ["radare2 binary metadata helper."]),
        probe(
            "Ghidra",
            "popular binary analysis",
            "ghidraRun",
            ["GUI decompiler/disassembler; useful cross-check for Hopper."],
        ),
        probe(
            "jtool2",
            "popular Mach-O",
            "jtool2",
            ["Third-party Mach-O and code-signature analysis; availability varies."],
        ),
        probe(
            "ipsw",
            "popular Apple firmware/Mach-O",
            "ipsw",
            ["Mach-O address/offset/lipo helpers, especially for Apple firmware work."],
        ),
    ]
    return rows


def developer_dir() -> str:
    rc, out, err = run(["xcode-select", "-p"])
    if rc == 0:
        return out
    return err


def build_inventory() -> Inventory:
    inv = Inventory(
        host={
            "platform": platform.platform(),
            "machine": platform.machine(),
            "python": sys.version.split()[0],
            "shell": os.environ.get("SHELL", ""),
        },
        developer_dir=developer_dir(),
        probes=default_probes(),
    )
    required = {"file", "lipo", "otool", "codesign"}
    missing_required = [
        row.name for row in inv.probes if row.name in required and not row.available
    ]
    if missing_required:
        inv.warnings.append("Missing core tools: " + ", ".join(missing_required))
    if not any(row.name == "Hopper CLI" and row.available for row in inv.probes):
        inv.warnings.append(
            "Hopper CLI launcher not found in PATH; use Hopper.app bundled path or install a symlink."
        )
    if not any(
        row.name in {"Hopper MCP", "Hopper MCP bundled"} and row.available for row in inv.probes
    ):
        inv.warnings.append(
            "Hopper MCP server not found; install Hopper 6+ or set HOPPER_MCP_SERVER."
        )
    return inv


def render_markdown(inv: Inventory) -> str:
    lines = ["# macOS Binary Toolchain Inventory", ""]
    lines.append("## Host")
    for key, value in inv.host.items():
        lines.append(f"- {key}: `{value}`")
    lines.append(f"- developer_dir: `{inv.developer_dir}`")
    if inv.warnings:
        lines.extend(["", "## Warnings"])
        for warning in inv.warnings:
            lines.append(f"- {warning}")
    lines.extend(["", "## Tools", ""])
    current_category = None
    for row in inv.probes:
        if row.category != current_category:
            current_category = row.category
            lines.extend([f"### {current_category}", ""])
        status = "yes" if row.available else "no"
        lines.append(f"- **{row.name}**: `{status}`")
        lines.append(f"  - command: `{row.command}`")
        if row.path:
            lines.append(f"  - path: `{row.path}`")
        if row.version:
            lines.append(f"  - version: `{row.version}`")
        for note in row.notes:
            lines.append(f"  - note: {note}")
    lines.append("")
    lines.append("## Recommended Baseline")
    lines.append(
        "- For read-only Hopper analysis: `file`, `lipo`, `otool`, `codesign`, Hopper CLI, and Hopper MCP."
    )
    lines.append(
        "- For authorized universal Mach-O mutation: add `vtool`, `install_name_tool`, `clang`, `lldb`, and a disposable test VM/sandbox."
    )
    lines.append(
        "- For source correlation: add `swift-demangle`, `rustfilt`, `dwarfdump`, and `atos` as applicable."
    )
    return "\n".join(lines).rstrip() + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    parser.add_argument("-o", "--output", type=Path, help="Write output to this path")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    inv = build_inventory()
    if args.format == "json":
        text = json.dumps(asdict(inv), indent=2, sort_keys=True) + "\n"
    else:
        text = render_markdown(inv)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
