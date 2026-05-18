#!/usr/bin/env bash
set -euo pipefail

usage() {
    cat <<'EOF'
Usage: install_codex_hopper_mcp.sh [--replace] [--name NAME] [--server PATH]

Probe Hopper's bundled MCP server and register it with Codex CLI using:
  codex mcp add NAME -- PATH

Defaults to HOPPER_MCP_SERVER, Hopper.app's bundled server, or /usr/local/bin/HopperMCPServer.
EOF
}

resolve_server() {
    local explicit="$1"
    local candidate
    if [[ -n "${explicit}" ]]; then
        printf '%s\n' "${explicit}"
        return 0
    fi
    if [[ -n "${HOPPER_MCP_SERVER:-}" && -x "${HOPPER_MCP_SERVER}" ]]; then
        printf '%s\n' "${HOPPER_MCP_SERVER}"
        return 0
    fi
    for candidate in \
        "/Applications/Hopper Disassembler.app/Contents/MacOS/HopperMCPServer" \
        "/usr/local/bin/HopperMCPServer"; do
        if [[ -x "${candidate}" ]]; then
            printf '%s\n' "${candidate}"
            return 0
        fi
    done
    candidate="$(command -v HopperMCPServer 2>/dev/null || true)"
    if [[ -n "${candidate}" && -x "${candidate}" ]]; then
        printf '%s\n' "${candidate}"
        return 0
    fi
    printf '%s\n' "/Applications/Hopper Disassembler.app/Contents/MacOS/HopperMCPServer"
}

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
name="hopper"
server=""
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

server="$(resolve_server "${server}")"
if [[ ! -x "${server}" ]]; then
    echo "error: HopperMCPServer not executable: ${server}" >&2
    exit 2
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
