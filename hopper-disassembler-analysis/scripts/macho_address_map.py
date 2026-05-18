#!/usr/bin/env python3
"""Map Mach-O virtual addresses to file offsets and summarize slices/load commands.

This parser is intentionally small and dependency-free. It handles common
64-bit Mach-O and universal/fat files used by modern macOS binaries. It is not a
replacement for `otool`, `vtool`, or Hopper; use it as a fast sanity check when
planning Hopper analysis or authorized byte-level work.
"""

from __future__ import annotations

import argparse
import json
import struct
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

FAT_MAGIC = 0xCAFEBABE
FAT_MAGIC_64 = 0xCAFEBABF
MH_MAGIC = 0xFEEDFACE
MH_CIGAM = 0xCEFAEDFE
MH_MAGIC_64 = 0xFEEDFACF
MH_CIGAM_64 = 0xCFFAEDFE

CPU_ARCH_ABI64 = 0x01000000
CPU_TYPE_X86 = 7
CPU_TYPE_ARM = 12
CPU_TYPE_X86_64 = CPU_TYPE_X86 | CPU_ARCH_ABI64
CPU_TYPE_ARM64 = CPU_TYPE_ARM | CPU_ARCH_ABI64
CPU_SUBTYPE_MASK = 0x00FFFFFF
CPU_SUBTYPE_ARM64E = 2

LC_SEGMENT = 0x1
LC_SYMTAB = 0x2
LC_DYSYMTAB = 0xB
LC_LOAD_DYLIB = 0xC
LC_ID_DYLIB = 0xD
LC_LOAD_DYLINKER = 0xE
LC_UUID = 0x1B
LC_CODE_SIGNATURE = 0x1D
LC_SEGMENT_64 = 0x19
LC_VERSION_MIN_MACOSX = 0x24
LC_MAIN = 0x80000028
LC_BUILD_VERSION = 0x32
LC_DYLD_CHAINED_FIXUPS = 0x80000034
LC_DYLD_EXPORTS_TRIE = 0x80000033

LOAD_COMMAND_NAMES = {
    LC_SEGMENT: "LC_SEGMENT",
    LC_SYMTAB: "LC_SYMTAB",
    LC_DYSYMTAB: "LC_DYSYMTAB",
    LC_LOAD_DYLIB: "LC_LOAD_DYLIB",
    LC_ID_DYLIB: "LC_ID_DYLIB",
    LC_LOAD_DYLINKER: "LC_LOAD_DYLINKER",
    LC_UUID: "LC_UUID",
    LC_CODE_SIGNATURE: "LC_CODE_SIGNATURE",
    LC_SEGMENT_64: "LC_SEGMENT_64",
    LC_VERSION_MIN_MACOSX: "LC_VERSION_MIN_MACOSX",
    LC_MAIN: "LC_MAIN",
    LC_BUILD_VERSION: "LC_BUILD_VERSION",
    LC_DYLD_CHAINED_FIXUPS: "LC_DYLD_CHAINED_FIXUPS",
    LC_DYLD_EXPORTS_TRIE: "LC_DYLD_EXPORTS_TRIE",
}

PLATFORMS = {
    1: "MACOS",
    2: "IOS",
    3: "TVOS",
    4: "WATCHOS",
    5: "BRIDGEOS",
    6: "MACCATALYST",
    7: "IOSSIMULATOR",
    8: "TVOSSIMULATOR",
    9: "WATCHOSSIMULATOR",
    10: "DRIVERKIT",
    11: "XROS",
    12: "XROSSIMULATOR",
}


@dataclass
class Section:
    sectname: str
    segname: str
    address: int
    size: int
    offset: int
    flags: int


@dataclass
class Segment:
    name: str
    vmaddr: int
    vmsize: int
    fileoff: int
    filesize: int
    initprot: int
    maxprot: int
    sections: list[Section] = field(default_factory=list)

    def address_to_offset(self, address: int) -> int | None:
        if not (self.vmaddr <= address < self.vmaddr + self.vmsize):
            return None
        delta = address - self.vmaddr
        if delta >= self.filesize:
            return None
        return self.fileoff + delta

    def offset_to_address(self, offset: int) -> int | None:
        if not (self.fileoff <= offset < self.fileoff + self.filesize):
            return None
        return self.vmaddr + (offset - self.fileoff)


