#!/usr/bin/env bash
set -euo pipefail

usage() {
    cat <<'EOF'
Usage: install_codex_hopper_mcp.sh [--replace] [--name NAME] [--server PATH]

Probe Hopper's bundled MCP server and register it with Codex CLI using:
  codex mcp add NAME -- PATH
EOF
}

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
name="hopper"
server="/usr/local/bin/HopperMCPServer"
replace=0

while [[ $# -gt 0 ]]; do
    case "$1" in
        --replace)
            replace=1
            shift
            ;;
        --name)
            name="$2"
            shift 2
            ;;
        --server)
            server="$2"
            shift 2
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

if [[ ! -x "${server}" ]]; then
    app_server="/Applications/Hopper Disassembler.app/Contents/MacOS/HopperMCPServer"
    if [[ -x "${app_server}" ]]; then
        server="${app_server}"
    else
        echo "error: HopperMCPServer not executable: ${server}" >&2
        exit 2
    fi
fi

python3 "${script_dir}/hopper_mcp_probe.py" --server "${server}" --call-tool none >/dev/null

if ! command -v codex >/dev/null 2>&1; then
    echo "error: codex CLI not found in PATH" >&2
    echo "generic MCP command: ${server}" >&2
    exit 2
fi

if codex mcp get "${name}" >/dev/null 2>&1; then
    if [[ "${replace}" -ne 1 ]]; then
        echo "error: Codex MCP server '${name}' already exists; rerun with --replace" >&2
        exit 3
    fi
    codex mcp remove "${name}" >/dev/null
fi

codex mcp add "${name}" -- "${server}"
codex mcp get "${name}"
