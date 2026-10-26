"""Interactive command-line tool to mark students Present, Absent, Late, or Excused."""
from pathlib import Path
import argparse
import sys

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.storage.database import DatabaseManager


def mark_student(student_id: str, new_status: str, session_id: str = None):
    db = DatabaseManager(str(ROOT / "data" / "classroom.db"))
    
    # If no session specified, pick the latest session
    if not session_id:
        sessions = db.list_sessions(limit=1)
        if not sessions:
            print("❌ No sessions found in database. Run 'python scripts/generate_demo_data.py' first.")
            return
        session_id = sessions[0]["session_id"]
        session_name = sessions[0]["name"]
    else:
        sess = db.get_session(session_id)
        session_name = sess["name"] if sess else session_id

    status_clean = new_status.upper()
    valid_statuses = ["PRESENT", "ABSENT", "LATE", "EXCUSED", "TRANSIENT_IGNORED"]
    if status_clean not in valid_statuses:
        print(f"❌ Invalid status '{new_status}'. Must be one of: {', '.join(valid_statuses)}")
        return

    updated = db.update_attendance_status(session_id, student_id, status_clean)
    if updated:
        print("=" * 60)
        print(f"✅ SUCCESS: Student '{student_id}' marked as [{status_clean}]")
        print(f"   Session: {session_name} ({session_id})")
        print("=" * 60)
    else:
        print(f"⚠️ Could not find record for student '{student_id}' in session '{session_id}'.")


def interactive_menu():
    db = DatabaseManager(str(ROOT / "data" / "classroom.db"))
    sessions = db.list_sessions(limit=5)
    if not sessions:
        print("❌ No sessions found in database. Run 'python scripts/generate_demo_data.py' first.")
        return

    latest_session = sessions[0]
    session_id = latest_session["session_id"]
    print("=" * 60)
    print(f"📋 CLASSROOM ATTENDANCE MARKER")
    print(f"   Active Session: {latest_session['name']} ({session_id})")
    print("=" * 60)

    records = db.get_attendance_records(session_id)
    if not records:
        print("No student records found in this session.")
        return

    print("\nCurrent Roll Call:")
    for idx, r in enumerate(records, 1):
        print(f"  {idx}. [{r['status']:<9}] {r['student_id']:<8} - {r['display_name']}")

    print("\n" + "-" * 60)
    try:
        choice = input("Enter student number to change status (or 'q' to quit): ").strip()
        if choice.lower() == 'q' or not choice:
            return

        choice_idx = int(choice) - 1
        if not (0 <= choice_idx < len(records)):
            print("Invalid student number.")
            return

        student = records[choice_idx]
        print(f"\nSelected: {student['display_name']} ({student['student_id']}) - Current Status: {student['status']}")
        print("Choose New Status:")
        print("  1. PRESENT")
        print("  2. ABSENT")
        print("  3. LATE")
        print("  4. EXCUSED")

        s_choice = input("Enter option (1-4): ").strip()
        status_map = {"1": "PRESENT", "2": "ABSENT", "3": "LATE", "4": "EXCUSED"}
        new_status = status_map.get(s_choice)

        if not new_status:
            print("Invalid option.")
            return

        mark_student(student["student_id"], new_status, session_id)

    except KeyboardInterrupt:
        print("\nExiting.")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Mark attendance for a student")
    parser.add_argument("--student", type=str, default=None, help="Student ID (e.g. STU-107)")
    parser.add_argument("--status", type=str, default=None, help="New status: PRESENT, ABSENT, LATE, EXCUSED")
    parser.add_argument("--session", type=str, default=None, help="Optional Session ID")

    args = parser.parse_args()

    if args.student and args.status:
        mark_student(args.student, args.status, args.session)
    else:
        interactive_menu()
