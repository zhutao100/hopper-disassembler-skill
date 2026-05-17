# macOS Binary Analysis Workflow

Use this reference when the target is a macOS app bundle, command-line tool, framework, XPC service, or helper.

## Contents

- [1. Resolve Targets](#1-resolve-targets)
- [2. Capture Baseline Metadata Outside Hopper](#2-capture-baseline-metadata-outside-hopper)
- [3. Export Hopper Evidence](#3-export-hopper-evidence)
- [4. Read and Triage the Snapshot](#4-read-and-triage-the-snapshot)
- [5. Correlate With Source When Available](#5-correlate-with-source-when-available)
- [6. Swift Correlation Gotchas](#6-swift-correlation-gotchas)
- [7. Triage Procedure Sets](#7-triage-procedure-sets)
- [8. Reporting Rules](#8-reporting-rules)
- [9. Modification Boundary](#9-modification-boundary)

## 1. Resolve Targets

For `.app` bundles, identify the main executable:

```bash
app="/Applications/Target.app"
exe="$(/usr/libexec/PlistBuddy -c 'Print :CFBundleExecutable' "$app/Contents/Info.plist")"
target="$app/Contents/MacOS/$exe"
file "$target"
```

Also inspect embedded code:

```bash
find "$app/Contents/MacOS" "$app/Contents/Frameworks" "$app/Contents/XPCServices" "$app/Contents/PlugIns" \
  -maxdepth 4 -type f 2>/dev/null
```

Prioritize:

1. Main executable
2. Login items, helpers, XPC services, and privileged helper tools
3. App-owned frameworks
4. Third-party frameworks only when call evidence points into them

If source points to a framework or helper module, analyze that embedded Mach-O directly. Do not assume the main app executable contains the implementation.

## 2. Capture Baseline Metadata Outside Hopper

Use platform tools for cheap context before opening Hopper:

```bash
codesign -dv --verbose=4 "$target" 2>&1
otool -L "$target"
nm -m "$target" 2>/dev/null | sed -n '1,120p'
strings -a "$target" | grep -E -n "http|keychain|token|license|login|xpc|socket" | sed -n '1,80p'
```

These outputs are not substitutes for Hopper evidence; they guide where to look.

## 3. Export Hopper Evidence

```bash
scripts/run_hopper_export.sh --output /tmp/target.hopper-snapshot.json "$target"
```

For universal binaries on Apple Silicon, prefer ARM64:

```bash
scripts/run_hopper_export.sh --arch arm64 --output /tmp/target.arm64.hopper-snapshot.json "$target"
```

For Apple system binaries that report `arm64e`, select that slice explicitly if auto-selection does not match the task:

```bash
scripts/run_hopper_export.sh --arch arm64e --output /tmp/target.arm64e.hopper-snapshot.json "$target"
```

For focused decompiler review:

```bash
scripts/run_hopper_export.sh \
  --include-pseudocode \
  --max-procedures 50 \
  --output /tmp/target.focused.hopper-snapshot.json \
  "$target"
```

## 4. Read and Triage the Snapshot

Start with metadata and limits:

```bash
python3 - <<'PY' /tmp/target.hopper-snapshot.json
import json, sys
data = json.load(open(sys.argv[1], encoding="utf-8"))
print("document:", data["document"])
print("counts:", data["counts"])
print("truncated:", data["truncated"])
print("segments:", [(s["name"], s["start"], s["length"]) for s in data["segments"]])
PY
```

List candidate procedures:

```bash
python3 - <<'PY' /tmp/target.hopper-snapshot.json
import json, sys
data = json.load(open(sys.argv[1], encoding="utf-8"))
for proc in data["procedures"][:50]:
    callees = ", ".join(ref.get("to_name") or ref.get("to") or "?" for ref in proc["callees"][:5])
    print(proc["address"], proc["name"], "blocks=", proc["basic_block_count"], "callees=", callees)
PY
```

If the snapshot is capped, use it for triage only. Rerun with higher caps, focused pseudocode, or live MCP for claims about functions outside the exported range.

## 5. Correlate With Source When Available

If the user provided source, search source and Hopper artifacts together:

```bash
grep -R --line-number "SymbolOrStringFromHopper" /path/to/source
python3 -m json.tool /tmp/target.hopper-snapshot.json >/dev/null
```

Good correlation signals:

- Function names or Swift/Objective-C selectors match source identifiers.
- String literals map to source constants, log lines, error messages, or UI text.
- String xrefs lead into the expected procedure or a known caller of it.
- Callees, imports, and framework calls match source dependencies.
- Basic-block structure matches source-level branching.
- Hopper call edges support the source-level flow.

Weak correlation signals:

- Pseudocode resembles source but names, strings, or xrefs do not match.
- A string exists but has no reference from the procedure under review.
- A function name is imported or stubbed rather than app-owned.
- A short Swift literal is missing from Hopper's string list; it may be encoded inline.

Recommended source-backed loop:

1. Choose one source function or property with unique names, strings, or external API calls.
2. Locate the containing Mach-O: main executable, app-owned framework, helper, XPC service, or plugin.
3. Export a snapshot with enough `--max-procedures`, `--max-names`, and `--max-strings` to avoid truncating the target area.
4. Search `names` for demangled Swift fragments or Objective-C selectors.
5. Search `strings`; use each string's `xrefs_to` or live MCP `xrefs` to find referencing instructions and containing procedures.
6. Use live MCP `procedure_info` and `procedure_assembly` for the focused function. Use `procedure_pseudo_code` only after checking the basic-block count.
7. Compare the assembly or pseudocode with source branches, calls, return cases, and error strings.

Useful MCP calls:

```bash
scripts/hopper_mcp_probe.py --json --call-tool search_name --tool-args '{"pattern":"FunctionOrTypeName"}'
scripts/hopper_mcp_probe.py --json --call-tool search_strings --tool-args '{"pattern":"Unique string"}'
scripts/hopper_mcp_probe.py --json --call-tool xrefs --tool-args '{"address":"0x10009cae0"}'
scripts/hopper_mcp_probe.py --json --call-tool procedure_info --tool-args '{"procedure":"0x100018ac8"}'
scripts/hopper_mcp_probe.py --json --call-tool procedure_assembly --tool-args '{"procedure":"0x100018ac8"}'
```

## 6. Swift Correlation Gotchas

- Swift symbols may be long but demangled names often preserve module, type, function, generic specialization, and closure context. Prefer `search_name` or snapshot `demangled` fields before scanning raw assembly.
- Procedure tools in Hopper MCP use `procedure` for either a symbol or a hexadecimal address. `address` is only for address-oriented tools such as `xrefs` and `goto_address`.
- Short Swift strings such as dictionary keys or suffix tokens can be encoded as immediates, not as rows in Hopper's string list. Confirm with assembly constants and calls such as `String.hasSuffix`, dictionary `find`, or `_parseInteger`.
- Optimized Swift can inline tuples and enum cases. A decompiler may show only one return register even when source returns a struct or tuple; check the ABI-level register moves at the return block.
- String xrefs can point to UI presentation or description getters rather than the business function that computed a value. Follow callers and callees before assigning ownership.
- Mangled private symbols with file-hash components still correlate well when the demangled name includes the source type/function.
- For functions with many basic blocks, focused assembly can be more reliable than full pseudocode. Decompilation may be slow and can produce very large output.

## 7. Triage Procedure Sets

Group procedures by evidence:

- Entry points and app lifecycle selectors.
- UI actions, command handlers, or menu callbacks.
- XPC, socket, URLSession, file, Keychain, and launch service APIs.
- Parser or deserializer routines.
- License, auth, update, and entitlement checks.
- Persistent storage and state-retention artifacts.

For each candidate function, record:

- Address and Hopper name.
- Callers and callees.
- Strings and imports referenced nearby.
- Relevant source path if known.
- Confidence level and next evidence needed.

## 8. Reporting Rules

Use `assets/hopper-analysis-report-template.md` for reports.

Every non-trivial claim should cite at least one of:

- Hopper procedure address and name.
- String address and value.
- Xref source and destination.
- Import or selector name.
- Source file and line, when source is available.

Do not present decompiler output as authoritative. Phrase pseudocode-only observations as "Hopper pseudocode suggests..." and follow with the assembly or xref that supports or weakens the claim.

## 9. Modification Boundary

Do not modify installed apps, source checkouts, or test fixtures in place. For binary patching, annotation write-back, or produced executables:

```bash
workdir="$(mktemp -d /tmp/hopper-analysis.XXXXXX)"
cp -R "/path/to/Target.app" "$workdir/"
```

Only run Hopper write-back actions after the user explicitly asks for annotations or binary changes. Prefer comments, labels, tags, and bookmarks over byte changes unless the task specifically requires a produced executable.

Universal Mach-O patching requires per-slice work:

```bash
workdir="$(mktemp -d /tmp/hopper-patch.XXXXXX)"
lipo -extract arm64 Target -output "$workdir/Target.arm64"
lipo -extract x86_64 Target -output "$workdir/Target.x86_64"
# Patch each thin slice separately, then:
lipo -create "$workdir/Target.arm64.patched" "$workdir/Target.x86_64.patched" -output "$workdir/Target"
codesign --force --sign - "$workdir/Target"
```

Do not assume a virtual address is always the same as a file offset. Check the selected slice's load commands with `otool -l` and account for FAT slice offsets before byte-level verification.