@dataclass
class Slice:
    arch: str
    cputype: int
    cpusubtype: int
    offset: int
    size: int
    align: int | None = None
    bits: int = 64
    endian: Literal["little", "big"] = "little"
    filetype: int | None = None
    ncmds: int | None = None
    flags: int | None = None
    segments: list[Segment] = field(default_factory=list)
    build_versions: list[dict[str, Any]] = field(default_factory=list)
    version_min: list[dict[str, Any]] = field(default_factory=list)
    code_signature: dict[str, int] | None = None
    chained_fixups: dict[str, int] | None = None
    warnings: list[str] = field(default_factory=list)


class MachOError(ValueError):
    pass


def parse_int(text: str) -> int:
    return int(text, 0)


def hex_int(value: int | None) -> str | None:
    return None if value is None else f"0x{value:x}"


def read_c_string(raw: bytes) -> str:
    return raw.split(b"\0", 1)[0].decode("utf-8", errors="replace")


def arch_name(cputype: int, cpusubtype: int) -> str:
    subtype = cpusubtype & CPU_SUBTYPE_MASK
    if cputype == CPU_TYPE_ARM64:
        return "arm64e" if subtype == CPU_SUBTYPE_ARM64E else "arm64"
    if cputype == CPU_TYPE_X86_64:
        return "x86_64"
    if cputype == CPU_TYPE_ARM:
        return "arm"
    if cputype == CPU_TYPE_X86:
        return "i386"
    return f"cpu{cputype:x}.sub{subtype:x}"


def version_text(encoded: int) -> str:
    return f"{(encoded >> 16) & 0xffff}.{(encoded >> 8) & 0xff}.{encoded & 0xff}"


def require_range(data: bytes, start: int, size: int, label: str) -> bytes:
    end = start + size
    if start < 0 or size < 0 or end > len(data):
        raise MachOError(f"{label} extends beyond file: offset=0x{start:x} size=0x{size:x}")
    return data[start:end]


def parse_fat(data: bytes) -> list[Slice] | None:
    if len(data) < 8:
        return None
    magic, nfat = struct.unpack_from(">II", data, 0)
    if magic not in {FAT_MAGIC, FAT_MAGIC_64}:
        return None
    record_size = 32 if magic == FAT_MAGIC_64 else 20
    pos = 8
    slices: list[Slice] = []
    for index in range(nfat):
        raw = require_range(data, pos, record_size, f"fat_arch[{index}]")
        if magic == FAT_MAGIC_64:
            cputype, cpusubtype, offset, size, align, _reserved = struct.unpack(">IIQQII", raw)
        else:
            cputype, cpusubtype, offset, size, align = struct.unpack(">IIIII", raw)
        slices.append(
            Slice(
                arch=arch_name(cputype, cpusubtype),
                cputype=cputype,
                cpusubtype=cpusubtype,
                offset=offset,
                size=size,
                align=align,
            )
        )
        pos += record_size
    return slices


def detect_thin_header(slice_data: bytes) -> tuple[str, bool]:
    if len(slice_data) < 4:
        raise MachOError("slice is too small for a Mach-O header")
    little = struct.unpack_from("<I", slice_data, 0)[0]
    big = struct.unpack_from(">I", slice_data, 0)[0]
    if little in {MH_MAGIC, MH_MAGIC_64}:
        return "<", little == MH_MAGIC_64
    if big in {MH_CIGAM, MH_CIGAM_64}:
        return ">", big == MH_CIGAM_64
    raise MachOError(f"unsupported Mach-O magic: little=0x{little:x} big=0x{big:x}")


def parse_sections_64(raw: bytes, count: int, endian: str) -> list[Section]:
    sections: list[Section] = []
    section_size = 80
    for index in range(count):
        start = index * section_size
        if start + section_size > len(raw):
            break
        chunk = raw[start : start + section_size]
        sectname = read_c_string(chunk[0:16])
        segname = read_c_string(chunk[16:32])
        addr, size, offset, _align, _reloff, _nreloc, flags, _r1, _r2, _r3 = struct.unpack_from(
            endian + "QQIIIIIIII", chunk, 32
        )
        sections.append(
            Section(
                sectname=sectname,
                segname=segname,
                address=addr,
                size=size,
                offset=offset,
                flags=flags,
            )
        )
    return sections


