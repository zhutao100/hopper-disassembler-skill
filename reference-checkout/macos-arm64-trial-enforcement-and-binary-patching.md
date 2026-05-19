## Introduction[#](https://sperixlabs.org/post/2026/02/unlocking-the-vault-a-deep-dive-into-macos-arm64-trial-enforcement-and-binary-patching/#introduction)

In the course of analyzing a decompiled macOS productivity application—a calendar and meeting alert utility with a time-limited trial—we encountered a multi-layered enforcement mechanism governing trial expiry, feature gating, and application termination. This practice is common in commercial software: when the trial expires, the app displays warnings, disables premium features, and eventually terminates unless the user purchases or restores a license.

This article documents the complete reverse engineering journey: from initial string reconnaissance through call-graph tracing, assembly-level analysis, and ultimately the development of six binary patches that bypass trial termination, re-enable gated features, and customize the UI—all without modifying the application’s source code or runtime environment.

___

## Overview & Goals[#](https://sperixlabs.org/post/2026/02/unlocking-the-vault-a-deep-dive-into-macos-arm64-trial-enforcement-and-binary-patching/#overview--goals)

**Target:** A macOS calendar/meeting alert application with a trial period, distributed as a Mach-O 64-bit executable (ARM64, with optional universal x86\_64+ARM64 support).

**Observed behavior:** When the trial expires, the app shows “Trial expired - Alerts disabled” and eventually displays a modal: “Your trial is complete. Purchase \[the app\] to continue using the app, or the app will close.” If the user does not click “Restore,” the application terminates.

**Goals:**

1.  Trace the trial validation flow from UI strings to enforcement logic
2.  Identify the critical branch that triggers app termination
3.  Re-enable alerts and other license-gated features
4.  Customize banner text and UI elements
5.  Create reproducible binary patches for both single-arch and universal binaries

___

| Tool | Purpose |
| --- | --- |
| **Hopper Disassembler** | Primary analysis (ARM64 decompilation, cross-references, call graphs) |
| **HopperPyMCP** (optional) | MCP integration for AI-assisted analysis |
| **xxd** | Hex dump for binary inspection and patch verification |
| **otool** | Mach-O structure inspection (segments, slices) |
| **PlistBuddy** | UserDefaults/plist inspection (alternative bypass vectors) |

**Binary path:** `[App].app/Contents/MacOS/[App]`
**Architecture:** ARM64 (Mach-O 64-bit executable)
**Base address:** `0x100000000` (standard macOS PIE)

**Important:** For Mach-O executables, the `__TEXT` segment typically has `vmaddr 0x100000000` and `fileoff 0`, so virtual addresses map directly to file offsets within each architecture slice.

___

## Step 1: Initial Reconnaissance[#](https://sperixlabs.org/post/2026/02/unlocking-the-vault-a-deep-dive-into-macos-arm64-trial-enforcement-and-binary-patching/#step-1-initial-reconnaissance)

### Locating the Binary[#](https://sperixlabs.org/post/2026/02/unlocking-the-vault-a-deep-dive-into-macos-arm64-trial-enforcement-and-binary-patching/#locating-the-binary)

```bash
file [App].app/Contents/MacOS/[App] # Output: Mach-O 64-bit executable arm64 # Or: Mach-O universal binary with 2 architectures: [x86_64, arm64]
```

### String Hunting[#](https://sperixlabs.org/post/2026/02/unlocking-the-vault-a-deep-dive-into-macos-arm64-trial-enforcement-and-binary-patching/#string-hunting)

```bash
strings [App].app/Contents/MacOS/[App] | grep -iE "trial|expired|purchase"
```

**Key strings found:**

-   `Trial expired - Alerts disabled`
-   `Trial not started`
-   `1h left in trial`
-   `Your trial is complete. Purchase [App] to continue using the app, or the app will close.`
-   `app_quit_after_trial_expiry`
-   `trialStartDateKey`
-   `trialValidationKey`
-   `purchased_product_ids`

### Data Storage[#](https://sperixlabs.org/post/2026/02/unlocking-the-vault-a-deep-dive-into-macos-arm64-trial-enforcement-and-binary-patching/#data-storage)

The application is sandboxed. Preferences and purchase state live in the app container:

