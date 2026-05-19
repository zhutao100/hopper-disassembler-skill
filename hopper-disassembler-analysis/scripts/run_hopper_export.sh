#!/usr/bin/env bash
set -euo pipefail

usage() {
    cat <<'EOF'
Usage: run_hopper_export.sh [options] <binary-app-or-hop>

Open a target in Hopper and run hopper_export_snapshot.py against it.

Options:
  -o, --output PATH             Output JSON path. Default: ./<target>.hopper-snapshot.json
      --database PATH           Open an existing Hopper .hop database instead of a binary.
      --save-hop PATH           Save the current Hopper database to PATH before closing.
      --hopper PATH             Hopper CLI path. Default: HOPPER_CLI, PATH hopper, or Hopper.app bundled CLI
      --arch auto|arm64|arm64e|x86_64
                                  FAT Mach-O architecture. Default: auto
      --timeout SECONDS         Wait limit for export file. Default: 180
      --max-procedures N        Procedure cap. Default: 500
      --max-strings N           String cap. Default: 2000
      --max-names N             Named-address cap. Default: 3000
      --max-string-xrefs N      Xrefs per string cap. Default: 16
      --max-basic-blocks N      Basic blocks per procedure cap. Default: 64
      --max-instructions-per-block N
                                  Instructions per basic block cap. Default: 8
      --max-call-refs N         Caller/callee refs per procedure cap. Default: 64
      --max-pseudocode-functions N
                                  Pseudocode functions cap. Default: 20
      --max-pseudocode-chars N   Characters per pseudocode body. Default: 20000
      --procedure-pattern REGEX Export only matching procedure addresses, names,
                                  demangled names, or signatures.
      --summary-output PATH      Also write a compact Markdown summary for LLM review.
      --summary-filter REGEX     Filter summary rows by name, demangled name, string,
                                  signature, address, or xref procedure text.
      --full                    Remove procedure/string/name caps.
      --include-pseudocode      Include limited pseudocode. Slower; disabled by default.
      --wait-for-analysis       Wait for Hopper background analysis before snapshot/save.
      --keep-open               Leave the Hopper document open after export.
  -h, --help                    Show this help.
EOF
}

abs_path() {
    local path="$1"
    if [[ -d "${path}" ]]; then
        (cd "${path}" && pwd -P)
        return
    fi
    local dir
    local base
    dir="$(dirname "${path}")"
    base="$(basename "${path}")"
    printf '%s/%s\n' "$(cd "${dir}" && pwd -P)" "${base}"
}

find_hopper_cli() {
    local candidate
    if [[ -n "${HOPPER_CLI:-}" && -x "${HOPPER_CLI}" ]]; then
        printf '%s\n' "${HOPPER_CLI}"
        return 0
    fi
    candidate="$(command -v hopper 2>/dev/null || true)"
    if [[ -n "${candidate}" && -x "${candidate}" ]]; then
        printf '%s\n' "${candidate}"
        return 0
    fi
    for candidate in \
        "/Applications/Hopper Disassembler.app/Contents/MacOS/hopper" \
        "/usr/local/bin/hopper"; do
        if [[ -x "${candidate}" ]]; then
            printf '%s\n' "${candidate}"
            return 0
        fi
    done
    return 1
}

resolve_target() {
    local target="$1"
    if [[ -d "${target}" && "${target}" == *.app ]]; then
        local plist="${target}/Contents/Info.plist"
        local executable
        executable="$(/usr/libexec/PlistBuddy -c 'Print :CFBundleExecutable' "${plist}")"
        target="${target}/Contents/MacOS/${executable}"
    fi
    if [[ ! -f "${target}" ]]; then
        echo "error: target is not a file or .app bundle: ${target}" >&2
        return 2
    fi
    abs_path "${target}"
}

