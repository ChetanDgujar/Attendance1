"""Integration tests for SessionOrchestrator and HTTP API handler logic."""
import unittest
import io
import json
import time
from pathlib import Path
from src.config import SystemConfig
from src.web.server import SessionOrchestrator, ClassroomIntelligenceHandler


class MockSocket:
    """Mock socket for testing BaseHTTPRequestHandler in-memory without OS network sockets."""

    def __init__(self, raw_input: bytes = b""):
        self.rfile = io.BytesIO(raw_input)
        self.wfile = io.BytesIO()

    def makefile(self, mode: str, *args, **kwargs):
        if "b" in mode:
            if "r" in mode:
                return self.rfile
            else:
                return self.wfile
        return self.rfile

    def sendall(self, data):
        self.wfile.write(data)


class TestServerIntegration(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.config = SystemConfig.load()
        cls.orchestrator = SessionOrchestrator(cls.config)
        cls.static_dir = Path(__file__).resolve().parent.parent / "src" / "web" / "static"

        # Bind to handler class
        ClassroomIntelligenceHandler.orchestrator = cls.orchestrator
        ClassroomIntelligenceHandler.static_dir = cls.static_dir

        # Run simulation for a couple ticks
        cls.orchestrator.start()
        time.sleep(1.2)

    @classmethod
    def tearDownClass(cls):
        cls.orchestrator.is_running = False

    def _execute_request(self, method: str, path: str, body: bytes = b"") -> tuple:
        raw = f"{method} {path} HTTP/1.1\r\nHost: localhost\r\nContent-Length: {len(body)}\r\n\r\n".encode("utf-8") + body
        sock = MockSocket(raw)

        # Instantiate handler with mock client_address and server
        handler = ClassroomIntelligenceHandler(sock, ("127.0.0.1", 12345), None)
        sock.wfile.seek(0)
        response_bytes = sock.wfile.read()

        # Parse HTTP response
        header_part, _, body_part = response_bytes.partition(b"\r\n\r\n")
        status_line = header_part.split(b"\r\n")[0].decode("utf-8")
        status_code = int(status_line.split()[1]) if len(status_line.split()) > 1 else 0
        return status_code, body_part

    def test_status_endpoint(self):
        status, body = self._execute_request("GET", "/api/status")
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertTrue(data["running"])
        self.assertGreater(data["session_time_seconds"], 0.0)

    def test_telemetry_endpoint(self):
        status, body = self._execute_request("GET", "/api/telemetry")
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertIn("average_engagement", data)
        self.assertIn("acoustic_state", data)
        self.assertIn("tracks", data)

    def test_attendance_endpoint(self):
        status, body = self._execute_request("GET", "/api/attendance")
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertIn("summary", data)
        self.assertIn("records", data)
        self.assertGreater(len(data["records"]), 0)

    def test_timeline_endpoint(self):
        status, body = self._execute_request("GET", "/api/timeline")
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertIn("timeline", data)
        self.assertIsInstance(data["timeline"], list)

    def test_suggestions_endpoint(self):
        status, body = self._execute_request("GET", "/api/suggestions")
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertIn("suggestions", data)

    def test_audit_endpoint(self):
        status, body = self._execute_request("GET", "/api/audit")
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertIn("audit", data)
        self.assertIn("markdown", data["audit"])

    def test_csv_download(self):
        status, body = self._execute_request("GET", "/api/download/attendance.csv")
        self.assertEqual(status, 200)
        content = body.decode("utf-8")
        self.assertIn("Student ID", content)
        self.assertIn("Presence Ratio", content)

    def test_toggle_privacy_action(self):
        status, body = self._execute_request("POST", "/api/action", json.dumps({"action": "toggle_privacy"}).encode("utf-8"))
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertTrue(data["success"])
        self.assertIn("anonymize_privacy", data)


if __name__ == "__main__":
    unittest.main()
