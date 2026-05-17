#!/usr/bin/env python3
"""Probe Hopper's bundled JSON-lines MCP server."""

from __future__ import annotations

import argparse
import json
import select
import subprocess
import sys
from pathlib import Path
from typing import Any

DEFAULT_SERVER = "/usr/local/bin/HopperMCPServer"
PROTOCOL_VERSION = "2025-03-26"


class JsonLineMCP:
    def __init__(self, command: str, timeout: float) -> None:
        self.command = command
        self.timeout = timeout
        self.next_id = 0
        self.process: subprocess.Popen[str] | None = None

    def __enter__(self) -> "JsonLineMCP":
        self.process = subprocess.Popen(
            [self.command],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        return self

    def __exit__(self, *_exc: Any) -> None:
        if self.process is None:
            return
        self.process.terminate()
        try:
            self.process.wait(timeout=1)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait(timeout=1)

    def request(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        if self.process is None or self.process.stdin is None or self.process.stdout is None:
            raise RuntimeError("MCP process is not running")
        self.next_id += 1
        message = {
            "jsonrpc": "2.0",
            "id": self.next_id,
            "method": method,
            "params": params or {},
        }
        self.process.stdin.write(json.dumps(message, separators=(",", ":")) + "\n")
        self.process.stdin.flush()
        ready, _, _ = select.select([self.process.stdout], [], [], self.timeout)
        if not ready:
            raise TimeoutError(f"timed out waiting for {method}")
        line = self.process.stdout.readline()
        if not line:
            stderr = ""
            if self.process.stderr is not None:
                stderr = self.process.stderr.read()
            raise RuntimeError(f"MCP server closed stdout. stderr: {stderr.strip()}")
        response = json.loads(line)
        if "error" in response:
            raise RuntimeError(response["error"].get("message", response["error"]))
        return response.get("result", {})


def decode_tool_result(result: dict[str, Any]) -> Any:
    text = ""
    for item in result.get("content", []):
        if item.get("type") == "text":
            text = item.get("text", "")
            break
    if not text:
        return result
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--server", default=DEFAULT_SERVER, help="HopperMCPServer path")
    parser.add_argument("--timeout", type=float, default=10.0, help="response timeout in seconds")
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    parser.add_argument(
        "--call-tool",
        default="list_documents",
        help="optional read-only tool to call after tools/list; use 'none' to skip",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    server = Path(args.server)
    if not server.exists():
        print(f"error: Hopper MCP server not found: {server}", file=sys.stderr)
        return 2
    if not server.is_file():
        print(f"error: Hopper MCP server is not a file: {server}", file=sys.stderr)
        return 2

    with JsonLineMCP(str(server), args.timeout) as client:
        initialize = client.request(
            "initialize",
            {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {
                    "name": "hopper-disassembler-analysis-probe",
                    "version": "0.1.0",
                },
            },
        )
        tools = client.request("tools/list")
        tool_names = [tool.get("name", "") for tool in tools.get("tools", [])]
        payload: dict[str, Any] = {
            "server": str(server),
            "initialize": initialize,
            "tool_count": len(tool_names),
            "tools": tool_names,
        }
        if args.call_tool != "none":
            if args.call_tool not in tool_names:
                print(f"error: tool is not exposed by server: {args.call_tool}", file=sys.stderr)
                return 3
            call_result = client.request(
                "tools/call",
                {"name": args.call_tool, "arguments": {}},
            )
            payload["call_tool"] = args.call_tool
            payload["call_result"] = decode_tool_result(call_result)

    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        server_info = payload["initialize"].get("serverInfo", {})
        print(
            f"{server_info.get('name', 'HopperMCPServer')} "
            f"{server_info.get('version', '')} protocol "
            f"{payload['initialize'].get('protocolVersion', '')}"
        )
        print(f"tools ({payload['tool_count']}): {', '.join(payload['tools'])}")
        if "call_tool" in payload:
            print(f"{payload['call_tool']}: {json.dumps(payload['call_result'], sort_keys=True)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
