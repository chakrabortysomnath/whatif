import streamlit as st
import hmac

def check_password() -> bool:
    """Returns True if the user entered the correct password."""

    def password_entered():
        if hmac.compare_digest(
            st.session_state["password"],
            st.secrets["PASSWORD"]
        ):
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if st.session_state.get("password_correct", False):
        return True

    # Login UI
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("""
        <div style="text-align:center;padding:40px 0 20px">
            <div style="font-size:36px;margin-bottom:8px">📊</div>
            <div style="font-size:24px;font-weight:600;margin-bottom:4px">Portfolio What-If</div>
            <div style="font-size:14px;color:#888;margin-bottom:28px">Personal financial scenario modeller</div>
        </div>
        """, unsafe_allow_html=True)
        st.text_input(
            "Password",
            type="password",
            on_change=password_entered,
            key="password",
            placeholder="Enter access password",
            label_visibility="collapsed"
        )
        if "password_correct" in st.session_state:
            st.error("Incorrect password. Please try again.")
    return False
