# Hopper Analysis Report

## Target

- Binary:
- App bundle, if any:
- Architecture slice:
- Hopper version:
- Snapshot path:
- Summary path:
- Export command:
- Export caps:

## Scope and Authorization

- Authorized target owner or source:
- Allowed actions:
- Explicitly disallowed actions:
- Modification boundary:

## Executive Summary

- Purpose:
- Primary entry points:
- High-confidence findings:
- Unknowns:

## Evidence Ledger

### Platform Metadata

- `file`:
- `lipo -archs`:
- `codesign`:
- `otool -L`:

### Hopper Snapshot

- Segments and sections:
- Procedure and call graph summary:
- Strings and names:
- External imports and selectors:
- Comments, tags, and bookmarks:
- Pseudocode notes:

## Function Triage

Repeat this block for each reviewed function.

### Function: `0x...` `name`

- Confidence:
- Why it matters:
- Evidence:
  - Procedure address/name:
  - String addresses/xrefs:
  - Callers/callees:
  - Source file/line, if available:
- Assessment:
- Next step:

## Boundaries and Risks

- Trust boundaries:
- Authorization boundary checks:
- Confidentiality boundary checks:
- State-retention artifacts:
- Input parsing and unsafe memory patterns:

## Reproducibility

```bash
scripts/inspect_macho_targets.py --include-deps --output /tmp/target.inventory.md /path/to/target
scripts/run_hopper_export.sh --summary-output /tmp/target.hopper-summary.md --output /tmp/target.hopper-snapshot.json /path/to/target
scripts/hopper_evidence_search.py /tmp/target.hopper-snapshot.json 'InterestingSymbol|Interesting string'
```

## Notes

- Treat decompiler output as a hypothesis until corroborated with assembly, strings, xrefs, and source.
- Record exact addresses, function names, and snapshot paths for every claim.
