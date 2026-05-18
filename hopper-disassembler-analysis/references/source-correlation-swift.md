# Swift Source Correlation

Use this reference when a macOS target is built from Swift, SwiftUI, AppKit, or mixed Swift/Objective-C sources.

## Contents

- [Workflow](#workflow)
- [Name and Selector Signals](#name-and-selector-signals)
- [String Xref Signals](#string-xref-signals)
- [Swift Gotchas](#swift-gotchas)
- [Evidence Checklist](#evidence-checklist)

## Workflow

1. Pick one source snippet with stable identifiers or UI/log strings.
2. Resolve the containing Mach-O. Check helpers, frameworks, XPC services, and plugins before assuming the main executable owns the snippet.
3. Export broad names and strings first:

   ```bash
   scripts/run_hopper_export.sh \
     --max-procedures 6000 \
     --max-names 20000 \
     --max-strings 20000 \
     --max-string-xrefs 32 \
     --summary-output /tmp/app.swift-triage.hopper-summary.md \
     --summary-filter 'TypeOrFunction|Unique UI String' \
     --output /tmp/app.swift-triage.hopper-snapshot.json \
     /path/to/App.app
   ```

4. Search snapshot `names[].demangled` for module/type/function fragments and `strings[].value` for source literals.
5. Use each string row's `xrefs_to[].procedure_demangled` to select the function that matches the source context.
6. Rerun focused on the matched function/address when assembly or pseudocode is needed:

   ```bash
   scripts/run_hopper_export.sh \
     --procedure-pattern 'ConfigureContextMenu|0x10003d674' \
     --max-procedures 20 \
     --max-basic-blocks 32 \
     --max-instructions-per-block 16 \
     --max-call-refs 32 \
     --summary-output /tmp/app.swift-focused.hopper-summary.md \
     --output /tmp/app.swift-focused.hopper-snapshot.json \
     /path/to/App.app
   ```

## Name and Selector Signals

- Prefer `demangled` fields and MCP `search_name` over raw mangled names.
- Private Swift functions commonly include a file-hash component, but the demangled name still preserves module, type, and function context.
- `@objc`-reachable methods often appear twice: an Objective-C selector surface such as `-[Module.Type OnContextQuit]`, plus a Swift thunk or implementation symbol.
- SwiftUI closure names are useful but noisy. Treat closure numbers and generic-specialization suffixes as orientation only.
- AppKit and Objective-C interop often shows `objc_msgSend` plus Swift bridge calls such as `_bridgeToObjectiveC` near UI string construction.

## String Xref Signals

Use string xrefs to move from source literals to code, then choose the xref whose containing procedure matches the source snippet.

Verified pattern from a menu-bar Swift app:

- Source snippet: an AppKit context menu builder with menu item titles such as `Reconnect codexd`, `Status Center...`, and `Quit CodexMenuBar`.
- Hopper name signal: a demangled procedure like `Module.StatusMenuController.(ConfigureContextMenu in _HASH)() -> ()`.
- Hopper string signal: each title appeared in `strings[]`, and xrefs to those strings included the context-menu procedure.
- Additional xrefs existed from other UI surfaces and the main menu, so the string alone was insufficient; the containing procedure confirmed the snippet.
- Focused procedure signal: the procedure called Swift string bridging, `objc_msgSend`, `objc_release`, and `NSArray` bridging around `NSMenuItem` construction, matching source-level AppKit menu assembly.

## Swift Gotchas

- Short strings, dictionary keys, enum tags, and small suffix tokens may be encoded inline or packed and may not appear as clean string rows.
- Verified example: `Quick Start` and `Settings...` in source appeared as short/packed fragments in raw `strings`, while longer titles such as `Reconnect codexd`, `Status Center...`, and `Quit CodexMenuBar` appeared as clean Hopper string rows.
- Optimized Swift can inline tuples, enum cases, and closures. Decompiler output can hide return-register details; check assembly at return blocks for ABI-level behavior.
- A string can be referenced by multiple UI surfaces. Do not assign ownership from the first xref.
- A filtered summary can include nearby strings whose value does not match the source literal because the string's xref procedure matches the filter. Treat those as context until the literal and xref both match.
- Swift generic and SwiftUI-heavy functions can have very long names and many synthetic callees. Narrow by source type/function first, then inspect callers/callees.
- Objective-C method-list and Swift metadata sections are good orientation signals, not behavior proof by themselves.

## Evidence Checklist

Record:

- Source path and line span for the snippet.
- Mach-O path and architecture slice.
- Hopper procedure address, raw name, and demangled name.
- Matching string addresses and xref addresses.
- Callees/imports that match the source APIs, for example AppKit menu construction or Swift bridging.
- Any ambiguity from shared strings, wrappers, generated closures, or truncated snapshot caps.