resolve_database() {
    local database="$1"
    if [[ ! -f "${database}" ]]; then
        echo "error: Hopper database is not a file: ${database}" >&2
        return 2
    fi
    abs_path "${database}"
}

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
exporter="${script_dir}/hopper_export_snapshot.py"
hopper_bin=""
arch="auto"
timeout_seconds=180
output=""
database=""
save_hop=""
max_procedures=500
max_strings=2000
max_names=3000
max_string_xrefs=16
max_basic_blocks=64
max_instructions_per_block=8
max_call_refs=64
max_pseudocode_functions=20
max_pseudocode_chars=20000
procedure_pattern=""
summary_output=""
summary_filter=""
full_export=0
include_pseudocode=0
close_after_export=1
wait_for_analysis=0

while [[ $# -gt 0 ]]; do
    case "$1" in
        -o | --output)
            output="$2"
            shift 2
            ;;
        --database)
            database="$2"
            shift 2
            ;;
        --save-hop)
            save_hop="$2"
            shift 2
            ;;
        --hopper)
            hopper_bin="$2"
            shift 2
            ;;
        --arch)
            arch="$2"
            shift 2
            ;;
        --timeout)
            timeout_seconds="$2"
            shift 2
            ;;
        --max-procedures)
            max_procedures="$2"
            shift 2
            ;;
        --max-strings)
            max_strings="$2"
            shift 2
            ;;
        --max-names)
            max_names="$2"
            shift 2
            ;;
        --max-string-xrefs)
            max_string_xrefs="$2"
            shift 2
            ;;
        --max-basic-blocks)
            max_basic_blocks="$2"
            shift 2
            ;;
        --max-instructions-per-block)
            max_instructions_per_block="$2"
            shift 2
            ;;
        --max-call-refs)
            max_call_refs="$2"
            shift 2
            ;;
        --max-pseudocode-functions)
            max_pseudocode_functions="$2"
            shift 2
            ;;
        --max-pseudocode-chars)
            max_pseudocode_chars="$2"
            shift 2
            ;;
        --procedure-pattern)
            procedure_pattern="$2"
            shift 2
            ;;
        --summary-output)
            summary_output="$2"
            shift 2
            ;;
        --summary-filter)
            summary_filter="$2"
            shift 2
            ;;
        --full)
            full_export=1
            shift
            ;;
        --include-pseudocode)
            include_pseudocode=1
            shift
            ;;
        --wait-for-analysis)
            wait_for_analysis=1
            shift
            ;;
        --keep-open)
            close_after_export=0
            shift
            ;;
        -h | --help)
            usage
            exit 0
            ;;
        --)
            shift
            break
            ;;
        -*)
            echo "error: unknown option: $1" >&2
            usage >&2
            exit 2
            ;;
        *)
            break
            ;;
    esac
done