def parse_sections_32(raw: bytes, count: int, endian: str) -> list[Section]:
    sections: list[Section] = []
    section_size = 68
    for index in range(count):
        start = index * section_size
        if start + section_size > len(raw):
            break
        chunk = raw[start : start + section_size]
        sectname = read_c_string(chunk[0:16])
        segname = read_c_string(chunk[16:32])
        addr, size, offset, _align, _reloff, _nreloc, flags, _r1, _r2 = struct.unpack_from(
            endian + "IIIIIIIII", chunk, 32
        )
        sections.append(
            Section(
                sectname=sectname,
                segname=segname,
                address=addr,
                size=size,
                offset=offset,
                flags=flags,
            )
        )
    return sections


def parse_thin(data: bytes, sl: Slice) -> None:
    slice_data = require_range(data, sl.offset, sl.size, f"slice {sl.arch}")
    endian, is64 = detect_thin_header(slice_data)
    sl.endian = "little" if endian == "<" else "big"
    sl.bits = 64 if is64 else 32
    header_size = 32 if is64 else 28
    header = require_range(slice_data, 0, header_size, "Mach-O header")
    if is64:
        _magic, cputype, cpusubtype, filetype, ncmds, sizeofcmds, flags, _reserved = struct.unpack(
            endian + "IiiIIIII", header
        )
    else:
        _magic, cputype, cpusubtype, filetype, ncmds, sizeofcmds, flags = struct.unpack(
            endian + "IiiIIII", header
        )
    sl.cputype = cputype & 0xFFFFFFFF
    sl.cpusubtype = cpusubtype & 0xFFFFFFFF
    sl.arch = arch_name(sl.cputype, sl.cpusubtype)
    sl.filetype = filetype
    sl.ncmds = ncmds
    sl.flags = flags

    commands = require_range(slice_data, header_size, sizeofcmds, "load commands")
    pos = 0
    for index in range(ncmds):
        if pos + 8 > len(commands):
            sl.warnings.append(f"load command {index} header exceeds sizeofcmds")
            break
        cmd, cmdsize = struct.unpack_from(endian + "II", commands, pos)
        if cmdsize < 8 or pos + cmdsize > len(commands):
            sl.warnings.append(f"load command {index} has invalid size {cmdsize}")
            break
        raw = commands[pos : pos + cmdsize]
        if cmd == LC_SEGMENT_64 and cmdsize >= 72:
            segname = read_c_string(raw[8:24])
            vmaddr, vmsize, fileoff, filesize, maxprot, initprot, nsects, flags2 = (
                struct.unpack_from(endian + "QQQQIIII", raw, 24)
            )
            section_bytes = raw[72:]
            sections = parse_sections_64(section_bytes, nsects, endian)
            sl.segments.append(
                Segment(
                    name=segname,
                    vmaddr=vmaddr,
                    vmsize=vmsize,
                    fileoff=fileoff,
                    filesize=filesize,
                    maxprot=maxprot,
                    initprot=initprot,
                    sections=sections,
                )
            )
        elif cmd == LC_SEGMENT and cmdsize >= 56:
            segname = read_c_string(raw[8:24])
            vmaddr, vmsize, fileoff, filesize, maxprot, initprot, nsects, flags2 = (
                struct.unpack_from(endian + "IIIIIIII", raw, 24)
            )
            section_bytes = raw[56:]
            sections = parse_sections_32(section_bytes, nsects, endian)
            sl.segments.append(
                Segment(
                    name=segname,
                    vmaddr=vmaddr,
                    vmsize=vmsize,
                    fileoff=fileoff,
                    filesize=filesize,
                    maxprot=maxprot,
                    initprot=initprot,
                    sections=sections,
                )
            )
        elif cmd == LC_BUILD_VERSION and cmdsize >= 24:
            platform, minos, sdk, ntools = struct.unpack_from(endian + "IIII", raw, 8)
            sl.build_versions.append(
                {
                    "platform": PLATFORMS.get(platform, str(platform)),
                    "minos": version_text(minos),
                    "sdk": version_text(sdk),
                    "ntools": ntools,
                }
            )
        elif cmd == LC_VERSION_MIN_MACOSX and cmdsize >= 16:
            version, sdk = struct.unpack_from(endian + "II", raw, 8)
            sl.version_min.append(
                {"platform": "MACOS", "version": version_text(version), "sdk": version_text(sdk)}
            )
        elif cmd == LC_CODE_SIGNATURE and cmdsize >= 16:
            dataoff, datasize = struct.unpack_from(endian + "II", raw, 8)
            sl.code_signature = {
                "dataoff": dataoff,
                "datasize": datasize,
                "absolute_dataoff": sl.offset + dataoff,
            }
        elif cmd == LC_DYLD_CHAINED_FIXUPS and cmdsize >= 16:
            dataoff, datasize = struct.unpack_from(endian + "II", raw, 8)
            sl.chained_fixups = {
                "dataoff": dataoff,
                "datasize": datasize,
                "absolute_dataoff": sl.offset + dataoff,
            }
        pos += cmdsize


