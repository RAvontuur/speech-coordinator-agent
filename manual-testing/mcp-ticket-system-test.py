import argparse
import json
import os
import subprocess
from pathlib import Path


def send(proc, payload):
    proc.stdin.write((json.dumps(payload) + "\n").encode())
    proc.stdin.flush()


def recv(proc):
    line = proc.stdout.readline()
    if not line:
        raise EOFError("server closed stdout")
    return json.loads(line)


def main():
    parser = argparse.ArgumentParser(
        description="Call outdoor-ticket-system-mcp over stdio."
    )
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument(
        "--list-tools",
        action="store_true",
        help="List the tools registered by the MCP server.",
    )
    action.add_argument(
        "--tool",
        help="Name of the MCP tool to call.",
    )
    parser.add_argument(
        "--arguments",
        default="{}",
        help="Tool arguments as a JSON object (default: {}).",
    )
    parser.add_argument(
        "--ticket-root",
        help="Override OUTDOOR_TICKET_ROOT for this server process.",
    )
    args = parser.parse_args()

    try:
        tool_arguments = json.loads(args.arguments)
    except json.JSONDecodeError as error:
        parser.error(f"--arguments must be valid JSON: {error}")
    if not isinstance(tool_arguments, dict):
        parser.error("--arguments must decode to a JSON object")

    repo_root = Path(__file__).resolve().parents[1]
    server_path = repo_root / ".venv" / "bin" / "outdoor-ticket-system-mcp"
    if not server_path.is_file():
        parser.error(f"MCP executable not found: {server_path}; install the package first")

    environment = os.environ.copy()
    if args.ticket_root:
        environment["OUTDOOR_TICKET_ROOT"] = str(Path(args.ticket_root).expanduser())

    print("Starting outdoor-ticket-system-mcp subprocess...")
    proc = subprocess.Popen(
        [str(server_path)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=False,
        env=environment,
    )

    try:
        send(proc, {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "manual-ticket-test", "version": "1.0.0"},
            },
        })
        print("INIT_RESP", json.dumps(recv(proc), indent=2))
        send(proc, {"jsonrpc": "2.0", "method": "notifications/initialized"})

        if args.list_tools:
            send(proc, {"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        else:
            send(proc, {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {"name": args.tool, "arguments": tool_arguments},
            })

        response = recv(proc)
        print("TOOLS_RESP" if args.list_tools else "CALL_RESP", json.dumps(response, indent=2))
    finally:
        if proc.stdin and not proc.stdin.closed:
            proc.stdin.close()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.terminate()
            proc.wait(timeout=5)
        if proc.stderr:
            error_output = proc.stderr.read().decode("utf-8", "replace")
            if error_output.strip():
                print("STDERR", error_output)
        print("EXIT", proc.returncode)


if __name__ == "__main__":
    main()