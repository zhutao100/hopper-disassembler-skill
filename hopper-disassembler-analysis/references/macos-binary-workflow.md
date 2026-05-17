# macOS Binary Analysis Workflow

Use this reference when the target is a macOS app bundle, command-line tool, framework, XPC service, or helper.

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
fd -t f -d 4 . "$app/Contents/MacOS" "$app/Contents/Frameworks" "$app/Contents/XPCServices" "$app/Contents/PlugIns"
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
strings -a "$target" | rg -n "http|keychain|token|license|login|xpc|socket" -m 80
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

For focused decompiler review:

```bash
scripts/run_hopper_export.sh \
  --include-pseudocode \
  --max-procedures 50 \
  --output /tmp/target.focused.hopper-snapshot.json \
  "$target"
```

## 4. Correlate With Source When Available

If the user provided source, search source and Hopper artifacts together:

```bash
rg -n "SymbolOrStringFromHopper" /path/to/source
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

## 5. Triage Procedure Sets

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

## 6. Reporting Rules

Use `assets/hopper-analysis-report-template.md` for reports.

Every non-trivial claim should cite at least one of:

- Hopper procedure address and name.
- String address and value.
- Xref source and destination.
- Import or selector name.
- Source file and line, when source is available.

Do not present decompiler output as authoritative. Phrase pseudocode-only observations as "Hopper pseudocode suggests..." and follow with the assembly or xref that supports or weakens the claim.

## 7. Modification Boundary

Do not modify installed apps, source checkouts, or test fixtures in place. For binary patching, annotation write-back, or produced executables:

```bash
workdir="$(mktemp -d /tmp/hopper-analysis.XXXXXX)"
cp -R "/path/to/Target.app" "$workdir/"
```

Only run Hopper write-back actions after the user explicitly asks for annotations or binary changes. Prefer comments, labels, tags, and bookmarks over byte changes unless the task specifically requires a produced executable.