def parse_file(path: Path) -> tuple[bool, list[Slice]]:
    data = path.read_bytes()
    fat = parse_fat(data)
    if fat is None:
        sl = Slice(arch="unknown", cputype=0, cpusubtype=0, offset=0, size=len(data), align=None)
        parse_thin(data, sl)
        return False, [sl]
    for sl in fat:
        parse_thin(data, sl)
    return True, fat


def serialize_section(section: Section) -> dict[str, Any]:
    return {
        "sectname": section.sectname,
        "segname": section.segname,
        "address": hex_int(section.address),
        "size": hex_int(section.size),
        "offset": hex_int(section.offset),
        "flags": hex_int(section.flags),
    }


def serialize_segment(segment: Segment, include_sections: bool = False) -> dict[str, Any]:
    row: dict[str, Any] = {
        "name": segment.name,
        "vmaddr": hex_int(segment.vmaddr),
        "vmsize": hex_int(segment.vmsize),
        "fileoff": hex_int(segment.fileoff),
        "filesize": hex_int(segment.filesize),
        "maxprot": hex_int(segment.maxprot),
        "initprot": hex_int(segment.initprot),
    }
    if include_sections:
        row["sections"] = [serialize_section(section) for section in segment.sections]
    return row


def serialize_slice(sl: Slice, include_sections: bool = False) -> dict[str, Any]:
    return {
        "arch": sl.arch,
        "cputype": hex_int(sl.cputype),
        "cpusubtype": hex_int(sl.cpusubtype),
        "slice_offset": hex_int(sl.offset),
        "slice_size": hex_int(sl.size),
        "align": sl.align,
        "bits": sl.bits,
        "endian": sl.endian,
        "filetype": hex_int(sl.filetype),
        "ncmds": sl.ncmds,
        "flags": hex_int(sl.flags),
        "build_versions": sl.build_versions,
        "version_min": sl.version_min,
        "code_signature": (
            {key: hex_int(value) for key, value in sl.code_signature.items()}
            if sl.code_signature
            else None
        ),
        "chained_fixups": (
            {key: hex_int(value) for key, value in sl.chained_fixups.items()}
            if sl.chained_fixups
            else None
        ),
        "segments": [
            serialize_segment(segment, include_sections=include_sections) for segment in sl.segments
        ],
        "warnings": sl.warnings,
    }


def select_slices(slices: list[Slice], arch: str | None) -> list[Slice]:
    if not arch or arch == "all":
        return slices
    selected = [sl for sl in slices if sl.arch == arch]
    if not selected:
        available = ", ".join(sl.arch for sl in slices)
        raise MachOError(f"architecture {arch!r} not found; available: {available}")
    return selected


