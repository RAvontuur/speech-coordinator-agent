import json
import os
import pathlib
from http.server import BaseHTTPRequestHandler, HTTPServer

from coordinator import Coordinator
from speech_service import SpeechService


class CoordinatorHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path == "/run":
            self._handle_run()
        elif self.path == "/synthesize":
            self._handle_synthesize()
        else:
            self.send_error(404, "Not found")

    def _handle_run(self):
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

    def _handle_synthesize(self):
        content_length = int(self.headers.get("Content-Length", 0))
        try:
            payload = json.loads(self.rfile.read(content_length))
        except json.JSONDecodeError:
            self.send_json({"error": "request body must be valid JSON"}, 400)
            return

        filename = payload.get("filename") if isinstance(payload, dict) else None

        if not isinstance(filename, str) or not filename.strip():
            self.send_json({"error": "filename must be a non-empty string"}, 400)
            return

        # Validate file exists and is readable
        if not os.path.isfile(filename):
            self.send_json({"error": f"file not found: {filename}"}, 404)
            return

        # Read text from file
        try:
            with open(filename, "r", encoding="utf-8") as f:
                text = f.read()
        except (OSError, IOError) as e:
            self.send_json({"error": f"failed to read file: {str(e)}"}, 400)
            return

        if not text.strip():
            self.send_json({"error": "file is empty"}, 400)
            return

        # Generate output path with .wav extension
        input_path = pathlib.Path(filename)
        output_path = input_path.with_suffix(".wav")

        # Synthesize and save
        try:
            speech = SpeechService()
            speech.text_to_speech_file(text, str(output_path))
            self.send_json({"audio_file": str(output_path)})
        except Exception as e:
            self.send_json({"error": f"synthesis failed: {str(e)}"}, 500)

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