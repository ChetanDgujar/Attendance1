from http.server import BaseHTTPRequestHandler
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import data_provider

class handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

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

        res_body = json.dumps(response_data).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(res_body)))
        self.end_headers()
        self.wfile.write(res_body)

app = handler
application = handler
