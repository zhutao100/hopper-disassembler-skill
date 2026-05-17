# Hopper Analysis Report

## Target

- Binary:
- Architecture:
- Hopper version:
- Snapshot:

## Executive Summary

- Purpose:
- Primary entry points:
- High-confidence findings:
- Unknowns:

## Evidence

- Segments and sections:
- Procedure and call graph summary:
- Strings and names:
- External imports and platform APIs:
- Pseudocode notes:

## Function Triage

| Address | Name | Evidence | Assessment | Next step |
|---|---|---|---|---|
| | | | | |

## Boundaries and Risks

- Trust boundaries:
- Authorization boundary checks:
- Confidentiality boundary checks:
- Persistence or state-retention artifacts:
- Input parsing and unsafe memory patterns:

## Reproducibility

```bash
scripts/run_hopper_export.sh --output /tmp/target.hopper-snapshot.json /path/to/target
scripts/hopper_mcp_probe.py --json
```

## Notes

- Treat decompiler output as a hypothesis until corroborated with assembly, strings, xrefs, and source.
- Record exact addresses, function names, and snapshot paths for every claim.
