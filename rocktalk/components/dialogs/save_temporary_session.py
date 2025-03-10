import streamlit as st
from app_context import AppContext
from config.settings import SettingsManager


@st.dialog("Save Temporary Session")
def save_temporary_session(app_context: AppContext):
    """Render option to save temporary session"""
    settings = SettingsManager(app_context=app_context)
    settings.render_save_temporary_session()
