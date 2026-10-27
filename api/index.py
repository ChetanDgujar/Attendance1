"""Vercel Serverless Function entrypoint for Multimodal Attendance & Engagement Agent.
Handles all /api/* requests and static web dashboard serving on Vercel.
"""
from http.server import BaseHTTPRequestHandler
from pathlib import Path
import json
import os
import sys
import time
import urllib.parse

# Ensure api directory and project root are on sys.path
API_DIR = Path(__file__).resolve().parent
ROOT = API_DIR.parent
for p in [str(API_DIR), str(ROOT)]:
    if p not in sys.path:
        sys.path.insert(0, p)

import data_provider


class handler(BaseHTTPRequestHandler):
    """Vercel serverless handler for web dashboard and /api/* routes."""

    def log_message(self, format, *args):
        pass

    def _serve_file(self, filename: str, content_type: str):
        search_paths = [
            ROOT / "public" / filename,
            ROOT / filename,
            API_DIR / filename,
            ROOT / "src" / "web" / "static" / filename,
            Path.cwd() / "public" / filename,
            Path.cwd() / filename,
        ]
        for p in search_paths:
            try:
                if p.exists() and p.is_file():
                    content = p.read_bytes()
                    self.send_response(200)
                    self.send_header("Content-Type", content_type)
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.send_header("Content-Length", str(len(content)))
                    self.send_header("Cache-Control", "public, max-age=3600")
                    self.end_headers()
                    self.wfile.write(content)
                    return
            except Exception:
                continue

        self.send_response(404)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(f"File {filename} not found on server.".encode("utf-8"))

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        # Read from Vercel forwarding headers or self.path
        raw_uri = self.headers.get("x-forwarded-uri") or self.headers.get("x-matched-path") or self.path
        parsed = urllib.parse.urlparse(raw_uri)
        path = parsed.path.rstrip("/")
        if not path:
            path = "/"

        # Check for query param fallback ?route=/api/status
        qs = urllib.parse.parse_qs(parsed.query)
        if "route" in qs and qs["route"]:
            path = qs["route"][0].rstrip("/")

        # Static assets
        if path in ("/", "", "/index.html"):
            self._serve_file("index.html", "text/html; charset=utf-8")
            return
        elif path == "/style.css" or path.endswith("/style.css"):
            self._serve_file("style.css", "text/css; charset=utf-8")
            return
        elif path == "/app.js" or path.endswith("/app.js"):
            self._serve_file("app.js", "application/javascript; charset=utf-8")
            return
        elif path == "/favicon.ico":
            self.send_response(204)
            self.end_headers()
            return

        # API Endpoints
        if "status" in path:
            self._send_json(data_provider.get_status_payload())
        elif "telemetry" in path:
            self._send_json(data_provider.get_telemetry_payload())
        elif "attendance.csv" in path:
            self._handle_csv_download()
        elif "attendance" in path:
            self._send_json(data_provider.get_attendance_payload())
        elif "timeline" in path:
            self._send_json(data_provider.get_timeline_payload())
        elif "suggestions" in path:
            self._send_json(data_provider.get_suggestions_payload())
        elif "audit" in path:
            self._send_json(data_provider.get_audit_payload())
        elif not path.startswith("/api"):
            # SPA fallback
            self._serve_file("index.html", "text/html; charset=utf-8")
        else:
            self.send_error(404, f"API endpoint {path} not found")

    def do_POST(self):
        content_len = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_len).decode("utf-8") if content_len > 0 else "{}"
        try:
            data = json.loads(body)
        except Exception:
            data = {}

        action = data.get("action")
        response_data = {"success": True}

        if action == "toggle_privacy":
            mode = data_provider.toggle_privacy_mode()
            response_data["anonymize_privacy"] = mode
        elif action == "override_attendance":
            student_id = data.get("student_id")
            new_status = data.get("status", "PRESENT")
            data_provider.set_manual_override(student_id, new_status)
            response_data["student_id"] = student_id
            response_data["status"] = new_status
        else:
            response_data["message"] = f"Action {action} acknowledged."

        self._send_json(response_data)

    def _handle_csv_download(self):
        csv_text = "Student ID,Display Name,Status,First Seen (s),Last Seen (s),Active Duration (s),Presence Ratio,Confidence\n"
        csv_text += "STU-101,Aarav Sharma,PRESENT,0.0,60.0,60.0,100.0%,0.99\n"
        csv_text += "STU-102,Priya Patel,PRESENT,0.0,58.0,58.0,97.0%,0.99\n"
        csv_text += "STU-107,Ishaan Gupta,ABSENT,N/A,N/A,0.0,0.0%,1.00\n"
        csv_text += "GUEST-999,Hallway Passerby,TRANSIENT_IGNORED,4.0,7.2,3.2,5.0%,0.90\n"

        csv_bytes = csv_text.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/csv")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Disposition", 'attachment; filename="attendance.csv"')
        self.send_header("Content-Length", str(len(csv_bytes)))
        self.end_headers()
        self.wfile.write(csv_bytes)

    def _send_json(self, data: dict):
        body = json.dumps(data).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


# Top-level exports required by Vercel Python runtime
app = handler
application = handler
