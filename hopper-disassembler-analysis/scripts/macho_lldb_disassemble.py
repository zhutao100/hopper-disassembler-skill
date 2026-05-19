#!/usr/bin/env python3
"""Focused LLDB disassembly for Mach-O symbols or address ranges."""

from __future__ import annotations

import argparse
import shlex
import shutil
import subprocess
import sys
from pathlib import Path


def int_auto(value: str) -> int:
    try:
        return int(value, 0)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid integer: {value}") from exc


def hex_addr(value: int) -> str:
    return f"0x{value:x}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", type=Path, help="Mach-O or universal Mach-O file.")
    parser.add_argument("--arch", default="arm64", help="LLDB target architecture.")
    parser.add_argument(
        "--address",
        action="append",
        type=int_auto,
        default=[],
        help="Start address to disassemble. Repeatable.",
    )
    parser.add_argument(
        "--symbol",
        action="append",
        default=[],
        help="Symbol name to look up and disassemble. Repeatable.",
    )
    parser.add_argument(
        "--size",
        type=int_auto,
        default=0x160,
        help="Bytes to disassemble for each --address when --end-address is not set.",
    )
    parser.add_argument(
        "--end-address",
        type=int_auto,
        help="End address for a single --address query.",
    )
    parser.add_argument("--output", type=Path, help="Write output to this file.")
    parser.add_argument(
        "--max-lines",
        type=int,
        default=500,
        help="Maximum output lines; use 0 for no cap.",
    )
    parser.add_argument(
        "--cxxfilt",
        action="store_true",
        help="Pipe LLDB output through c++filt when available.",
    )
    return parser.parse_args()


def build_lldb_args(args: argparse.Namespace) -> list[str]:
    if not args.address and not args.symbol:
        raise ValueError("pass at least one --address or --symbol")
    if args.end_address is not None and len(args.address) != 1:
        raise ValueError("--end-address requires exactly one --address")
    if args.size <= 0:
        raise ValueError("--size must be positive")

    commands = [f"target create --arch {args.arch} {shlex.quote(str(args.target))}"]
    for symbol in args.symbol:
        quoted = shlex.quote(symbol)
        commands.append(f"image lookup -n {quoted}")
        commands.append(f"disassemble --name {quoted}")
    for address in args.address:
        end = args.end_address if args.end_address is not None else address + args.size
        commands.append(f"image lookup -a {hex_addr(address)}")
        commands.append(
            f"disassemble --start-address {hex_addr(address)} --end-address {hex_addr(end)}"
        )

    lldb = shutil.which("lldb")
    if not lldb:
        raise ValueError("lldb not found in PATH")
    lldb_args = [lldb, "--batch"]
    for command in commands:
        lldb_args.extend(["-o", command])
    return lldb_args


def maybe_cxxfilt(text: str, enabled: bool) -> str:
    if not enabled:
        return text
    cxxfilt = shutil.which("c++filt")
    if not cxxfilt:
        return text
    proc = subprocess.run(
        [cxxfilt],
        input=text,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    return proc.stdout if proc.returncode == 0 else text


def limit_lines(text: str, max_lines: int) -> str:
    if max_lines <= 0:
        return text
    lines = text.splitlines()
    if len(lines) <= max_lines:
        return text
    shown = lines[:max_lines]
    shown.append(f"[truncated: {len(lines) - max_lines} lines omitted; rerun with --max-lines 0]")
    return "\n".join(shown) + "\n"


def main() -> int:
    args = parse_args()
    try:
        if not args.target.is_file():
            raise ValueError(f"target is not a file: {args.target}")
        proc = subprocess.run(
            build_lldb_args(args),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        text = proc.stdout
        if proc.stderr:
            text += ("\n" if text else "") + "## stderr\n" + proc.stderr
        text = maybe_cxxfilt(text, args.cxxfilt)
        text = limit_lines(text, max(0, args.max_lines))
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
