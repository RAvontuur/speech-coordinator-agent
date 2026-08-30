import json
from http.server import BaseHTTPRequestHandler, HTTPServer

from coordinator import Coordinator


class CoordinatorHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/run":
            self.send_error(404, "Not found")
            return

        content_length = int(self.headers.get("Content-Length", 0))
        try:
            payload = json.loads(self.rfile.read(content_length))
        except json.JSONDecodeError:
            self.send_json({"error": "request body must be valid JSON"}, 400)
            return

        message = payload.get("message") if isinstance(payload, dict) else None

        if not isinstance(message, str) or not message.strip():
            self.send_json({"error": "message must be a non-empty string"}, 400)
            return

        submitted_text = Coordinator().run(message)
        self.send_json({"text": submitted_text})

    def send_json(self, payload, status=200):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def run_server(host="0.0.0.0", port=8000):
    HTTPServer((host, port), CoordinatorHandler).serve_forever()


if __name__ == "__main__":
    run_server()