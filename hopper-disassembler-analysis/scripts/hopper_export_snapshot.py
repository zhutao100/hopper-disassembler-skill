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
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

VERSION = "0.4.0"

CALL_TYPE_NAMES = {
    0: "none",
    1: "unknown",
    2: "direct",
    3: "objc",
}


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


def env_text(name: str, default: str = "") -> str:
    value = os.environ.get(name)
    if value is None:
        return default
    return value


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


def call_type_name(value: Any) -> str:
    try:
        return CALL_TYPE_NAMES.get(int(value), f"unknown-{value}")
    except Exception:
        return "unknown"


def valid_offset(value: Any) -> bool:
    if value is None or value is False:
        return False
    try:
        return int(value) >= 0
    except Exception:
        return False


def file_offset_for_address(document: Any, address: Any) -> str | None:
    segment = safe_call(None, document.getSegmentAtAddress, address)
    if segment is not None:
        offset = safe_call(None, segment.getFileOffsetForAddress, address)
        if valid_offset(offset):
            return to_hex(offset)

    offset = safe_call(None, document.getFileOffsetFromAddress, address)
    if valid_offset(offset):
        return to_hex(offset)
    return None


def segment_file_offset_for_address(segment: Any, address: Any) -> str | None:
    offset = safe_call(None, segment.getFileOffsetForAddress, address)
    if valid_offset(offset):
        return to_hex(offset)
    return None


def hopper_version() -> str:
    info = globals().get("GlobalInformation")
    if info is None:
        return ""
    return safe_text(safe_call("", info.getHopperVersion))


def truncate(text: str, limit: int) -> str:
    if limit <= 0 or len(text) <= limit:
        return text
    if limit <= 3:
        return text[:limit]
    return text[: limit - 3] + "..."


def bounded_text(text: str, limit: int) -> tuple[str, int, bool]:
    if limit < 0 or len(text) <= limit:
        return text, len(text), False
    if limit == 0:
        return "", len(text), bool(text)
    return truncate(text, limit), len(text), True


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
        type_value = safe_call(None, ref.type)
        result.append(
            {
                "from": to_hex(from_address),
                "from_file_offset": file_offset_for_address(document, from_address),
                "to": to_hex(to_address),
                "to_file_offset": file_offset_for_address(document, to_address),
                "to_name": safe_text(safe_call(None, document.getNameAtAddress, to_address)),
                "type": type_value,
                "type_name": call_type_name(type_value),
            }
        )
    return result


def containing_procedure(document: Any, address: Any) -> dict[str, Any]:
    segment = safe_call(None, document.getSegmentAtAddress, address)
    if segment is None:
        return {}
    procedure = safe_call(None, segment.getProcedureAtAddress, address)
    if procedure is None:
        return {}

    entry = safe_call(None, procedure.getEntryPoint)
    return {
        "procedure": to_hex(entry),
        "procedure_name": safe_text(safe_call("", segment.getNameAtAddress, entry)),
        "procedure_demangled": safe_text(safe_call("", segment.getDemangledNameAtAddress, entry)),
    }


def xrefs_to_address(
    document: Any, address: Any, max_refs: int
) -> tuple[list[dict[str, Any]], bool]:
    if max_refs == 0:
        return [], False

    segment = safe_call(None, document.getSegmentAtAddress, address)
    if segment is None:
        return [], False

    refs = safe_call([], segment.getReferencesOfAddress, address) or []
    rows: list[dict[str, Any]] = []
    for ref in refs[:max_refs]:
        row = {
            "from": to_hex(ref),
            "from_file_offset": file_offset_for_address(document, ref),
            "from_name": safe_text(safe_call("", document.getNameAtAddress, ref)),
        }
        row.update(containing_procedure(document, ref))
        rows.append(row)
    return rows, len(refs) > max_refs


