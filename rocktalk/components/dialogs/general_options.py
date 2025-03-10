import streamlit as st
from app_context import AppContext
from config.settings import SettingsManager


@st.dialog("Settings")
def general_options(app_context: AppContext):
    """Dialog for global application settings and data management"""
    settings = SettingsManager(app_context=app_context)

    tab1, tab2, tab3, tab4 = st.tabs(
        [
            "Model Settings",
            "Import/Export",
            "Credentials",
            "Log Viewer",
        ]
    )

    with tab1:
        settings.render_settings_dialog()
    with tab2:
        settings._render_import_export()
    with tab3:
        settings.render_refresh_credentials()
    with tab4:
        settings.render_log_viewer()
