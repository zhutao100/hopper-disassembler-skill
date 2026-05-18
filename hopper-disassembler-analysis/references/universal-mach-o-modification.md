# Universal Mach-O Modification Workflow

Use this reference for authorized mutation planning on universal macOS Mach-O files. It is also useful for non-mutating analysis because it keeps address spaces and slices separate.

## Core Rule

A universal Mach-O file is a container of architecture-specific thin Mach-O slices. Analyze and modify one thin slice at a time, then recombine slices and re-sign the resulting output. Do not write byte changes into the installed original.

## Coordinates to Keep Separate

|Coordinate|Meaning|Example use|
|-|-|-|
|Hopper virtual address|The address Hopper shows after applying Mach-O segment VM addresses and slide assumptions|Instruction and xref reasoning.|
|Slice-relative file offset|Offset inside one thin Mach-O slice|Patching a copied thin slice or validating a produced thin executable.|
|Fat-file absolute offset|Offset from the beginning of the universal container|Patching or verifying bytes in the recombined universal file.|

Use `macho_address_map.py` before and after any byte-level reasoning:

```bash
scripts/macho_address_map.py --arch arm64 --address 0x100003f50 /path/to/UniversalBinary
scripts/macho_address_map.py --arch x86_64 --offset 0x3f50 /path/to/UniversalBinary
```

## Recommended Workspace

Create a copy-only workspace:

```bash
scripts/macho_universal_workspace.py \
  --output-dir /tmp/target.macho-workspace \
  --sign-ad-hoc \
  /path/to/Target.app
```

The workspace contains:

```text
WORKFLOW.md
plan.json
recombine.sh
install_rebuilt_into_app.sh
original/
slices/
patched/
rebuilt/
metadata/
```

- `original/`: copied original executable.
- `slices/`: extracted thin slices when `lipo` is available, or copied thin input when applicable.
- `patched/`: put reviewed modified thin slices here using the names described in `WORKFLOW.md`.
- `rebuilt/`: output directory for `recombine.sh`.
- `metadata/`: full baseline `file`, `lipo`, `otool`, `vtool`, and `codesign` output.
- `plan.json`: compact command log previews plus paths to full metadata files.
- `recombine.sh`: generated script that recombines patched slices or copies a patched thin file to `rebuilt/`.
- `install_rebuilt_into_app.sh`: for `.app` inputs, installs `rebuilt/<binary>` into the input app bundle. Run it only when the input is a disposable app copy.

## Manual Universal Workflow

When not using the workspace script:

```bash
mkdir -p /tmp/target-universal/{original,slices,patched,out,metadata}
cp /path/to/UniversalBinary /tmp/target-universal/original/UniversalBinary
lipo -info /tmp/target-universal/original/UniversalBinary
lipo -extract arm64 /tmp/target-universal/original/UniversalBinary -output /tmp/target-universal/slices/UniversalBinary.arm64
lipo -extract x86_64 /tmp/target-universal/original/UniversalBinary -output /tmp/target-universal/slices/UniversalBinary.x86_64
```

Open and modify copied thin slices only. Produce new thin executables into `patched/`, then recombine:

```bash
lipo -create \
  /tmp/target-universal/patched/UniversalBinary.arm64 \
  /tmp/target-universal/patched/UniversalBinary.x86_64 \
  -output /tmp/target-universal/out/UniversalBinary
codesign --force --sign - /tmp/target-universal/out/UniversalBinary
codesign --verify --verbose=4 /tmp/target-universal/out/UniversalBinary
```

Ad-hoc signing is for local testing. Distribution, notarization, hardened runtime, and entitlements require a proper signing identity and release workflow.

## Hopper-Specific Workflow

1. Use CLI tools to identify slices first.
2. Open a copied thin slice in Hopper, not the universal container, when mutation is planned.
3. Apply only reviewed, same-slice changes.
4. Produce a new executable from Hopper into `patched/`.
5. Re-run `macho_address_map.py` on the produced thin slice and recombined output.
6. Re-open the produced output in Hopper or verify with `otool`/`llvm-objdump` to confirm the intended basic block changed and nearby code was not corrupted.
7. Re-sign and test only in a disposable environment.

## Load Commands and Signatures

Relevant load commands and data:

- `LC_SEGMENT_64`: maps VM address ranges to file offsets.
- `LC_CODE_SIGNATURE`: points to the embedded code signature data; mutation normally invalidates it.
- `LC_DYLD_CHAINED_FIXUPS`: modern dyld fixup metadata can be important for pointer and import reasoning.
- `LC_BUILD_VERSION`: platform, minimum OS, and SDK information.
- `LC_LOAD_DYLIB`/`LC_LOAD_WEAK_DYLIB`/related commands: dynamic dependency graph.

Do not remove or blindly edit load commands. Use `vtool`, `install_name_tool`, or a proper linker workflow for supported load-command operations, then verify signing and runtime behavior.

## Slice Plan Template

Copy and fill:

```bash
cp assets/macho-slice-plan-template.json /tmp/target.macho-workspace/plan.review.json
```

A good plan records:

- Authorization scope and owner.
- Original file hash and produced output hash.
- Per-architecture Hopper document name, VA, slice offset, fat offset, procedure, and evidence.
- Modification intent in behavioral terms, not just bytes.
- Recombination command and signing command.
- Test matrix across available architectures.

## Verification Checklist

Before reporting success:

- `lipo -info` shows expected slices.
- `file` reports expected universal/thin type.
- `macho_address_map.py` maps all cited addresses in the final output.
- `otool -l` load commands are structurally sane.
- `codesign --verify --verbose=4` result is recorded.
- The app/binary launches only in an authorized sandbox/VM/test machine.
- Behavior is verified per architecture, not only on the host architecture.
