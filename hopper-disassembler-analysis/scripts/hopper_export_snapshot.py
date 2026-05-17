#!/usr/bin/env python3
"""Export a bounded Hopper document snapshot as JSON.

Run this file from Hopper with:

    hopper -l Mach-O -e /path/to/binary -Y hopper_export_snapshot.py

Configuration is passed through environment variables because Hopper's `-Y`
launcher does not forward script arguments.
"""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

VERSION = "0.1.0"


def env_flag(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_int(name: str, default: int) -> int:
    value = os.environ.get(name)
    if value is None or not value.strip():
        return default
    try:
        return max(0, int(value, 10))
    except ValueError:
        return default


def safe_call(default: Any, func: Any, *args: Any) -> Any:
    try:
        return func(*args)
    except Exception:
        return default


def safe_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    try:
        return str(value)
    except Exception:
        return default


def to_hex(value: Any) -> str | None:
    try:
        return f"0x{int(value):x}"
    except Exception:
        return None


def truncate(text: str, limit: int) -> str:
    if limit <= 0 or len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


def tag_names(owner: Any) -> list[str]:
    tags = safe_call([], owner.getTagList)
    result: list[str] = []
    for tag in tags or []:
        name = safe_call(None, tag.getName)
        if name:
            result.append(safe_text(name))
    return result


def local_variables(procedure: Any) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for variable in safe_call([], procedure.getLocalVariableList) or []:
        result.append(
            {
                "name": safe_text(safe_call("", variable.name)),
                "displacement": safe_call(None, variable.displacement),
            }
        )
    return result


def call_refs(document: Any, procedure: Any, direction: str, max_refs: int) -> list[dict[str, Any]]:
    if max_refs == 0:
        return []
    getter = procedure.getAllCallees if direction == "callees" else procedure.getAllCallers
    refs = safe_call([], getter) or []
    result: list[dict[str, Any]] = []
    for ref in refs[:max_refs]:
        from_address = safe_call(None, ref.fromAddress)
        to_address = safe_call(None, ref.toAddress)
        result.append(
            {
                "from": to_hex(from_address),
                "to": to_hex(to_address),
                "to_name": safe_text(safe_call(None, document.getNameAtAddress, to_address)),
                "type": safe_call(None, ref.type),
            }
        )
    return result


def instruction_rows(
    segment: Any, start: Any, end: Any, max_instructions: int
) -> list[dict[str, Any]]:
    if max_instructions == 0:
        return []

    rows: list[dict[str, Any]] = []
    try:
        cursor = int(start)
        stop = int(end)
    except Exception:
        return rows

    while cursor < stop and len(rows) < max_instructions:
        instruction = safe_call(None, segment.getInstructionAtAddress, cursor)
        if instruction is None:
            length = safe_call(1, segment.getObjectLength, cursor)
            try:
                cursor += max(1, int(length))
            except Exception:
                cursor += 1
            continue

        arg_count = safe_call(0, instruction.getArgumentCount)
        formatted_args: list[str] = []
        raw_args: list[str] = []
        for index in range(int(arg_count or 0)):
            formatted_args.append(safe_text(safe_call("", instruction.getFormattedArgument, index)))
            raw_args.append(safe_text(safe_call("", instruction.getRawArgument, index)))

        length = safe_call(1, instruction.getInstructionLength)
        rows.append(
            {
                "address": to_hex(cursor),
                "mnemonic": safe_text(safe_call("", instruction.getInstructionString)),
                "formatted_args": formatted_args,
                "raw_args": raw_args,
                "length": length,
                "conditional_jump": bool(safe_call(False, instruction.isAConditionalJump)),
                "unconditional_jump": bool(safe_call(False, instruction.isAnInconditionalJump)),
                "comment": safe_text(safe_call("", segment.getCommentAtAddress, cursor)),
                "inline_comment": safe_text(
                    safe_call("", segment.getInlineCommentAtAddress, cursor)
                ),
            }
        )
        try:
            cursor += max(1, int(length))
        except Exception:
            cursor += 1

    return rows


def basic_blocks(
    procedure: Any, segment: Any, max_blocks: int, max_instructions: int
) -> list[dict[str, Any]]:
    if max_blocks == 0:
        return []

    count = safe_call(0, procedure.getBasicBlockCount)
    rows: list[dict[str, Any]] = []
    for index in range(min(int(count or 0), max_blocks)):
        block = safe_call(None, procedure.getBasicBlock, index)
        if block is None:
            continue
        successor_count = safe_call(0, block.getSuccessorCount)
        successors: list[str | None] = []
        for successor_index in range(int(successor_count or 0)):
            successors.append(
                to_hex(safe_call(None, block.getSuccessorAddressAtIndex, successor_index))
            )
        start = safe_call(None, block.getStartingAddress)
        end = safe_call(None, block.getEndingAddress)
        rows.append(
            {
                "start": to_hex(start),
                "end": to_hex(end),
                "successors": successors,
                "tags": tag_names(block),
                "instructions": instruction_rows(segment, start, end, max_instructions),
            }
        )
    return rows


def collect_segments(document: Any) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, segment in enumerate(safe_call([], document.getSegmentsList) or []):
        sections: list[dict[str, Any]] = []
        for section in safe_call([], segment.getSectionsList) or []:
            sections.append(
                {
                    "name": safe_text(safe_call("", section.getName)),
                    "start": to_hex(safe_call(None, section.getStartingAddress)),
                    "length": safe_call(None, section.getLength),
                    "flags": safe_call(None, section.getFlags),
                }
            )
        rows.append(
            {
                "index": index,
                "name": safe_text(safe_call("", segment.getName)),
                "start": to_hex(safe_call(None, segment.getStartingAddress)),
                "length": safe_call(None, segment.getLength),
                "file_offset": safe_call(None, segment.getFileOffset),
                "section_count": safe_call(None, segment.getSectionCount),
                "sections": sections,
            }
        )
    return rows


def collect_strings(
    document: Any, max_strings: int, max_string_length: int
) -> tuple[list[dict[str, Any]], bool]:
    rows: list[dict[str, Any]] = []
    truncated = False
    for segment in safe_call([], document.getSegmentsList) or []:
        segment_name = safe_text(safe_call("", segment.getName))
        for value, address in safe_call([], segment.getStringsList) or []:
            if len(rows) >= max_strings:
                truncated = True
                return rows, truncated
            text = safe_text(value)
            rows.append(
                {
                    "address": to_hex(address),
                    "segment": segment_name,
                    "value": truncate(text, max_string_length),
                    "truncated_value": max_string_length > 0 and len(text) > max_string_length,
                }
            )
    return rows, truncated


def collect_names(document: Any, max_names: int) -> tuple[list[dict[str, Any]], bool]:
    rows: list[dict[str, Any]] = []
    truncated = False
    for segment in safe_call([], document.getSegmentsList) or []:
        labels = safe_call([], segment.getLabelsList) or []
        addresses = safe_call([], segment.getNamedAddresses) or []
        segment_name = safe_text(safe_call("", segment.getName))
        for name, address in zip(labels, addresses):
            if len(rows) >= max_names:
                truncated = True
                return rows, truncated
            rows.append(
                {
                    "address": to_hex(address),
                    "name": safe_text(name),
                    "segment": segment_name,
                    "demangled": safe_text(
                        safe_call("", segment.getDemangledNameAtAddress, address)
                    ),
                }
            )
    return rows, truncated


def iter_procedures(document: Any) -> list[tuple[Any, Any]]:
    rows: list[tuple[Any, Any]] = []
    for segment in safe_call([], document.getSegmentsList) or []:
        count = safe_call(0, segment.getProcedureCount)
        for index in range(int(count or 0)):
            procedure = safe_call(None, segment.getProcedureAtIndex, index)
            if procedure is not None:
                rows.append((segment, procedure))
    return rows


def collect_procedures(
    document: Any, config: dict[str, int | bool]
) -> tuple[list[dict[str, Any]], int, bool]:
    rows: list[dict[str, Any]] = []
    procedures = iter_procedures(document)
    max_procedures = int(config["max_procedures"])
    truncated = len(procedures) > max_procedures

    for segment, procedure in procedures[:max_procedures]:
        entry = safe_call(None, procedure.getEntryPoint)
        name = safe_text(safe_call("", segment.getNameAtAddress, entry))
        row: dict[str, Any] = {
            "address": to_hex(entry),
            "name": name,
            "demangled": safe_text(safe_call("", segment.getDemangledNameAtAddress, entry)),
            "segment": safe_text(safe_call("", segment.getName)),
            "signature": safe_text(safe_call("", procedure.signatureString)),
            "heap_size": safe_call(None, procedure.getHeapSize),
            "basic_block_count": safe_call(None, procedure.getBasicBlockCount),
            "locals": local_variables(procedure),
            "tags": tag_names(procedure),
            "comment": safe_text(safe_call("", segment.getCommentAtAddress, entry)),
            "inline_comment": safe_text(safe_call("", segment.getInlineCommentAtAddress, entry)),
            "callers": call_refs(document, procedure, "callers", int(config["max_call_refs"])),
            "callees": call_refs(document, procedure, "callees", int(config["max_call_refs"])),
            "basic_blocks": basic_blocks(
                procedure,
                segment,
                int(config["max_basic_blocks"]),
                int(config["max_instructions_per_block"]),
            ),
        }

        if config["include_pseudocode"] and len(rows) < int(config["max_pseudocode_functions"]):
            row["pseudocode"] = safe_text(safe_call(None, procedure.decompile))

        rows.append(row)
    return rows, len(procedures), truncated


def default_output_path(document: Any) -> Path:
    executable_path = safe_text(safe_call("", document.getExecutableFilePath))
    if executable_path:
        stem = Path(executable_path).name
    else:
        stem = safe_text(safe_call("hopper-document", document.getDocumentName), "hopper-document")
    safe_stem = re.sub(r"[^A-Za-z0-9_.-]+", "_", stem).strip("._") or "hopper-document"
    return Path(os.environ.get("TMPDIR", "/tmp")) / f"{safe_stem}.hopper-snapshot.json"


def collect_snapshot(document: Any) -> dict[str, Any]:
    full_export = env_flag("HOPPER_SKILL_FULL_EXPORT", False)
    high_cap = 10**9
    max_procedures = high_cap if full_export else env_int("HOPPER_SKILL_MAX_PROCEDURES", 500)
    max_strings = high_cap if full_export else env_int("HOPPER_SKILL_MAX_STRINGS", 2000)
    max_names = high_cap if full_export else env_int("HOPPER_SKILL_MAX_NAMES", 3000)
    config: dict[str, int | bool] = {
        "max_procedures": max_procedures,
        "max_strings": max_strings,
        "max_names": max_names,
        "max_basic_blocks": env_int("HOPPER_SKILL_MAX_BASIC_BLOCKS", 64),
        "max_instructions_per_block": env_int("HOPPER_SKILL_MAX_INSTRUCTIONS_PER_BLOCK", 8),
        "max_call_refs": env_int("HOPPER_SKILL_MAX_CALL_REFS", 64),
        "max_string_length": env_int("HOPPER_SKILL_MAX_STRING_LENGTH", 4096),
        "include_pseudocode": env_flag("HOPPER_SKILL_INCLUDE_PSEUDOCODE", False),
        "max_pseudocode_functions": env_int("HOPPER_SKILL_MAX_PSEUDOCODE_FUNCTIONS", 20),
    }

    background_active = bool(safe_call(False, document.backgroundProcessActive))
    segments = collect_segments(document)
    strings, strings_truncated = collect_strings(
        document, int(config["max_strings"]), int(config["max_string_length"])
    )
    names, names_truncated = collect_names(document, int(config["max_names"]))
    procedures, total_procedures, procedures_truncated = collect_procedures(document, config)

    return {
        "tool": "hopper-disassembler-analysis/scripts/hopper_export_snapshot.py",
        "version": VERSION,
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "document": {
            "name": safe_text(safe_call("", document.getDocumentName)),
            "executable_path": safe_text(safe_call("", document.getExecutableFilePath)),
            "database_path": safe_text(safe_call("", document.getDatabaseFilePath)),
            "entry_point": to_hex(safe_call(None, document.getEntryPoint)),
            "is_64_bits": bool(safe_call(False, document.is64Bits)),
            "background_analysis_active": background_active,
        },
        "limits": config,
        "capabilities": {
            "pseudocode_included": bool(config["include_pseudocode"]),
            "background_analysis_completed": not background_active,
        },
        "counts": {
            "segments": len(segments),
            "strings_exported": len(strings),
            "names_exported": len(names),
            "procedures_total": total_procedures,
            "procedures_exported": len(procedures),
        },
        "truncated": {
            "strings": strings_truncated,
            "names": names_truncated,
            "procedures": procedures_truncated,
        },
        "segments": segments,
        "strings": strings,
        "names": names,
        "procedures": procedures,
    }


def main() -> int:
    document_class = globals().get("Document")
    if document_class is None:
        print("Hopper Document API is unavailable. Run this script inside Hopper.", file=sys.stderr)
        return 2

    document = document_class.getCurrentDocument()
    if document is None:
        print("No active Hopper document.", file=sys.stderr)
        return 3

    output = Path(os.environ.get("HOPPER_SKILL_EXPORT_PATH") or default_output_path(document))
    output.parent.mkdir(parents=True, exist_ok=True)
    snapshot = collect_snapshot(document)
    output.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    safe_call(None, document.log, f"[hopper-disassembler-analysis] exported snapshot to {output}")
    print(f"hopper snapshot exported: {output}")

    if env_flag("HOPPER_SKILL_CLOSE_AFTER_EXPORT", False):
        safe_call(None, document.closeDocument)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
