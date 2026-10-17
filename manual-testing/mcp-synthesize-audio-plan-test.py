import argparse
import json
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
        description="Call outdoor-speech-mcp.synthesize_audio_plan over stdio."
    )
    parser.add_argument(
        "--filename",
        required=True,
        help="Source file or directory to synthesize.",
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Directory where the generated audio plan will be written.",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    server_path = repo_root / ".venv" / "bin" / "outdoor-speech-mcp"

    print('Starting outdoor-speech-mcp subprocess...')
    proc = subprocess.Popen(
        [str(server_path)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=False,
    )
    print('Subprocess started, PID:', proc.pid)

    print('Sending initialize request...')
    send(proc, {
        'jsonrpc': '2.0',
        'id': 1,
        'method': 'initialize',
        'params': {
            'protocolVersion': '2024-11-05',
            'capabilities': {},
            'clientInfo': {'name': 'cli-test', 'version': '1.0.0'}
        }
    })
    print('INIT_RESP', recv(proc))

    send(proc, {'jsonrpc': '2.0', 'method': 'notifications/initialized'})

    send(proc, {
        'jsonrpc': '2.0',
        'id': 2,
        'method': 'tools/call',
        'params': {
            'name': 'synthesize_audio_plan',
            'arguments': {'filename': args.filename, 'output_dir': args.output_dir},
        }
    })
    resp = recv(proc)
    print('CALL_RESP', json.dumps(resp, indent=2))

    proc.stdin.close()
    proc.wait(timeout=10)
    print('EXIT', proc.returncode)
    if proc.stderr:
        err = proc.stderr.read().decode('utf-8', 'replace')
        if err.strip():
            print('STDERR', err)


if __name__ == "__main__":
    main()