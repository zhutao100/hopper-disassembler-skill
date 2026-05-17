# macOS Binary Analysis Workflow

Use this reference when the target is a macOS app bundle, command-line tool, framework, XPC service, or helper.

## Contents

- [1. Resolve Targets](#1-resolve-targets)
- [2. Capture Baseline Metadata Outside Hopper](#2-capture-baseline-metadata-outside-hopper)
- [3. Export Hopper Evidence](#3-export-hopper-evidence)
- [4. Read and Triage the Snapshot](#4-read-and-triage-the-snapshot)
- [5. Correlate With Source When Available](#5-correlate-with-source-when-available)
- [6. Triage Procedure Sets](#6-triage-procedure-sets)
- [7. Reporting Rules](#7-reporting-rules)
- [8. Modification Boundary](#8-modification-boundary)

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
- Imports and framework calls match source dependencies.
- Hopper call edges support the source-level flow.

Weak correlation signals:

- Pseudocode resembles source but names, strings, or xrefs do not match.
- A string exists but has no reference from the procedure under review.
- A function name is imported or stubbed rather than app-owned.

## 6. Triage Procedure Sets

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

## 7. Reporting Rules

Use `assets/hopper-analysis-report-template.md` for reports.

Every non-trivial claim should cite at least one of:

- Hopper procedure address and name.
- String address and value.
- Xref source and destination.
- Import or selector name.
- Source file and line, when source is available.

Do not present decompiler output as authoritative. Phrase pseudocode-only observations as "Hopper pseudocode suggests..." and follow with the assembly or xref that supports or weakens the claim.

## 8. Modification Boundary

Do not modify installed apps, source checkouts, or test fixtures in place. For binary patching, annotation write-back, or produced executables:

```bash
workdir="$(mktemp -d /tmp/hopper-analysis.XXXXXX)"
cp -R "/path/to/Target.app" "$workdir/"
```

Only run Hopper write-back actions after the user explicitly asks for annotations or binary changes. Prefer comments, labels, tags, and bookmarks over byte changes unless the task specifically requires a produced executable.
