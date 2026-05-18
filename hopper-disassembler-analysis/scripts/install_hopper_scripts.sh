#!/usr/bin/env bash
set -euo pipefail

usage() {
    cat <<'EOF'
Usage: install_hopper_scripts.sh [--replace] [--target-dir DIR] [--dry-run]

Install Hopper menu scripts from this skill into the user's Hopper Scripts folder.
The installed export script writes a bounded JSON snapshot of the current Hopper document to /tmp by default.
EOF
}

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
target_dir="${HOME}/Library/Application Support/Hopper/Scripts"
replace=0
dry_run=0

while [[ $# -gt 0 ]]; do
    case "$1" in
        --replace)
            replace=1
            shift
            ;;
        --target-dir)
            target_dir="$2"
            shift 2
            ;;
        --dry-run)
            dry_run=1
            shift
            ;;
        -h | --help)
            usage
            exit 0
            ;;
        *)
            echo "error: unknown option: $1" >&2
            usage >&2
            exit 2
            ;;
    esac
done

source_script="${script_dir}/hopper_export_snapshot.py"
if [[ ! -f "${source_script}" ]]; then
    echo "error: missing source script: ${source_script}" >&2
    exit 2
fi

target_path="${target_dir}/Hopper Skill - Export Snapshot.py"
if [[ -e "${target_path}" && "${replace}" -ne 1 ]]; then
    echo "error: ${target_path} exists; rerun with --replace" >&2
    exit 3
fi

echo "install ${source_script} -> ${target_path}"
if [[ "${dry_run}" -eq 1 ]]; then
    exit 0
fi

mkdir -p "${target_dir}"
cp "${source_script}" "${target_path}"
chmod 0644 "${target_path}"
echo "installed ${target_path}"
echo "In Hopper, use Scripts > Reload Script Folder Content if Hopper is already running."