```bash
ls ~/Library/Containers/[bundle_id]/Data/Library/ plutil -p ~/Library/Containers/[bundle_id]/Data/Library/Preferences/[bundle_id].plist
```

**Relevant keys:** `purchased_product_ids`, `trial_duration_migration_v1`, `app_install_date`

___

## Step 2: Tracing String References[#](https://sperixlabs.org/post/2026/02/unlocking-the-vault-a-deep-dive-into-macos-arm64-trial-enforcement-and-binary-patching/#step-2-tracing-string-references)

### Cross-References in Hopper[#](https://sperixlabs.org/post/2026/02/unlocking-the-vault-a-deep-dive-into-macos-arm64-trial-enforcement-and-binary-patching/#cross-references-in-hopper)

1.  Open the binary in Hopper Disassembler
2.  Search for the string `Trial expired - Alerts disabled`
3.  Right-click → **References to this address**

**“Trial expired - Alerts disabled”** is referenced by two procedures. One of them—the banner text getter—selects which trial message to display based on trial state.

### Call Graph (Backward)[#](https://sperixlabs.org/post/2026/02/unlocking-the-vault-a-deep-dive-into-macos-arm64-trial-enforcement-and-binary-patching/#call-graph-backward)

```
TrialBannerView → sub_1000cd914 → sub_1000ccde0 (banner text getter)
```

### Key Components Identified[#](https://sperixlabs.org/post/2026/02/unlocking-the-vault-a-deep-dive-into-macos-arm64-trial-enforcement-and-binary-patching/#key-components-identified)

| Component | Purpose |
| --- | --- |
| **PurchaseManager** | Trial state, StoreKit integration, UserDefaults keys |
| **BannerNotificationManager** | Notification banner UI |
| **TrialBannerView** | SwiftUI trial banner view |
| **NotificationPreferenceManager** | Alert preferences and gating |

___

The banner text getter receives a `TrialState` enum and returns the appropriate string:

```
Input: TrialState enum (case + payload)
- var_38 = case selector (0 = active, 1 = expired/notStarted)
- x22 = hours remaining (for active) or 0 for expired

If case == 1 (expired/notStarted):
  If x22 == 0: return "Trial expired - Alerts disabled"
  Else:        return "Trial not started"
If x22 == 1:
  return "1h left in trial"
If x22 &lt;= 23:
  return "{x22}h left in trial"
If x22 &gt;= 24:
  days = x22 / 24
  return "{days} day(s) left in trial"
```

### TrialState Enum (from Hopper metadata)[#](https://sperixlabs.org/post/2026/02/unlocking-the-vault-a-deep-dive-into-macos-arm64-trial-enforcement-and-binary-patching/#trialstate-enum-from-hopper-metadata)

```swift
enum PurchaseManager.TrialState { case active(hoursRemaining: Int) case notStarted case expired }
```

___

## Step 4: Locating the Trial Expiry Handler[#](https://sperixlabs.org/post/2026/02/unlocking-the-vault-a-deep-dive-into-macos-arm64-trial-enforcement-and-binary-patching/#step-4-locating-the-trial-expiry-handler)

### Search for Termination Strings[#](https://sperixlabs.org/post/2026/02/unlocking-the-vault-a-deep-dive-into-macos-arm64-trial-enforcement-and-binary-patching/#search-for-termination-strings)

The string “Your trial is complete” references a procedure that displays an `NSAlert` and calls `[NSApp terminate]`. The analytics event `app_quit_after_trial_expiry` is logged immediately before termination.

### Call Chain to Trial Expiry[#](https://sperixlabs.org/post/2026/02/unlocking-the-vault-a-deep-dive-into-macos-arm64-trial-enforcement-and-binary-patching/#call-chain-to-trial-expiry)

```
sub_1001165a8 → sub_1001156a0 → sub_100115738 → sub_100115a18
```

**sub\_100115a18** is the trial expiry alert handler:

1.  Creates `NSAlert` with “Trial Complete - Upgrade to Continue” and “Your trial is complete…”
2.  Adds buttons: “Restore” and “Purchase”
3.  Runs modal: `[alert runModal]`
4.  **If return value == 0x3e8 (1000):** User clicked “Restore” → call restore flow, do not terminate
5.  **Else:** Log `app_quit_after_trial_expiry`, call `[NSApp terminate:0]`

___

