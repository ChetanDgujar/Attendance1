"""Unified Entrypoint CLI for Multimodal Attendance & Engagement Agent.
Provides commands to run demonstrations, launch the interactive web dashboard,
execute unit tests, and export classroom reports.
"""
import argparse
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import SystemConfig
from src.web.server import ClassroomIntelligenceServer
from scripts.run_demo import run_classroom_simulation
from scripts.generate_sample_data import generate_all


def run_dashboard(host: str = "127.0.0.1", port: int = 8080):
    print("=" * 80)
    print("🎓 LAUNCHING CLASSROOM INTELLIGENCE DASHBOARD")
    print("=" * 80)
    config = SystemConfig.load()
    config.server.host = host
    config.server.port = port

    server = ClassroomIntelligenceServer(config)
    url = server.start(auto_start_simulation=True)

    print(f"\n🚀 Web Dashboard live at: {url}")
    print("   Open this URL in Google Chrome, Microsoft Edge, or Mozilla Firefox.")
    print("   Press Ctrl+C to terminate the server.\n")

    try:
        while True:
            import time
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping Classroom Intelligence Server...")
        server.stop()
        print("Server stopped.")


def run_tests():
    print("=" * 80)
    print("🧪 RUNNING SUITE OF VERIFICATION & UNIT TESTS")
    print("=" * 80)
    loader = unittest.TestLoader()
    suite = loader.discover(start_dir=str(ROOT / "tests"), pattern="test_*.py")
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)


def main():
    parser = argparse.ArgumentParser(
        description="Multimodal Attendance & Engagement Agent - AI Classroom Intelligence System"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # Command: demo
    demo_p = subparsers.add_parser("demo", help="Run simulated end-to-end classroom session in terminal")
    demo_p.add_argument("--duration", type=float, default=30.0, help="Duration in seconds (default: 30)")

    # Command: dashboard
    dash_p = subparsers.add_parser("dashboard", help="Start the interactive web dashboard server")
    dash_p.add_argument("--host", type=str, default="127.0.0.1", help="Host interface (default: 127.0.0.1)")
    dash_p.add_argument("--port", type=int, default=8080, help="Port (default: 8080)")

    # Command: test
    subparsers.add_parser("test", help="Run automated test suite")

    # Command: sample-data
    subparsers.add_parser("sample-data", help="Generate sample roster and audio WAV file")

    args = parser.parse_args()

    if args.command == "demo":
        run_classroom_simulation(duration_sec=args.duration)
    elif args.command == "dashboard":
        run_dashboard(host=args.host, port=args.port)
    elif args.command == "test":
        run_tests()
    elif args.command == "sample-data":
        generate_all()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