if [[ -n "${database}" ]]; then
    if [[ $# -ne 0 ]]; then
        echo "error: pass either --database PATH or a positional target, not both" >&2
        usage >&2
        exit 2
    fi
    target="$(resolve_database "${database}")"
    input_mode="database"
elif [[ $# -eq 1 && "$1" == *.hop ]]; then
    target="$(resolve_database "$1")"
    input_mode="database"
elif [[ $# -eq 1 ]]; then
    target="$(resolve_target "$1")"
    input_mode="executable"
else
    usage >&2
    exit 2
fi

if [[ "${input_mode}" == "database" && "${arch}" != "auto" ]]; then
    echo "error: --arch only applies when opening executable Mach-O targets, not .hop databases" >&2
    exit 2
fi

launch_target="${target}"
load_database=""
if [[ "${input_mode}" == "database" ]]; then
    load_database="${target}"
    # Hopper can open .hop files directly, but that path does not run -Y scripts.
    # Launch a tiny executable, then let the exporter load the database in-process.
    launch_target="${HOPPER_SKILL_DATABASE_BOOTSTRAP:-/bin/echo}"
    if [[ ! -f "${launch_target}" ]]; then
        echo "error: database bootstrap target is not a file: ${launch_target}" >&2
        exit 2
    fi
    launch_target="$(abs_path "${launch_target}")"
fi

if [[ -z "${hopper_bin}" ]]; then
    hopper_bin="$(find_hopper_cli || true)"
fi
if [[ -z "${hopper_bin}" || ! -x "${hopper_bin}" ]]; then
    echo "error: Hopper CLI not found. Set --hopper PATH or HOPPER_CLI." >&2
    exit 2
fi
if [[ ! -f "${exporter}" ]]; then
    echo "error: exporter script missing: ${exporter}" >&2
    exit 2
fi

if [[ -z "${output}" ]]; then
    output="${PWD}/$(basename "${target}").hopper-snapshot.json"
fi
mkdir -p "$(dirname "${output}")"
output="$(abs_path "${output}")"
rm -f "${output}"

loader_args=()
file_info="$(file "${launch_target}")"
if [[ "${file_info}" == *"Mach-O universal binary"* ]]; then
    case "${arch}" in
        auto)
            if [[ "${file_info}" == *"arm64e"* ]]; then
                loader_args=(-l FAT -s AArch64e -l Mach-O)
            elif [[ "${file_info}" == *"arm64"* ]]; then
                loader_args=(-l FAT --aarch64 -l Mach-O)
            elif [[ "${file_info}" == *"x86_64"* ]]; then
                loader_args=(-l FAT --intel-64 -l Mach-O)
            else
                loader_args=(-l FAT -l Mach-O)
            fi
            ;;
        arm64e)
            loader_args=(-l FAT -s AArch64e -l Mach-O)
            ;;
        arm64)
            loader_args=(-l FAT --aarch64 -l Mach-O)
            ;;
        x86_64)
            loader_args=(-l FAT --intel-64 -l Mach-O)
            ;;
        *)
            echo "error: unsupported --arch value: ${arch}" >&2
            exit 2
            ;;
    esac
elif [[ "${file_info}" == *"Mach-O"* ]]; then
    loader_args=(-l Mach-O)
fi

if [[ -n "${save_hop}" ]]; then
    mkdir -p "$(dirname "${save_hop}")"
    save_hop="$(abs_path "${save_hop}")"
fi

log_path="${TMPDIR:-/tmp}/hopper-disassembler-analysis-${$}.log"
runner_path="${TMPDIR:-/tmp}/hopper-disassembler-analysis-${$}.py"
rm -f "${log_path}"
rm -f "${runner_path}"

python3 - "${runner_path}" "${exporter}" "${output}" "${max_procedures}" "${max_strings}" "${max_names}" "${max_string_xrefs}" "${max_basic_blocks}" "${max_instructions_per_block}" "${max_call_refs}" "${max_pseudocode_functions}" "${max_pseudocode_chars}" "${procedure_pattern}" "${full_export}" "${include_pseudocode}" "${close_after_export}" "${wait_for_analysis}" "${save_hop}" "${load_database}" <<'PY'
from __future__ import annotations

import sys
from pathlib import Path

runner, exporter, output = sys.argv[1:4]
keys = [
    "HOPPER_SKILL_MAX_PROCEDURES",
    "HOPPER_SKILL_MAX_STRINGS",
    "HOPPER_SKILL_MAX_NAMES",
    "HOPPER_SKILL_MAX_STRING_XREFS",
    "HOPPER_SKILL_MAX_BASIC_BLOCKS",
    "HOPPER_SKILL_MAX_INSTRUCTIONS_PER_BLOCK",
    "HOPPER_SKILL_MAX_CALL_REFS",
    "HOPPER_SKILL_MAX_PSEUDOCODE_FUNCTIONS",
    "HOPPER_SKILL_MAX_PSEUDOCODE_CHARS",
    "HOPPER_SKILL_PROCEDURE_PATTERN",
    "HOPPER_SKILL_FULL_EXPORT",
    "HOPPER_SKILL_INCLUDE_PSEUDOCODE",
    "HOPPER_SKILL_CLOSE_AFTER_EXPORT",
    "HOPPER_SKILL_WAIT_FOR_ANALYSIS",
    "HOPPER_SKILL_SAVE_DATABASE_PATH",
    "HOPPER_SKILL_LOAD_DATABASE_PATH",
]
values = dict(zip(keys, sys.argv[4:]))
if len(values) != len(keys):
    raise SystemExit("internal error: missing Hopper export runner values")
values["HOPPER_SKILL_EXPORT_PATH"] = output

lines = [
    "import os",
    "import traceback",
]
for key, value in sorted(values.items()):
    lines.append(f"os.environ[{key!r}] = {value!r}")
lines.extend(
    [
        f"_hopper_skill_exporter = {exporter!r}",
        f"_hopper_skill_error_path = {str(Path(output).with_suffix(Path(output).suffix + '.error.log'))!r}",
        "try:",
        "    with open(_hopper_skill_exporter, 'r', encoding='utf-8') as _handle:",
        "        _source = _handle.read()",
        "    _namespace = dict(globals())",
        "    _namespace.update({'__name__': '__main__', '__file__': _hopper_skill_exporter})",
        "    exec(compile(_source, _hopper_skill_exporter, 'exec'), _namespace)",
        "except SystemExit as _exc:",
        "    if _exc.code not in (0, None):",
        "        with open(_hopper_skill_error_path, 'w', encoding='utf-8') as _handle:",
        "            traceback.print_exc(file=_handle)",
        "        raise",
        "except BaseException:",
        "    with open(_hopper_skill_error_path, 'w', encoding='utf-8') as _handle:",
        "        traceback.print_exc(file=_handle)",
        "    raise",
    ]
)
Path(runner).write_text("\n".join(lines) + "\n", encoding="utf-8")
PY

cleanup() {
    rm -f "${runner_path}"
}
trap cleanup EXIT

hopper_args=()
if [[ "${input_mode}" == "database" ]]; then
    hopper_args=(-A -O -F -Z "${loader_args[@]}" -e "${launch_target}" -Y "${runner_path}")
else
    hopper_args=(-a -o -f -z "${loader_args[@]}" -e "${launch_target}" -Y "${runner_path}")
fi

if ! "${hopper_bin}" "${hopper_args[@]}" >"${log_path}" 2>&1; then
    echo "error: Hopper launcher failed" >&2
    echo "Hopper log: ${log_path}" >&2
    sed -n '1,120p' "${log_path}" >&2 || true
    exit 1
fi

deadline=$((SECONDS + timeout_seconds))
while [[ ! -s "${output}" ]]; do
    if [[ -s "${output}.error.log" ]]; then
        echo "error: Hopper exporter failed" >&2
        echo "Hopper log: ${log_path}" >&2
        sed -n '1,120p' "${log_path}" >&2 || true
        echo "Exporter error log: ${output}.error.log" >&2
        sed -n '1,160p' "${output}.error.log" >&2 || true
        exit 1
    fi
    if ((SECONDS >= deadline)); then
        echo "error: timed out waiting for Hopper export: ${output}" >&2
        echo "Hopper log: ${log_path}" >&2
        sed -n '1,120p' "${log_path}" >&2 || true
        if [[ -f "${output}.error.log" ]]; then
            echo "Exporter error log: ${output}.error.log" >&2
            sed -n '1,160p' "${output}.error.log" >&2 || true
        fi
        exit 1
    fi
    sleep 1
done

python3 -m json.tool "${output}" >/dev/null
echo "exported ${output}"
if [[ -n "${summary_output}" ]]; then
    mkdir -p "$(dirname "${summary_output}")"
    summary_output="$(abs_path "${summary_output}")"
    summary_args=(--output "${summary_output}")
    if [[ -n "${summary_filter}" ]]; then
        summary_args+=(--filter "${summary_filter}")
    fi
    summary_args+=("${output}")
    python3 "${script_dir}/hopper_snapshot_summary.py" "${summary_args[@]}"
    echo "summary ${summary_output}"
fi
echo "hopper log ${log_path}"