## Step 5: Assembly Analysis of the Critical Branch[#](https://sperixlabs.org/post/2026/02/unlocking-the-vault-a-deep-dive-into-macos-arm64-trial-enforcement-and-binary-patching/#step-5-assembly-analysis-of-the-critical-branch)

### The Critical Instruction[#](https://sperixlabs.org/post/2026/02/unlocking-the-vault-a-deep-dive-into-macos-arm64-trial-enforcement-and-binary-patching/#the-critical-instruction)

| Address | Instruction | Bytes (hex) | Purpose |
| --- | --- | --- | --- |
| `0x100115b5c` | `cmp x0, #0x3e8` | `0a 09 00 d1` (LE) | Compare `runModal` return value to 1000 (Restore button) |

**Branch behavior:**

-   If `x0 == 0x3e8` (Z=1): Branch to Restore path → no terminate
-   If `x0 != 0x3e8` (Z=0): Fall through to terminate block → app quits

### Patch Strategy: Option B[#](https://sperixlabs.org/post/2026/02/unlocking-the-vault-a-deep-dive-into-macos-arm64-trial-enforcement-and-binary-patching/#patch-strategy-option-b)

**Goal:** Make the branch always take the Restore path.

**Chosen approach:** Replace `cmp x0, #0x3e8` with `cmp x0, x0`. This always sets Z=1 (equal), so the subsequent `b.eq` (branch if equal) will always branch to the Restore block.

**ARM64 encoding:**

-   Original: `cmp x0, #0x3e8` → `0a 09 00 d1`
-   Patch: `cmp x0, x0` → `1f 00 00 eb`

___

## Step 6: Alert Gating — Why Patches 1 Alone Isn’t Enough[#](https://sperixlabs.org/post/2026/02/unlocking-the-vault-a-deep-dive-into-macos-arm64-trial-enforcement-and-binary-patching/#step-6-alert-gating--why-patches-1-alone-isnt-enough)

Patch 1 prevents termination, but alerts remain disabled. The alert scheduler checks a function we call `has_valid_license` before showing any alert:

```
alert_scheduler
  if (has_valid_license())
    → show alert
  else
    → log "alert_blocked_no_license"
    → skip alert
```

**has\_valid\_license** returns 1 if: lifetime purchased OR annual/monthly purchased OR trial still active. Returns 0 when trial expired and no purchase.

**Patch 2:** Replace the first 8 bytes of `has_valid_license` with `mov w0, #1; ret` — always return true. Alerts are then shown regardless of trial state.

**ARM64 encoding:**

-   `mov w0, #1` → `20 00 80 52`
-   `ret` → `c0 03 5f d6`

___

The application has two distinct banner systems:

1.  **Trial banner (orange)** — Uses the banner text getter. Shows “Trial expired - Alerts disabled”, “1h left in trial”, etc. **Patch 3** modifies the `adrp`/`add` instructions to load “Your lifetime license is active” instead of “Trial expired - Alerts disabled” when trial is expired.

2.  **License status banner (green checkmark)** — Shown when `has_valid_license()` returns true (Patch 2 enables this). Calls a separate text getter that returns:

    -   If lifetime purchased → “Your lifetime license is active”
    -   If annual/monthly → subscription message
    -   Else → “X days remaining” (trial)

**Patch 4:** Replace the prologue of the license status text getter with `movz x0, #0x1f; movk x0, #0xd000, lsl #48; ret` — always return the Swift string for “Your lifetime license is active”.

___

## Step 8: Universal Binary Considerations[#](https://sperixlabs.org/post/2026/02/unlocking-the-vault-a-deep-dive-into-macos-arm64-trial-enforcement-and-binary-patching/#step-8-universal-binary-considerations)

For universal binaries (x86\_64 + ARM64), each architecture occupies a separate slice. The Mach-O fat header stores the file offset of each slice. Patches must be applied at:

```
file_offset = slice_offset + virtual_offset_within_slice
```

For example, if the ARM64 slice starts at `0x2e4000`, Patch 1 (virtual offset `0x115b5c`) is applied at file offset `0x2e4000 + 0x115b5c`.

String patches (e.g., overwriting “Upgrade to restore alerts” with “@jayluxferro”) may need to be applied to both slices if the string exists in both.

___

