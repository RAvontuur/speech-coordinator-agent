import json, subprocess, sys

print('Starting outdoor-speech-mcp subprocess...')
proc = subprocess.Popen(
    ['/Users/ravontuur/speech-coordinator-agent/.venv/bin/outdoor-speech-mcp'],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=False,
)
print('Subprocess started, PID:', proc.pid)

def send(payload):
    data = json.dumps(payload, separators=(',', ':')).encode('utf-8')
    header = f'Content-Length: {len(data)}\r\n\r\n'.encode('ascii')
    proc.stdin.write(header + data)
    proc.stdin.flush()


def send(payload):
    proc.stdin.write((json.dumps(payload) + "\n").encode())
    proc.stdin.flush()


def recv():
    line = proc.stdout.readline()
    if not line:
        raise EOFError("server closed stdout")
    return json.loads(line)

print('Sending initialize request...')
send({
    'jsonrpc': '2.0',
    'id': 1,
    'method': 'initialize',
    'params': {
        'protocolVersion': '2024-11-05',
        'capabilities': {},
        'clientInfo': {'name': 'cli-test', 'version': '1.0.0'}
    }
})
print('INIT_RESP', recv())

send({'jsonrpc': '2.0', 'method': 'notifications/initialized'})

send({
    'jsonrpc': '2.0',
    'id': 2,
    'method': 'tools/call',
    'params': {'name': 'synthesize_audio_plan', 'arguments': {'filename': '.', 'output_dir': 'test/plan4'}}
})
resp = recv()
print('CALL_RESP', json.dumps(resp, indent=2))

proc.stdin.close()
proc.wait(timeout=10)
print('EXIT', proc.returncode)
if proc.stderr:
    err = proc.stderr.read().decode('utf-8', 'replace')
    if err.strip():
        print('STDERR', err)