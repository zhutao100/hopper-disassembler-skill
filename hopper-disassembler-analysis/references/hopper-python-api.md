# Hopper Python API Patterns

Use this reference when writing or modifying scripts that run inside Hopper.

## Contents

- [Document Model](#document-model)
- [Script Entrypoint Template](#script-entrypoint-template)
- [Avoid Main-Thread Deadlocks](#avoid-main-thread-deadlocks)
- [Enumerate Segments and Sections](#enumerate-segments-and-sections)
- [Enumerate Procedures](#enumerate-procedures)
- [Walk Basic Blocks and Instructions](#walk-basic-blocks-and-instructions)
- [Strings and Names](#strings-and-names)
- [Cross-References](#cross-references)
- [Addresses and File Offsets](#addresses-and-file-offsets)
- [Comments, Labels, Tags, and Bookmarks](#comments-labels-tags-and-bookmarks)
- [Pseudocode Discipline](#pseudocode-discipline)

## Document Model

Hopper scripts start from the active `Document`.

```python
document = Document.getCurrentDocument()
if document is None:
    print("No active Hopper document.")
    raise SystemExit(1)
```

The public model is:

- `Document`: global file/database state, segments, current cursor, tags, bookmarks, names, reads, writes.
- `Segment`: mapped address range, sections, typed bytes, strings, labels, instructions, references.
- `Section`: named subrange inside a segment.
- `Procedure`: function entry, basic blocks, locals, tags, callers, callees, pseudocode.
- `BasicBlock`: start/end addresses and successor edges.
- `Instruction`: architecture, mnemonic, raw/formatted arguments, length, jump classification.

## Script Entrypoint Template

Use this for custom scripts that run directly through `hopper -Y script.py`:

```python
from __future__ import annotations

from pathlib import Path


def main() -> int:
    document = Document.getCurrentDocument()
    if document is None:
        print("No active Hopper document.")
        return 2

    output = Path("/tmp/hopper-custom-export.txt")
    output.write_text(document.getDocumentName() + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

Hopper injects `Document`, `Segment`, `Procedure`, and related classes into the script's global namespace. If a wrapper dispatches from one Hopper Python script to another file, preserve those globals:

```python
exporter = "/path/to/real_script.py"
with open(exporter, "r", encoding="utf-8") as handle:
    source = handle.read()

namespace = dict(globals())
namespace.update({"__name__": "__main__", "__file__": exporter})
exec(compile(source, exporter, "exec"), namespace)
```

Do not use `runpy.run_path()` for Hopper-dispatched scripts; it starts a new namespace without the injected Hopper API classes.

## Avoid Main-Thread Deadlocks

`waitForBackgroundProcessToEnd()` can deadlock in some batch-script contexts because it dispatches to the main thread while Python holds the interpreter lock. For batch exports, prefer one of these:

```python
if document.backgroundProcessActive():
    document.log("Background analysis still active; export may be incomplete.")
```

or launch with Hopper's `-Y` option, which runs after initial analysis:

```bash
hopper -a -o -f -z -l Mach-O -e /path/to/binary -Y /path/to/script.py
```

Use blocking waits only in a known interactive script where the UI remains responsive.

## Enumerate Segments and Sections

```python
for segment in document.getSegmentsList():
    print(segment.getName(), hex(segment.getStartingAddress()), segment.getLength())
    for section in segment.getSectionsList():
        print("  ", section.getName(), hex(section.getStartingAddress()), section.getLength())
```

Useful methods:

- `segment.getFileOffset()`
- `segment.getFileOffsetForAddress(addr)`
- `segment.getSectionAtAddress(addr)`
- `segment.getTypeAtAddress(addr)`
- `Segment.stringForType(type_value)`

## Enumerate Procedures

Prefer segment-based enumeration; it stays on the public API.

```python
def iter_procedures(document):
    for segment in document.getSegmentsList():
        for index in range(segment.getProcedureCount()):
            procedure = segment.getProcedureAtIndex(index)
            if procedure is not None:
                yield segment, procedure


for segment, procedure in iter_procedures(document):
    entry = procedure.getEntryPoint()
    name = segment.getNameAtAddress(entry) or hex(entry)
    print(name, procedure.signatureString())
```

Procedure detail methods:

- `procedure.getEntryPoint()`
- `procedure.signatureString()`
- `procedure.getHeapSize()`
- `procedure.getLocalVariableList()`
- `procedure.getBasicBlockCount()`
- `procedure.getAllCallers()`
- `procedure.getAllCallees()`
- `procedure.decompile()`

Local variables expose method accessors:

```python
for variable in procedure.getLocalVariableList():
    print(variable.name(), variable.displacement())
```

Call references expose `fromAddress()`, `toAddress()`, and `type()`.

## Walk Basic Blocks and Instructions

```python
for block_index in range(procedure.getBasicBlockCount()):
    block = procedure.getBasicBlock(block_index)
    start = block.getStartingAddress()
    end = block.getEndingAddress()
    successors = [
        block.getSuccessorAddressAtIndex(i)
        for i in range(block.getSuccessorCount())
    ]

    cursor = start
    while cursor < end:
        instruction = segment.getInstructionAtAddress(cursor)
        if instruction is None:
            cursor += 1
            continue
        print(hex(cursor), instruction.getInstructionString())
        cursor += max(1, instruction.getInstructionLength())
```

For each instruction, capture both `getRawArgument(i)` and `getFormattedArgument(i)` when operand interpretation matters.

## Strings and Names

```python
for segment in document.getSegmentsList():
    for value, address in segment.getStringsList():
        print(hex(address), value)

    labels = segment.getLabelsList()
    addresses = segment.getNamedAddresses()
    for label, address in zip(labels, addresses):
        print(hex(address), label, segment.getDemangledNameAtAddress(address))
```

For global lookup:

```python
address = document.getAddressForName("_main")
name = document.getNameAtAddress(address)
```

## Cross-References

```python
segment = document.getSegmentAtAddress(address)
refs_to = segment.getReferencesOfAddress(address)
refs_from = segment.getReferencesFromAddress(address)
```

Corroborate a reference with instruction text and the containing procedure before drawing conclusions.

For string-driven triage, map each reference back to its owning procedure:

```python
for ref in segment.getReferencesOfAddress(string_address):
    ref_segment = document.getSegmentAtAddress(ref)
    procedure = ref_segment.getProcedureAtAddress(ref) if ref_segment else None
    if procedure:
        entry = procedure.getEntryPoint()
        print(hex(ref), hex(entry), document.getNameAtAddress(entry))
```

## Addresses and File Offsets

Use Hopper's mapping APIs before byte-level claims:

```python
segment = document.getSegmentAtAddress(address)
if segment:
    print(segment.getFileOffsetForAddress(address))
print(document.getFileOffsetFromAddress(address))
print(document.getAddressFromFileOffset(file_offset))
```

For universal Mach-O files, Hopper is analyzing one selected thin slice. Account for the FAT slice offset separately before writing to the combined file.

## Comments, Labels, Tags, and Bookmarks

Use conservative write-back. A wrong label can mislead later analysis.

```python
segment.setNameAtAddress(address, "reviewed_function")
segment.setCommentAtAddress(address, "Prefix comment")
segment.setInlineCommentAtAddress(address, "Inline comment")

tag = document.getTagWithName("review")
if tag is None:
    tag = document.buildTag("review")
document.addTagAtAddress(tag, address)
document.setBookmarkName(address, "analysis checkpoint")
```

Prefer batch review in JSON first. `assets/hopper-annotation-payload-template.json` is a starting point for annotation payloads.

For byte-level experiments in a copy, assemble first and write bytes explicitly:

```python
patch = document.assemble("nop", address, 0)
segment.writeBytes(address, bytes(patch))
produced_path = document.produceNewExecutable(True)
print(produced_path)
```

Use this only in a disposable copy or VM workflow, then verify file offsets and code signatures outside Hopper.

## Pseudocode Discipline

`procedure.decompile()` is useful for summaries but is not ground truth. Always cap serialized pseudocode; optimized Rust and Swift generic-heavy functions can produce megabytes from one `decompile()` call. When reporting behavior:

1. Cite procedure address and name.
2. Check assembly and xrefs for the same claim.
3. Check strings/imports and, when available, source code.
4. Mark pseudocode-only conclusions as hypotheses.
