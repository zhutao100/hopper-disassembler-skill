# Mach-O Addressing and Offset Mapping

Use this reference whenever a Hopper address must be reconciled with file bytes, `otool` output, `dd`, a hex editor, or a universal Mach-O container.

## Address Spaces

|Term|Definition|Where it appears|
|-|-|-|
|Virtual address|Mach-O VM address in a segment/section|Hopper, disassembly, symbols.|
|File offset|Offset into a thin Mach-O slice|Mach-O segment `fileoff`, hex editors on thin files.|
|Fat-file offset|Offset into the universal container|Hex editors on universal binaries.|
|Slide|Runtime ASLR adjustment|Debugger/runtime addresses.|
|Load address|Runtime base plus slide|`lldb`, crash logs, `atos` workflows.|

For static Hopper work, start with virtual address to file offset:

```text
slice_relative_offset = segment.fileoff + (virtual_address - segment.vmaddr)
fat_file_offset = fat_arch.offset + slice_relative_offset
```

This applies only when the virtual address falls within a segment’s mapped file range. Zero-fill areas such as part of `__bss` may have VM space without corresponding bytes.

## Use the Script

Map both ways:

```bash
scripts/macho_address_map.py --arch arm64 --address 0x100003f50 /path/to/target
scripts/macho_address_map.py --arch arm64 --offset 0x3f50 /path/to/target
scripts/macho_address_map.py --queries-only --arch arm64 --address 0x100003f50 /path/to/target
```

JSON output for automation:

```bash
scripts/macho_address_map.py --format json --arch arm64 --address 0x100003f50 /path/to/target > /tmp/address-map.json
scripts/macho_address_map.py --format json --queries-only --arch arm64 --address 0x100003f50 /path/to/target > /tmp/address-map.compact.json
```

For universal files, specify `--arch` unless you intentionally want all slices:

```bash
scripts/macho_address_map.py --arch arm64e --address 0x100003f50 /path/to/UniversalBinary
```

## What the Script Parses

`macho_address_map.py` is dependency-free and parses:

- Fat/universal headers, including big-endian fat magic.
- 32-bit and 64-bit Mach-O headers.
- `LC_SEGMENT` and `LC_SEGMENT_64` segments/sections.
- `LC_CODE_SIGNATURE` data offset and size.
- `LC_DYLD_CHAINED_FIXUPS` data offset and size.
- `LC_BUILD_VERSION` platform/minimum OS/SDK.
- `LC_VERSION_MIN_MACOSX` for older binaries.

It reports:

- CPU type/subtype and inferred architecture name.
- Slice offset, size, and alignment.
- Segments and sections with VM/file ranges.
- Address-to-offset and offset-to-address matches.
- Signature/fixup/build-version metadata when present.

## Hopper Address to Runtime Address

Hopper static addresses are not always runtime addresses. For crash logs or `lldb`:

```text
runtime_address = static_vm_address + slide
static_vm_address = runtime_address - slide
```

Sources for slide:

- Crash report binary images section.
- `lldb image list -o -f`.
- Dyld logs or process maps in authorized contexts.

Use `atos` with correct architecture and load address:

```bash
atos -arch arm64 -o /path/to/target -l 0xLOAD_ADDRESS 0xRUNTIME_ADDRESS
```

When in doubt, write down all three: Hopper VA, runtime address, and slide.

## Common Pitfalls

- Applying a thin-slice offset directly to a universal file. Add the fat slice offset first.
- Assuming `arm64` and `arm64e` slices have identical code addresses or offsets.
- Treating a Hopper address as an unslid runtime address in crash-log analysis.
- Patching bytes in `__LINKEDIT` or code-signature data accidentally because an absolute offset was confused with a slice offset.
- Ignoring alignment and size changes after Hopper produces a new executable.
- Assuming `otool -l` ordering implies all VM ranges map to file-backed bytes.

## Offset Evidence Record

For each byte-level statement, record:

```text
File: /path/to/copied/target
Architecture: arm64
Hopper VA: 0x...
Segment: __TEXT
Section: __text
Slice offset: 0x...
Universal absolute offset: 0x... or n/a
Original bytes: ...
Modified bytes: ...
Tool output: macho_address_map.py command and result path
```
