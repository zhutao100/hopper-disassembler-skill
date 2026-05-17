#!/usr/bin/env bash
set -euo pipefail

usage() {
    cat <<'EOF'
Usage: run_hopper_export.sh [options] <binary-or-app>

Open a target in Hopper and run hopper_export_snapshot.py against it.

Options:
  -o, --output PATH             Output JSON path. Default: ./<target>.hopper-snapshot.json
      --hopper PATH             Hopper CLI path. Default: /usr/local/bin/hopper
      --arch auto|arm64|x86_64  FAT Mach-O architecture. Default: auto
      --timeout SECONDS         Wait limit for export file. Default: 180
      --max-procedures N        Procedure cap. Default: 500
      --max-strings N           String cap. Default: 2000
      --max-names N             Named-address cap. Default: 3000
      --full                    Remove procedure/string/name caps.
      --include-pseudocode      Include limited pseudocode. Slower; disabled by default.
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

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
exporter="${script_dir}/hopper_export_snapshot.py"
hopper_bin="/usr/local/bin/hopper"
arch="auto"
timeout_seconds=180
output=""
max_procedures=500
max_strings=2000
max_names=3000
full_export=0
include_pseudocode=0
close_after_export=1

while [[ $# -gt 0 ]]; do
    case "$1" in
        -o | --output)
            output="$2"
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
        --full)
            full_export=1
            shift
            ;;
        --include-pseudocode)
            include_pseudocode=1
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

if [[ $# -ne 1 ]]; then
    usage >&2
    exit 2
fi

target="$(resolve_target "$1")"
if [[ ! -x "${hopper_bin}" ]]; then
    echo "error: Hopper CLI not executable: ${hopper_bin}" >&2
    exit 2
fi
if [[ ! -f "${exporter}" ]]; then
    echo "error: exporter script missing: ${exporter}" >&2
    exit 2
fi

if [[ -z "${output}" ]]; then
    output="${PWD}/$(basename "${target}").hopper-snapshot.json"
fi
output="$(abs_path "${output}")"
mkdir -p "$(dirname "${output}")"
rm -f "${output}"

file_info="$(file "${target}")"
loader_args=()
if [[ "${file_info}" == *"Mach-O universal binary"* ]]; then
    case "${arch}" in
        auto)
            if [[ "${file_info}" == *"arm64"* ]]; then
                loader_args=(-l FAT --aarch64 -l Mach-O)
            elif [[ "${file_info}" == *"x86_64"* ]]; then
                loader_args=(-l FAT --intel-64 -l Mach-O)
            else
                loader_args=(-l FAT -l Mach-O)
            fi
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

log_path="${TMPDIR:-/tmp}/hopper-disassembler-analysis-${$}.log"
rm -f "${log_path}"

(
    export HOPPER_SKILL_EXPORT_PATH="${output}"
    export HOPPER_SKILL_MAX_PROCEDURES="${max_procedures}"
    export HOPPER_SKILL_MAX_STRINGS="${max_strings}"
    export HOPPER_SKILL_MAX_NAMES="${max_names}"
    export HOPPER_SKILL_FULL_EXPORT="${full_export}"
    export HOPPER_SKILL_INCLUDE_PSEUDOCODE="${include_pseudocode}"
    export HOPPER_SKILL_CLOSE_AFTER_EXPORT="${close_after_export}"
    exec "${hopper_bin}" -a -o -f -z "${loader_args[@]}" -e "${target}" -Y "${exporter}"
) >"${log_path}" 2>&1 &

hopper_pid=$!
deadline=$((SECONDS + timeout_seconds))
while [[ ! -s "${output}" ]]; do
    if ((SECONDS >= deadline)); then
        echo "error: timed out waiting for Hopper export: ${output}" >&2
        echo "Hopper log: ${log_path}" >&2
        sed -n '1,120p' "${log_path}" >&2 || true
        kill "${hopper_pid}" 2>/dev/null || true
        exit 1
    fi
    sleep 1
done

wait "${hopper_pid}" 2>/dev/null || true
python3 -m json.tool "${output}" >/dev/null
echo "exported ${output}"
echo "hopper log ${log_path}"