## Step 9: Patch Summary[#](https://sperixlabs.org/post/2026/02/unlocking-the-vault-a-deep-dive-into-macos-arm64-trial-enforcement-and-binary-patching/#step-9-patch-summary)

| Patch | Purpose | Technique |
| --- | --- | --- |
| 1 | Terminate bypass | `cmp x0, #0x3e8` → `cmp x0, x0` |
| 2 | Alerts enable | Prologue of `has_valid_license` → `mov w0, #1; ret` |
| 3 | Trial banner text | `adrp`/`add` → load “Your lifetime license is active” |
| 4 | License status banner | Prologue of text getter → return Swift string directly |
| 5 | Trial banner subtitle | Overwrite “Upgrade to restore alerts” with “@jayluxferro” |
| 6 | Hide “About” in settings | Overwrite “About” strings with null bytes |

___

## Step 10: Applying the Patches[#](https://sperixlabs.org/post/2026/02/unlocking-the-vault-a-deep-dive-into-macos-arm64-trial-enforcement-and-binary-patching/#step-10-applying-the-patches)

### Manual Application (ARM64-only binary)[#](https://sperixlabs.org/post/2026/02/unlocking-the-vault-a-deep-dive-into-macos-arm64-trial-enforcement-and-binary-patching/#manual-application-arm64-only-binary)

```bash
# Backup first cp [App].app/Contents/MacOS/[App] [App].bak # Patch 1 — Terminate bypass printf '\x1f\x00\x00\xeb' | dd of="[App]" bs=1 seek=$((0x115b5c)) conv=notrunc # Patch 2 — Alerts enable printf '\x20\x00\x80\x52\xc0\x03\x5f\xd6' | dd of="[App]" bs=1 seek=$((0x12c990)) conv=notrunc
```

### Verification[#](https://sperixlabs.org/post/2026/02/unlocking-the-vault-a-deep-dive-into-macos-arm64-trial-enforcement-and-binary-patching/#verification)

```bash
xxd -s 0x115b58 -l 16 [App] # Expected at 0x115b5c: 1f 00 00 eb
```

### Code Signing[#](https://sperixlabs.org/post/2026/02/unlocking-the-vault-a-deep-dive-into-macos-arm64-trial-enforcement-and-binary-patching/#code-signing)

After patching, macOS may reject the modified binary. Re-sign with:

```bash
codesign -f -s - [App].app/Contents/MacOS/[App]
```

___

## Alternative Bypass: UserDefaults Injection[#](https://sperixlabs.org/post/2026/02/unlocking-the-vault-a-deep-dive-into-macos-arm64-trial-enforcement-and-binary-patching/#alternative-bypass-userdefaults-injection)

If the application does not perform server-side verification, injecting a fake purchase into UserDefaults may suffice:

```bash
PLIST="$HOME/Library/Containers/[bundle_id]/Data/Library/Preferences/[bundle_id].plist" /usr/libexec/PlistBuddy -c "Delete :purchased_product_ids" "$PLIST" /usr/libexec/PlistBuddy -c "Add :purchased_product_ids array" "$PLIST" /usr/libexec/PlistBuddy -c "Add :purchased_product_ids:0 string '[product_id]'" "$PLIST"
```

Quit the application before modifying; relaunch after. This approach may not persist if StoreKit verifies purchases server-side.

___

## Conclusion[#](https://sperixlabs.org/post/2026/02/unlocking-the-vault-a-deep-dive-into-macos-arm64-trial-enforcement-and-binary-patching/#conclusion)

This reverse engineering exercise demonstrated a systematic approach to analyzing trial enforcement in a macOS ARM64 application:

1.  **String hunting** — Identify UI and analytics strings as entry points
2.  **Cross-reference tracing** — Follow references from strings to procedures
3.  **Call graph analysis** — Map the flow from UI to enforcement logic
4.  **Assembly-level understanding** — Identify critical branches and comparison instructions
5.  **Minimal patching** — Apply the smallest possible changes to achieve the desired behavior
6.  **Universal binary awareness** — Account for slice offsets when patching fat binaries

The techniques described—instruction substitution, prologue replacement, and string overwriting—are applicable to similar analyses of commercial macOS applications. Understanding how trial and license enforcement is implemented helps security researchers assess robustness and developers improve their protection strategies.

___

_For educational and authorized security research only._
