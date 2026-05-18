#!/usr/bin/env python3
"""Render a compact, source-correlation friendly Hopper snapshot summary."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Summarize hopper_export_snapshot.py JSON for LLM review."
    )
    parser.add_argument("snapshot", type=Path, help="Snapshot JSON path.")
    parser.add_argument("-o", "--output", type=Path, help="Write summary to this path.")
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    parser.add_argument(
        "--filter",
        help="Only include rows whose identity, string, signature, address, or xref text matches this regex.",
    )
    parser.add_argument("--max-procedures", type=int, default=12)
    parser.add_argument("--max-strings", type=int, default=20)
    parser.add_argument("--max-names", type=int, default=20)
    parser.add_argument("--max-call-refs", type=int, default=8)
    parser.add_argument("--max-basic-blocks", type=int, default=3)
    parser.add_argument("--max-instructions", type=int, default=8)
    parser.add_argument("--max-pseudocode-chars", type=int, default=1600)
    parser.add_argument("--max-string-chars", type=int, default=220)
    return parser.parse_args()


def load_snapshot(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("snapshot root must be a JSON object")
    return data


def redact_path(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    home = str(Path.home())
    if value == home:
        return "~"
    if value.startswith(home + "/"):
        return "~/" + value[len(home) + 1 :]
    return value


def shorten(value: Any, limit: int) -> str:
    text = "" if value is None else str(value)
    text = text.replace("\r", "\\r").replace("\n", "\\n")
    if limit >= 0 and len(text) > limit:
        if limit <= 3:
            return text[:limit]
        return text[: max(0, limit - 3)] + "..."
    return text


def shorten_multiline(value: Any, limit: int) -> str:
    text = "" if value is None else str(value)
    text = text.replace("\r", "")
    if limit >= 0 and len(text) > limit:
        if limit <= 3:
            return text[:limit]
        return text[: max(0, limit - 3)] + "..."
    return text


def q(value: Any, limit: int = 220) -> str:
    return json.dumps(shorten(value, limit), ensure_ascii=True)


def row_text(row: Any) -> str:
    if isinstance(row, dict):
        parts: list[str] = []
        for key, value in row.items():
            if key in {"basic_blocks", "instructions", "pseudocode"}:
                continue
            if isinstance(value, (str, int, float, bool)) or value is None:
                parts.append(str(value))
            elif isinstance(value, list):
                parts.extend(row_text(item) for item in value[:8])
            elif isinstance(value, dict):
                parts.append(row_text(value))
        return " ".join(parts)
    if isinstance(row, list):
        return " ".join(row_text(item) for item in row[:8])
    return str(row)


def matches(row: Any, pattern: re.Pattern[str] | None) -> bool:
    if pattern is None:
        return True
    return bool(pattern.search(row_text(row)))


def limited_rows(
    rows: list[dict[str, Any]], pattern: re.Pattern[str] | None, limit: int
) -> tuple[list[dict[str, Any]], int]:
    matched = [row for row in rows if matches(row, pattern)]
    return matched[: max(0, limit)], len(matched)


def compact_ref(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "from": row.get("from"),
        "to": row.get("to"),
        "from_name": row.get("from_name") or "",
        "to_name": row.get("to_name") or "",
        "type": row.get("type_name") or "",
        "procedure": row.get("procedure"),
        "procedure_name": row.get("procedure_demangled") or row.get("procedure_name") or "",
    }


def compact_instruction(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "address": row.get("address"),
        "mnemonic": row.get("mnemonic"),
        "args": row.get("formatted_args") or [],
        "comment": row.get("comment") or row.get("inline_comment") or "",
    }


def compact_block(block: dict[str, Any], max_instructions: int) -> dict[str, Any]:
    instructions = block.get("instructions") or []
    return {
        "start": block.get("start"),
        "end": block.get("end"),
        "successors": block.get("successors") or [],
        "instructions_truncated": block.get("instructions_truncated", False),
        "instructions": [
            compact_instruction(row) for row in instructions[: max(0, max_instructions)]
        ],
    }


def compact_procedure(
    proc: dict[str, Any],
    max_call_refs: int,
    max_blocks: int,
    max_instructions: int,
    max_pseudo: int,
) -> dict[str, Any]:
    pseudocode = proc.get("pseudocode", "")
    return {
        "address": proc.get("address"),
        "file_offset": proc.get("file_offset"),
        "name": proc.get("name"),
        "demangled": proc.get("demangled"),
        "signature": proc.get("signature"),
        "basic_block_count": proc.get("basic_block_count"),
        "basic_blocks_truncated": proc.get("basic_blocks_truncated", False),
        "callers": [compact_ref(row) for row in (proc.get("callers") or [])[:max_call_refs]],
        "callees": [compact_ref(row) for row in (proc.get("callees") or [])[:max_call_refs]],
        "basic_blocks": [
            compact_block(block, max_instructions)
            for block in (proc.get("basic_blocks") or [])[: max(0, max_blocks)]
        ],
        "pseudocode": shorten_multiline(pseudocode, max_pseudo),
        "pseudocode_length": proc.get("pseudocode_length", len(pseudocode)),
        "pseudocode_truncated": proc.get("pseudocode_truncated", False)
        or (max_pseudo >= 0 and len(str(pseudocode)) > max_pseudo),
    }


def build_compact(data: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    pattern = re.compile(args.filter) if args.filter else None
    procedures, procedure_matches = limited_rows(
        data.get("procedures") or [], pattern, args.max_procedures
    )
    strings, string_matches = limited_rows(data.get("strings") or [], pattern, args.max_strings)
    names, name_matches = limited_rows(data.get("names") or [], pattern, args.max_names)

    document = dict(data.get("document") or {})
    for key in ("executable_path", "database_path"):
        document[key] = redact_path(document.get(key))

    return {
        "document": document,
        "version": data.get("version"),
        "created_at": data.get("created_at"),
        "counts": data.get("counts") or {},
        "truncated": data.get("truncated") or {},
        "limits": data.get("limits") or {},
        "filter": args.filter or "",
        "matched": {
            "procedures": procedure_matches,
            "strings": string_matches,
            "names": name_matches,
        },
        "procedures": [
            compact_procedure(
                proc,
                args.max_call_refs,
                args.max_basic_blocks,
                args.max_instructions,
                args.max_pseudocode_chars,
            )
            for proc in procedures
        ],
        "strings": [
            {
                "address": row.get("address"),
                "file_offset": row.get("file_offset"),
                "segment": row.get("segment"),
                "value": shorten(row.get("value", ""), args.max_string_chars),
                "truncated_value": row.get("truncated_value", False),
                "xrefs_truncated": row.get("xrefs_truncated", False),
                "xrefs_to": [
                    compact_ref(ref) for ref in (row.get("xrefs_to") or [])[: args.max_call_refs]
                ],
            }
            for row in strings
        ],
        "names": [
            {
                "address": row.get("address"),
                "file_offset": row.get("file_offset"),
                "name": row.get("name"),
                "demangled": row.get("demangled"),
                "segment": row.get("segment"),
            }
            for row in names
        ],
    }


def section(title: str) -> str:
    return f"\n## {title}\n"


def render_refs(title: str, refs: list[dict[str, Any]]) -> list[str]:
    lines = [f"  - {title}:"] if refs else []
    for ref in refs:
        if title == "Callers":
            target = ref.get("from") or ref.get("procedure") or "?"
            name = ref.get("from_name") or ref.get("procedure_name") or ""
        else:
            target = ref.get("to") or ref.get("from") or "?"
            name = ref.get("to_name") or ref.get("procedure_name") or ref.get("from_name") or ""
        type_name = ref.get("type") or ""
        detail = f" {q(name, 140)}" if name else ""
        suffix = f" ({type_name})" if type_name else ""
        lines.append(f"    - `{target}`{detail}{suffix}")
    return lines


def render_markdown(compact: dict[str, Any]) -> str:
    lines: list[str] = ["# Hopper Snapshot Summary"]
    document = compact["document"]
    lines.extend(
        [
            "",
            f"- Document: `{q(document.get('name'), 120).strip(chr(34))}`",
            f"- Executable: `{redact_path(document.get('executable_path') or '')}`",
            f"- Entry point: `{document.get('entry_point') or ''}`",
            f"- Hopper version: `{document.get('hopper_version') or ''}`",
            f"- Background analysis active: `{document.get('background_analysis_active')}`",
            f"- Counts: `{json.dumps(compact['counts'], sort_keys=True)}`",
            f"- Truncated: `{json.dumps(compact['truncated'], sort_keys=True)}`",
        ]
    )
    if compact["filter"]:
        lines.append(f"- Filter: `{compact['filter']}`")
    lines.append(f"- Matched rows before caps: `{json.dumps(compact['matched'], sort_keys=True)}`")

    if compact["procedures"]:
        lines.append(section("Procedures"))
    for proc in compact["procedures"]:
        label = proc.get("demangled") or proc.get("name") or ""
        lines.append(f"- `{proc.get('address')}` {q(label, 220)}")
        lines.append(f"  - Raw name: `{shorten(proc.get('name'), 220)}`")
        lines.append(f"  - Signature: `{shorten(proc.get('signature'), 220)}`")
        lines.append(
            "  - Basic blocks: "
            f"`{len(proc.get('basic_blocks') or [])}` exported of `{proc.get('basic_block_count')}`; "
            f"truncated=`{proc.get('basic_blocks_truncated')}`"
        )
        lines.extend(render_refs("Callers", proc.get("callers") or []))
        lines.extend(render_refs("Callees", proc.get("callees") or []))
        for block in proc.get("basic_blocks") or []:
            lines.append(
                f"  - Block `{block.get('start')}` -> `{block.get('end')}`, "
                f"successors=`{block.get('successors')}`, "
                f"instructions_truncated=`{block.get('instructions_truncated')}`"
            )
            for ins in block.get("instructions") or []:
                args = ", ".join(shorten(arg, 80) for arg in ins.get("args") or [])
                lines.append(f"    - `{ins.get('address')}` `{ins.get('mnemonic')}` {args}")
        if proc.get("pseudocode"):
            lines.append(
                f"  - Pseudocode chars: `{proc.get('pseudocode_length')}`, "
                f"truncated=`{proc.get('pseudocode_truncated')}`"
            )
            lines.append("    ```text")
            for line in str(proc["pseudocode"]).splitlines()[:40]:
                lines.append("    " + line[:220])
            lines.append("    ```")

    if compact["strings"]:
        lines.append(section("Strings"))
    for row in compact["strings"]:
        lines.append(f"- `{row.get('address')}` {q(row.get('value'), 260)}")
        for ref in row.get("xrefs_to") or []:
            proc = ref.get("procedure_name") or ""
            lines.append(f"  - xref `{ref.get('from')}` in `{ref.get('procedure')}` {q(proc, 220)}")

    if compact["names"]:
        lines.append(section("Names"))
    for row in compact["names"]:
        label = row.get("demangled") or row.get("name") or ""
        lines.append(f"- `{row.get('address')}` {q(label, 260)}")
        if row.get("demangled") and row.get("name") != row.get("demangled"):
            lines.append(f"  - Raw: `{shorten(row.get('name'), 260)}`")

    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    args = parse_args()
    try:
        data = load_snapshot(args.snapshot)
        compact = build_compact(data, args)
        if args.format == "json":
            text = json.dumps(compact, indent=2, sort_keys=True) + "\n"
        else:
            text = render_markdown(compact)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
