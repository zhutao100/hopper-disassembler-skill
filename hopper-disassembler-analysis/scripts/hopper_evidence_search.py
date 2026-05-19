#!/usr/bin/env python3
"""Search Hopper snapshot JSON for procedures, names, strings, xrefs, and comments."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

Scalar = str | int | float | bool | None


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError("snapshot root must be a JSON object")
    return value


def shorten(value: Any, limit: int = 220) -> str:
    text = "" if value is None else str(value)
    text = text.replace("\r", "\\r").replace("\n", "\\n")
    if len(text) <= limit:
        return text
    if limit <= 3:
        return text[:limit]
    return text[: limit - 3] + "..."


def redact_path(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    home = str(Path.home())
    if value == home:
        return "~"
    if value.startswith(home + "/"):
        return "~/" + value[len(home) + 1 :]
    return value


def row_text(value: Any) -> str:
    if isinstance(value, dict):
        parts: list[str] = []
        for key, item in value.items():
            if key in {"basic_blocks", "instructions", "pseudocode"}:
                continue
            parts.append(str(key))
            parts.append(row_text(item))
        return " ".join(parts)
    if isinstance(value, list):
        return " ".join(row_text(item) for item in value[:64])
    return "" if value is None else str(value)


def pattern_matches(row: Any, patterns: list[re.Pattern[str]]) -> bool:
    text = row_text(row)
    return all(pattern.search(text) for pattern in patterns)


def compact_ref(ref: dict[str, Any]) -> dict[str, Any]:
    return {
        "from": ref.get("from"),
        "to": ref.get("to"),
        "procedure": ref.get("procedure"),
        "from_name": ref.get("from_name") or "",
        "to_name": ref.get("to_name") or "",
        "procedure_name": ref.get("procedure_demangled") or ref.get("procedure_name") or "",
        "type": ref.get("type_name") or ref.get("type") or "",
    }


def compact_procedure(
    row: dict[str, Any], max_refs: int, max_blocks: int, max_instructions: int
) -> dict[str, Any]:
    return {
        "address": row.get("address"),
        "file_offset": row.get("file_offset"),
        "name": row.get("name"),
        "demangled": row.get("demangled"),
        "signature": row.get("signature"),
        "basic_block_count": row.get("basic_block_count"),
        "comment": row.get("comment") or "",
        "inline_comment": row.get("inline_comment") or "",
        "callers": [compact_ref(ref) for ref in (row.get("callers") or [])[:max_refs]],
        "callees": [compact_ref(ref) for ref in (row.get("callees") or [])[:max_refs]],
        "basic_blocks": [
            {
                "start": block.get("start"),
                "end": block.get("end"),
                "successors": block.get("successors") or [],
                "instructions": [
                    {
                        "address": ins.get("address"),
                        "mnemonic": ins.get("mnemonic"),
                        "args": ins.get("formatted_args") or [],
                        "comment": ins.get("comment") or ins.get("inline_comment") or "",
                    }
                    for ins in (block.get("instructions") or [])[:max_instructions]
                ],
            }
            for block in (row.get("basic_blocks") or [])[:max_blocks]
        ],
    }


def compact_string(row: dict[str, Any], max_refs: int, max_chars: int) -> dict[str, Any]:
    return {
        "address": row.get("address"),
        "file_offset": row.get("file_offset"),
        "segment": row.get("segment"),
        "value": shorten(row.get("value") or "", max_chars),
        "xrefs_to": [compact_ref(ref) for ref in (row.get("xrefs_to") or [])[:max_refs]],
    }


def compact_name(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "address": row.get("address"),
        "file_offset": row.get("file_offset"),
        "segment": row.get("segment"),
        "name": row.get("name"),
        "demangled": row.get("demangled"),
    }


def find_matches(
    data: dict[str, Any],
    patterns: list[re.Pattern[str]],
    limit: int,
    max_refs: int,
    max_blocks: int,
    max_instructions: int,
    max_string_chars: int,
) -> dict[str, Any]:
    procedures: list[dict[str, Any]] = []
    strings: list[dict[str, Any]] = []
    names: list[dict[str, Any]] = []
    segments: list[dict[str, Any]] = []

    for row in data.get("procedures") or []:
        if pattern_matches(row, patterns):
            procedures.append(
                compact_procedure(
                    row,
                    max_refs=max_refs,
                    max_blocks=max_blocks,
                    max_instructions=max_instructions,
                )
            )
    for row in data.get("strings") or []:
        if pattern_matches(row, patterns):
            strings.append(compact_string(row, max_refs=max_refs, max_chars=max_string_chars))
    for row in data.get("names") or []:
        if pattern_matches(row, patterns):
            names.append(compact_name(row))
    for row in data.get("segments") or []:
        if pattern_matches(row, patterns):
            segments.append(row)

    document = dict(data.get("document") or {})
    for key in ("executable_path", "database_path"):
        document[key] = redact_path(document.get(key))

    return {
        "document": document,
        "counts": data.get("counts") or {},
        "truncated": data.get("truncated") or {},
        "query": [pattern.pattern for pattern in patterns],
        "matched_total": {
            "procedures": len(procedures),
            "strings": len(strings),
            "names": len(names),
            "segments": len(segments),
        },
        "procedures": procedures[:limit],
        "strings": strings[:limit],
        "names": names[:limit],
        "segments": segments[:limit],
    }


def quote(value: Any, limit: int = 220) -> str:
    return json.dumps(shorten(value, limit), ensure_ascii=True)


def render_refs(refs: list[dict[str, Any]], title: str) -> list[str]:
    if not refs:
        return []
    lines = [f"  - {title}:"]
    for ref in refs:
        location = ref.get("to") or ref.get("from") or ref.get("procedure") or "?"
        name = ref.get("to_name") or ref.get("from_name") or ref.get("procedure_name") or ""
        suffix = f" ({ref.get('type')})" if ref.get("type") else ""
        lines.append(f"    - `{location}` {quote(name, 160)}{suffix}")
    return lines


def render_markdown(result: dict[str, Any]) -> str:
    lines = ["# Hopper Evidence Search", ""]
    document = result.get("document") or {}
    lines.append(f"- Document: `{document.get('name') or ''}`")
    lines.append(f"- Executable: `{document.get('executable_path') or ''}`")
    lines.append(f"- Query: `{', '.join(result.get('query') or [])}`")
    lines.append(
        f"- Matched before caps: `{json.dumps(result.get('matched_total'), sort_keys=True)}`"
    )
    lines.append(f"- Snapshot truncated: `{json.dumps(result.get('truncated'), sort_keys=True)}`")

    if result.get("procedures"):
        lines.extend(["", "## Procedures", ""])
    for row in result.get("procedures") or []:
        label = row.get("demangled") or row.get("name") or ""
        lines.append(f"- `{row.get('address')}` {quote(label, 240)}")
        lines.append(f"  - Signature: `{shorten(row.get('signature'), 240)}`")
        lines.append(f"  - Blocks: `{row.get('basic_block_count')}`")
        if row.get("comment") or row.get("inline_comment"):
            lines.append(
                f"  - Comment: {quote(row.get('comment') or row.get('inline_comment'), 240)}"
            )
        lines.extend(render_refs(row.get("callers") or [], "Callers"))
        lines.extend(render_refs(row.get("callees") or [], "Callees"))
        for block in row.get("basic_blocks") or []:
            lines.append(f"  - Block `{block.get('start')}` -> `{block.get('end')}`")
            for ins in block.get("instructions") or []:
                args = ", ".join(shorten(arg, 80) for arg in ins.get("args") or [])
                lines.append(f"    - `{ins.get('address')}` `{ins.get('mnemonic')}` {args}")

    if result.get("strings"):
        lines.extend(["", "## Strings", ""])
    for row in result.get("strings") or []:
        lines.append(f"- `{row.get('address')}` {quote(row.get('value'), 300)}")
        for ref in row.get("xrefs_to") or []:
            proc = ref.get("procedure_name") or ""
            lines.append(
                f"  - xref `{ref.get('from')}` in `{ref.get('procedure')}` {quote(proc, 200)}"
            )

    if result.get("names"):
        lines.extend(["", "## Names", ""])
    for row in result.get("names") or []:
        label = row.get("demangled") or row.get("name") or ""
        lines.append(f"- `{row.get('address')}` {quote(label, 260)}")
        if row.get("name") and row.get("name") != row.get("demangled"):
            lines.append(f"  - Raw: `{shorten(row.get('name'), 260)}`")

    if result.get("segments"):
        lines.extend(["", "## Segments", ""])
    for row in result.get("segments") or []:
        lines.append(
            f"- `{row.get('name')}` start=`{row.get('start')}` length=`{row.get('length')}`"
        )
    return "\n".join(lines).rstrip() + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshot", type=Path, help="hopper_export_snapshot.py JSON output.")
    parser.add_argument("patterns", nargs="+", help="Regex patterns; all must match a row.")
    parser.add_argument("-o", "--output", type=Path, help="Write output to this path.")
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    parser.add_argument("--ignore-case", action="store_true")
    parser.add_argument("--limit", type=int, default=24, help="Maximum rows per category.")
    parser.add_argument("--max-call-refs", type=int, default=8)
    parser.add_argument("--max-basic-blocks", type=int, default=2)
    parser.add_argument("--max-instructions-per-block", type=int, default=4)
    parser.add_argument("--max-string-chars", type=int, default=260)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    flags = re.IGNORECASE if args.ignore_case else 0
    try:
        patterns = [re.compile(pattern, flags) for pattern in args.patterns]
        data = load_json(args.snapshot)
        result = find_matches(
            data,
            patterns,
            limit=max(0, args.limit),
            max_refs=max(0, args.max_call_refs),
            max_blocks=max(0, args.max_basic_blocks),
            max_instructions=max(0, args.max_instructions_per_block),
            max_string_chars=max(0, args.max_string_chars),
        )
        text = (
            json.dumps(result, indent=2, sort_keys=True) + "\n"
            if args.format == "json"
            else render_markdown(result)
        )
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