def instruction_rows(
    segment: Any, start: Any, end: Any, max_instructions: int
) -> tuple[list[dict[str, Any]], bool]:
    if max_instructions == 0:
        return [], int(safe_call(0, lambda: end - start)) > 0

    rows: list[dict[str, Any]] = []
    try:
        cursor = int(start)
        stop = int(end)
    except Exception:
        return rows, False

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
                "file_offset": segment_file_offset_for_address(segment, cursor),
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

    return rows, cursor < stop


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
        instructions, instructions_truncated = instruction_rows(
            segment, start, end, max_instructions
        )
        rows.append(
            {
                "start": to_hex(start),
                "start_file_offset": segment_file_offset_for_address(segment, start),
                "end": to_hex(end),
                "end_file_offset": segment_file_offset_for_address(segment, end),
                "successors": successors,
                "tags": tag_names(block),
                "instructions": instructions,
                "instructions_truncated": instructions_truncated,
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
    document: Any, max_strings: int, max_string_length: int, max_xrefs: int
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
            xrefs, xrefs_truncated = xrefs_to_address(document, address, max_xrefs)
            rows.append(
                {
                    "address": to_hex(address),
                    "file_offset": file_offset_for_address(document, address),
                    "segment": segment_name,
                    "value": truncate(text, max_string_length),
                    "truncated_value": max_string_length > 0 and len(text) > max_string_length,
                    "xrefs_to": xrefs,
                    "xrefs_truncated": xrefs_truncated,
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
                    "file_offset": file_offset_for_address(document, address),
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


def procedure_identity(segment: Any, procedure: Any) -> dict[str, Any]:
    entry = safe_call(None, procedure.getEntryPoint)
    return {
        "entry": entry,
        "address": to_hex(entry),
        "name": safe_text(safe_call("", segment.getNameAtAddress, entry)),
        "demangled": safe_text(safe_call("", segment.getDemangledNameAtAddress, entry)),
        "signature": safe_text(safe_call("", procedure.signatureString)),
        "segment": safe_text(safe_call("", segment.getName)),
    }


def compile_optional_regex(pattern: str) -> re.Pattern[str] | None:
    if not pattern:
        return None
    return re.compile(pattern)


def procedure_matches(identity: dict[str, Any], pattern: re.Pattern[str] | None) -> bool:
    if pattern is None:
        return True
    fields = [
        identity.get("address"),
        identity.get("name"),
        identity.get("demangled"),
        identity.get("signature"),
        identity.get("segment"),
    ]
    return any(pattern.search(safe_text(field)) for field in fields)


def collect_procedures(
    document: Any, config: dict[str, Any]
) -> tuple[list[dict[str, Any]], int, int, bool]:
    rows: list[dict[str, Any]] = []
    procedure_pattern = compile_optional_regex(safe_text(config["procedure_pattern"]))
    procedures = iter_procedures(document)
    max_procedures = int(config["max_procedures"])

    matched: list[tuple[Any, Any, dict[str, Any]]] = []
    for segment, procedure in procedures:
        identity = procedure_identity(segment, procedure)
        if procedure_matches(identity, procedure_pattern):
            matched.append((segment, procedure, identity))

    truncated = len(matched) > max_procedures

    for segment, procedure, identity in matched[:max_procedures]:
        entry = identity["entry"]
        basic_block_count = safe_call(None, procedure.getBasicBlockCount)
        row: dict[str, Any] = {
            "address": identity["address"],
            "file_offset": file_offset_for_address(document, entry),
            "name": identity["name"],
            "demangled": identity["demangled"],
            "segment": identity["segment"],
            "signature": identity["signature"],
            "heap_size": safe_call(None, procedure.getHeapSize),
            "basic_block_count": basic_block_count,
            "basic_blocks_truncated": bool(
                int(basic_block_count or 0) > int(config["max_basic_blocks"])
            ),
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
            pseudocode = safe_text(safe_call(None, procedure.decompile))
            bounded, length, pseudocode_truncated = bounded_text(
                pseudocode, int(config["max_pseudocode_chars"])
            )
            row["pseudocode"] = bounded
            row["pseudocode_length"] = length
            row["pseudocode_truncated"] = pseudocode_truncated

        rows.append(row)
    return rows, len(procedures), len(matched), truncated


def default_output_path(document: Any) -> Path:
    executable_path = safe_text(safe_call("", document.getExecutableFilePath))
    if executable_path:
        stem = Path(executable_path).name
    else:
        stem = safe_text(safe_call("hopper-document", document.getDocumentName), "hopper-document")
    safe_stem = re.sub(r"[^A-Za-z0-9_.-]+", "_", stem).strip("._") or "hopper-document"
    return Path(os.environ.get("TMPDIR", "/tmp")) / f"{safe_stem}.hopper-snapshot.json"


def wait_for_analysis(document: Any) -> None:
    if not env_flag("HOPPER_SKILL_WAIT_FOR_ANALYSIS", False):
        return
    safe_call(None, document.log, "[hopper-disassembler-analysis] waiting for background analysis")
    print("waiting for Hopper background analysis to finish")
    safe_call(None, document.waitForBackgroundProcessToEnd)


def save_database(document: Any) -> Path | None:
    save_path = env_text("HOPPER_SKILL_SAVE_DATABASE_PATH").strip()
    if not save_path:
        return None
    path = Path(save_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        document.saveDocumentAt(str(path))
    except Exception as exc:
        print(f"Failed to save Hopper database to {path}: {exc}", file=sys.stderr)
        raise
    safe_call(None, document.log, f"[hopper-disassembler-analysis] saved database to {path}")
    print(f"hopper database saved: {path}")
    return path


def same_existing_file(left: str, right: Path) -> bool:
    if not left:
        return False
    try:
        return Path(left).resolve(strict=True) == right.resolve(strict=True)
    except Exception:
        return False


def database_path_matches(document: Any, database_path: Path) -> bool:
    active_database_path = safe_text(safe_call("", document.getDatabaseFilePath))
    return same_existing_file(active_database_path, database_path)


def find_database_document(document_class: Any, database_path: Path) -> Any:
    documents = []
    current = safe_call(None, document_class.getCurrentDocument)
    if current is not None:
        documents.append(current)
    documents.extend(safe_call([], document_class.getAllDocuments) or [])
    for document in documents:
        if document is not None and database_path_matches(document, database_path):
            return document
    return None


def current_document() -> Any:
    document_class = globals().get("Document")
    if document_class is None:
        return None

    load_path = env_text("HOPPER_SKILL_LOAD_DATABASE_PATH").strip()
    if not load_path:
        return document_class.getCurrentDocument()

    database_path = Path(load_path)
    bootstrap_document = document_class.getCurrentDocument()
    database_document = safe_call(None, document_class.newDocument)
    load_host = database_document or bootstrap_document
    if load_host is None:
        return None
    loaded_document = safe_call(None, load_host.loadDocumentAt, str(database_path))
    deadline = time.monotonic() + 30
    document = loaded_document if loaded_document is not None else load_host
    if document is not None and not database_path_matches(document, database_path):
        document = None
    while document is None and time.monotonic() < deadline:
        document = find_database_document(document_class, database_path)
        if document is None:
            time.sleep(0.25)

    if bootstrap_document is not None and bootstrap_document is not document:
        safe_call(None, bootstrap_document.closeDocument)

    if document is None:
        print(f"Failed to load Hopper database: {database_path}", file=sys.stderr)
        return None
    return document


def collect_snapshot(document: Any) -> dict[str, Any]:
    full_export = env_flag("HOPPER_SKILL_FULL_EXPORT", False)
    high_cap = 10**9
    max_procedures = high_cap if full_export else env_int("HOPPER_SKILL_MAX_PROCEDURES", 500)
    max_strings = high_cap if full_export else env_int("HOPPER_SKILL_MAX_STRINGS", 2000)
    max_names = high_cap if full_export else env_int("HOPPER_SKILL_MAX_NAMES", 3000)
    config: dict[str, Any] = {
        "max_procedures": max_procedures,
        "max_strings": max_strings,
        "max_names": max_names,
        "max_basic_blocks": env_int("HOPPER_SKILL_MAX_BASIC_BLOCKS", 64),
        "max_instructions_per_block": env_int("HOPPER_SKILL_MAX_INSTRUCTIONS_PER_BLOCK", 8),
        "max_call_refs": env_int("HOPPER_SKILL_MAX_CALL_REFS", 64),
        "max_string_xrefs": env_int("HOPPER_SKILL_MAX_STRING_XREFS", 16),
        "max_string_length": env_int("HOPPER_SKILL_MAX_STRING_LENGTH", 4096),
        "include_pseudocode": env_flag("HOPPER_SKILL_INCLUDE_PSEUDOCODE", False),
        "max_pseudocode_functions": env_int("HOPPER_SKILL_MAX_PSEUDOCODE_FUNCTIONS", 20),
        "max_pseudocode_chars": env_int("HOPPER_SKILL_MAX_PSEUDOCODE_CHARS", 20000),
        "procedure_pattern": env_text("HOPPER_SKILL_PROCEDURE_PATTERN"),
    }

    background_active = bool(safe_call(False, document.backgroundProcessActive))
    segments = collect_segments(document)
    strings, strings_truncated = collect_strings(
        document,
        int(config["max_strings"]),
        int(config["max_string_length"]),
        int(config["max_string_xrefs"]),
    )
    names, names_truncated = collect_names(document, int(config["max_names"]))
    procedures, total_procedures, matched_procedures, procedures_truncated = collect_procedures(
        document, config
    )

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
            "hopper_version": hopper_version(),
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
            "procedures_matched": matched_procedures,
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

    document = current_document()
    if document is None:
        print("No active Hopper document.", file=sys.stderr)
        return 3

    output = Path(os.environ.get("HOPPER_SKILL_EXPORT_PATH") or default_output_path(document))
    output.parent.mkdir(parents=True, exist_ok=True)
    wait_for_analysis(document)
    save_database(document)
    snapshot = collect_snapshot(document)
    output.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    safe_call(None, document.log, f"[hopper-disassembler-analysis] exported snapshot to {output}")
    print(f"hopper snapshot exported: {output}")

    if env_flag("HOPPER_SKILL_CLOSE_AFTER_EXPORT", False):
        if env_text("HOPPER_SKILL_LOAD_DATABASE_PATH").strip():
            safe_call(None, document.saveDocument)
        safe_call(None, document.closeDocument)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
