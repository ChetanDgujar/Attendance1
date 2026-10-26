"""Optional Streamlit Interface for Multimodal Attendance & Engagement Agent.
Can be executed when Streamlit and Plotly are installed:
`streamlit run src/web/app_streamlit.py`
"""
import sys
from pathlib import Path

# Add project root to path
ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    import streamlit as st
    STREAMLIT_AVAILABLE = True
except ImportError:
    STREAMLIT_AVAILABLE = False


def main():
    if not STREAMLIT_AVAILABLE:
        print("Streamlit is not installed. Use the standalone web dashboard instead:\n  python main.py dashboard")
        return

    st.set_page_config(
        page_title="Multimodal Attendance & Engagement Agent",
        page_icon="🎓",
        layout="wide",
    )

    st.title("🎓 Multimodal Attendance & Engagement Agent")
    st.markdown("AI-Powered, Privacy-Preserving Classroom Intelligence System")

    st.sidebar.header("Classroom Control Panel")
    privacy_mode = st.sidebar.checkbox("Enable Privacy Anonymization", value=False)
    fps = st.sidebar.slider("Sampling FPS", 1, 10, 5)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Avg Engagement", "78.4%", "+4.2%")
    with col2:
        st.metric("Sustained Attendance", "85.7%", "6/7 Present")
    with col3:
        st.metric("Acoustic Dynamic", "Discussion", "Speech 45%")
    with col4:
        st.metric("AI Pedagogical Alerts", "2 Active", "Pacing Check")

    st.subheader("💡 Real-Time AI Teaching Suggestions")
    st.info("Continuous monologue detected > 90s. Suggestion: Launch a 2-minute Think-Pair-Share check-in.")

    st.subheader("📋 Sustained Attendance Records")
    sample_data = [
        {"ID": "STU-101", "Name": "Learner-A1" if privacy_mode else "Aarav Sharma", "Status": "PRESENT", "Active": "54.2s", "Ratio": "90.3%"},
        {"ID": "STU-102", "Name": "Learner-B2" if privacy_mode else "Priya Patel", "Status": "PRESENT", "Active": "58.1s", "Ratio": "96.8%"},
        {"ID": "STU-103", "Name": "Learner-C3" if privacy_mode else "Rohan Mehta", "Status": "PRESENT", "Active": "49.0s", "Ratio": "81.6%"},
        {"ID": "STU-106", "Name": "Learner-D4" if privacy_mode else "Diya Nair", "Status": "TARDY", "Active": "42.0s", "Ratio": "70.0%"},
        {"ID": "GUEST-999", "Name": "Passerby", "Status": "TRANSIENT_IGNORED", "Active": "3.0s", "Ratio": "5.0%"},
    ]
    st.table(sample_data)


if __name__ == "__main__":
    main()
