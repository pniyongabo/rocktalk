import hmac
import os
from typing import Optional

import streamlit as st

DEPLOYED = os.getenv("DEPLOYED", "false").lower() == "true"


def get_password() -> Optional[str]:
    """
    Get password from environment variables or Streamlit secrets
    Returns None if no password is configured, with appropriate warnings
    """
    password = None
    if DEPLOYED:
        password = st.secrets.get("password")
        if not password:
            st.warning("⚠️ No password configured in Streamlit secrets")
    else:
        password = os.getenv("APP_PASSWORD")
        if not password:
            st.warning("⚠️ No APP_PASSWORD set in environment variables")
    return password


def check_password() -> bool:
    """Returns `True` if the user had the correct password."""
    password = get_password()
    if not password:
        st.error("Password not configured")
        st.stop()

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if hmac.compare_digest(st.session_state["password"], password):
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if st.session_state.get("password_correct", False):
        return True

    st.text_input(
        "Password", type="password", on_change=password_entered, key="password"
    )
    # TODO fix this. weird logic?
    if "password_correct" in st.session_state:
        st.error("😕 Password incorrect")
    return False
