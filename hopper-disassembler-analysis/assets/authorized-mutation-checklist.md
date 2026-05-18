# Authorized Mach-O Mutation Checklist

Use this before any byte-level change, load-command edit, install-name edit, or rebuilt executable test.

## Authorization

- Scope owner:
- Target binary or app bundle:
- Allowed architectures:
- Allowed modification class:
- Explicitly out-of-scope behavior:
- Test host or VM:

## Baseline Evidence

- Original SHA-256:
- `file` output:
- `lipo -archs` output:
- `codesign -dv --verbose=4` summary:
- `otool -l` or `vtool -show-build` notes:
- Hopper version:
- Hopper architecture slice:

## Planned Change

|Arch|Hopper VA|Slice-relative file offset|Original bytes|New bytes|Reason|Reviewer|
|---|---:|---:|---|---|---|---|
|arm64|||||||
|x86_64|||||||

## Rebuild and Validation

- Thin slices patched from workspace copies only:
- Universal binary rebuilt with `lipo -create`:
- Re-signed identity:
- `codesign --verify --strict --verbose=4` result:
- `spctl`/Gatekeeper status, when relevant:
- Static re-open in Hopper confirms intended bytes:
- Dynamic validation performed only in disposable VM/sandbox:

## Report

- Record unresolved uncertainty and any capped Hopper exports.
