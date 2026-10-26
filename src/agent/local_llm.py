"""Optional Local LLM Adapter (e.g. Ollama) for classroom decision support.
Disabled by default, fails gracefully with zero cloud dependency and automatic heuristic fallback.
"""
from typing import Dict, Any, Optional
import json
import urllib.request
import urllib.error


class LocalLLMAdapter:
    """Interfaces with a local offline LLM instance (Ollama, LM Studio, etc.)."""

    def __init__(
        self,
        enabled: bool = False,
        provider: str = "ollama",
        endpoint: str = "http://localhost:11434",
        model: str = "llama3:8b",
        timeout_sec: float = 4.0,
    ):
        self.enabled = enabled
        self.provider = provider
        self.endpoint = endpoint.rstrip("/")
        self.model = model
        self.timeout_sec = timeout_sec

    def is_available(self) -> bool:
        """Checks if local LLM service is running and responsive."""
        if not self.enabled:
            return False
        try:
            url = f"{self.endpoint}/api/tags" if self.provider == "ollama" else f"{self.endpoint}/v1/models"
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=1.5) as resp:
                return resp.status == 200
        except Exception:
            return False

    def generate_suggestion(self, prompt: str) -> Optional[str]:
        """Calls local LLM with prompt; returns None on any network/connection failure."""
        if not self.enabled:
            return None

        try:
            if self.provider == "ollama":
                url = f"{self.endpoint}/api/generate"
                payload = {
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.3, "num_predict": 100},
                }
            else:
                url = f"{self.endpoint}/v1/chat/completions"
                payload = {
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 100,
                    "temperature": 0.3,
                }

            req_data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(url, data=req_data, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=self.timeout_sec) as resp:
                if resp.status == 200:
                    res_json = json.loads(resp.read().decode("utf-8"))
                    if self.provider == "ollama":
                        return res_json.get("response", "").strip()
                    else:
                        choices = res_json.get("choices", [])
                        if choices:
                            return choices[0].get("message", {}).get("content", "").strip()
        except Exception:
            # Graceful fallback: return None without raising exception
            return None

        return None