def map_address(slices: list[Slice], address: int, arch: str | None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for sl in select_slices(slices, arch):
        for segment in sl.segments:
            offset = segment.address_to_offset(address)
            if offset is None:
                continue
            rows.append(
                {
                    "arch": sl.arch,
                    "address": hex_int(address),
                    "segment": segment.name,
                    "slice_relative_offset": hex_int(offset),
                    "absolute_file_offset": hex_int(sl.offset + offset),
                    "slice_offset": hex_int(sl.offset),
                }
            )
    return rows


def map_offset(
    slices: list[Slice], offset: int, arch: str | None, slice_relative: bool
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for sl in select_slices(slices, arch):
        relative = offset if slice_relative else offset - sl.offset
        if relative < 0 or relative >= sl.size:
            continue
        for segment in sl.segments:
            address = segment.offset_to_address(relative)
            if address is None:
                continue
            rows.append(
                {
                    "arch": sl.arch,
                    "address": hex_int(address),
                    "segment": segment.name,
                    "slice_relative_offset": hex_int(relative),
                    "absolute_file_offset": hex_int(sl.offset + relative),
                    "slice_offset": hex_int(sl.offset),
                }
            )
    return rows


def render_markdown(payload: dict[str, Any]) -> str:
    lines: list[str] = ["# Mach-O Address Map", ""]
    lines.append(f"- Path: `{payload['path']}`")
    lines.append(f"- Universal: `{payload['universal']}`")
    lines.append("")
    lines.append("## Slices")
    lines.append("")
    for sl in payload["slices"]:
        lines.append(f"### `{sl['arch']}`")
        lines.append(f"- Slice offset: `{sl['slice_offset']}`")
        lines.append(f"- Slice size: `{sl['slice_size']}`")
        lines.append(f"- Bits/endian: `{sl['bits']}` / `{sl['endian']}`")
        if sl.get("build_versions"):
            lines.append(f"- Build versions: `{json.dumps(sl['build_versions'], sort_keys=True)}`")
        if sl.get("version_min"):
            lines.append(f"- Minimum versions: `{json.dumps(sl['version_min'], sort_keys=True)}`")
        if sl.get("code_signature"):
            lines.append(f"- Code signature: `{json.dumps(sl['code_signature'], sort_keys=True)}`")
        if sl.get("chained_fixups"):
            lines.append(f"- Chained fixups: `{json.dumps(sl['chained_fixups'], sort_keys=True)}`")
        lines.append("- Segments:")
        for segment in sl["segments"]:
            lines.append(
                f"  - `{segment['name']}` vm `{segment['vmaddr']}`+`{segment['vmsize']}` "
                f"file `{segment['fileoff']}`+`{segment['filesize']}`"
            )
        if sl.get("warnings"):
            lines.append("- Warnings:")
            for warning in sl["warnings"]:
                lines.append(f"  - {warning}")
        lines.append("")
    if payload.get("queries"):
        lines.append("## Queries")
        lines.append("")
        for query in payload["queries"]:
            lines.append(f"### {query['kind']} `{query['input']}`")
            if not query["matches"]:
                lines.append("- No mapped segment found.")
            for match in query["matches"]:
                lines.append(
                    f"- `{match['arch']}` `{match['segment']}` address `{match['address']}` "
                    f"slice offset `{match['slice_relative_offset']}` absolute offset `{match['absolute_file_offset']}`"
                )
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", type=Path, help="Mach-O thin or universal file")
    parser.add_argument(
        "--arch",
        default=None,
        help="Architecture to query, for example arm64, arm64e, x86_64, or all",
    )
    parser.add_argument(
        "--address",
        action="append",
        default=[],
        help="Virtual address to map to file offset. May be repeated.",
    )
    parser.add_argument(
        "--offset",
        action="append",
        default=[],
        help="File offset to map to a virtual address. May be repeated.",
    )
    parser.add_argument(
        "--slice-relative",
        action="store_true",
        help="Interpret --offset values as offsets relative to the selected slice instead of absolute file offsets.",
    )
    parser.add_argument(
        "--include-sections", action="store_true", help="Include section rows in JSON output."
    )
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    parser.add_argument(
        "-o", "--output", type=Path, help="Write output to this path instead of stdout"
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        universal, slices = parse_file(args.target.expanduser())
        serialized = [serialize_slice(sl, include_sections=args.include_sections) for sl in slices]
        queries: list[dict[str, Any]] = []
        for value in args.address:
            address = parse_int(value)
            queries.append(
                {
                    "kind": "address",
                    "input": value,
                    "matches": map_address(slices, address, args.arch),
                }
            )
        for value in args.offset:
            offset = parse_int(value)
            queries.append(
                {
                    "kind": "slice-relative offset" if args.slice_relative else "absolute offset",
                    "input": value,
                    "matches": map_offset(slices, offset, args.arch, args.slice_relative),
                }
            )
        payload = {
            "path": str(args.target.expanduser()),
            "universal": universal,
            "slices": serialized,
            "queries": queries,
        }
    except (OSError, MachOError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    text = (
        json.dumps(payload, indent=2, sort_keys=True) + "\n"
        if args.format == "json"
        else render_markdown(payload)
    )
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
