#!/usr/bin/env bash
set -euo pipefail

usage() {
    cat <<'EOF'
Usage: install_codex_skill.sh [--replace] [--target-root DIR] [--scope user|repo|legacy-codex] [--dry-run]

Install this skill folder into a skills directory.

Defaults:
  --scope user        -> ${AGENTS_SKILLS_HOME:-$HOME/.agents/skills}
  --scope repo        -> .agents/skills under the current repository root when detectable
  --scope legacy-codex -> ${CODEX_HOME:-$HOME/.codex}/skills for older Codex builds
EOF
}

repo_root() {
    if command -v git >/dev/null 2>&1 && git rev-parse --show-toplevel >/dev/null 2>&1; then
        git rev-parse --show-toplevel
    else
        pwd -P
    fi
}

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
skill_dir="$(cd "${script_dir}/.." && pwd -P)"
skill_name="$(basename "${skill_dir}")"
scope="user"
target_root=""
replace=0
dry_run=0

while [[ $# -gt 0 ]]; do
    case "$1" in
        --replace)
            replace=1
            shift
            ;;
        --target-root)
            target_root="$2"
            shift 2
            ;;
        --scope)
            scope="$2"
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

if [[ -z "${target_root}" ]]; then
    case "${scope}" in
        user)
            target_root="${AGENTS_SKILLS_HOME:-${HOME}/.agents/skills}"
            ;;
        repo)
            target_root="$(repo_root)/.agents/skills"
            ;;
        legacy-codex)
            target_root="${CODEX_HOME:-${HOME}/.codex}/skills"
            ;;
        *)
            echo "error: unsupported --scope: ${scope}" >&2
            exit 2
            ;;
    esac
fi

if [[ -d "${target_root}" ]]; then
    target_root="$(cd "${target_root}" && pwd -P)"
elif [[ "${dry_run}" -eq 1 ]]; then
    if [[ "${target_root}" != /* ]]; then
        target_root="${PWD}/${target_root}"
    fi
else
    target_root="$(mkdir -p "${target_root}" && cd "${target_root}" && pwd -P)"
fi
target="${target_root}/${skill_name}"

if [[ "${skill_dir}" == "${target}" ]]; then
    echo "already installed at ${target}"
    exit 0
fi

if [[ -e "${target}" && "${replace}" -ne 1 ]]; then
    echo "error: ${target} already exists; rerun with --replace" >&2
    exit 3
fi

echo "install ${skill_dir} -> ${target}"
if [[ "${dry_run}" -eq 1 ]]; then
    exit 0
fi

tmp_dir="$(mktemp -d "${TMPDIR:-/tmp}/hopper-skill-install.XXXXXX")"
cleanup() {
    rm -rf "${tmp_dir}"
}
trap cleanup EXIT

cp -R "${skill_dir}" "${tmp_dir}/"
find "${tmp_dir}" \( -name '.DS_Store' -o -name '._*' \) -delete
if [[ -e "${target}" ]]; then
    rm -rf "${target}"
fi
mv "${tmp_dir}/${skill_name}" "${target}"
echo "installed ${target}"
