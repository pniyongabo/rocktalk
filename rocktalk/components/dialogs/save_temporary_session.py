import streamlit as st
from config.settings import SettingsManager


@st.dialog("Save Temporary Session")
def save_temporary_session():
    """Render option to save temporary session"""
    settings = SettingsManager(storage=st.session_state.storage)
    settings.render_save_temporary_session()
