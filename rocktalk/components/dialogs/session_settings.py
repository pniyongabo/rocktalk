
import pandas as pd
import streamlit as st
from config.settings import SettingsManager


@st.dialog("Session Settings")
def session_settings(df_session: pd.Series):
    session_id = df_session["session_id"]
    storage = st.session_state.storage
    session = storage.get_session(session_id)

    settings = SettingsManager(session=session, storage=storage)

    tab1, tab2, tab3 = st.tabs(["Settings", "Export", "Debug Info"])

    with tab1:
        settings.render_session_settings()
        settings.render_session_actions()
    with tab2:
        settings._render_import_export()
    with tab3:
        settings._render_debug_tab()


# def _render_settings_tab(
#     session: ChatSession, session_id: str, storage: StorageInterface
# ):
#     """Render the main settings tab"""
#     st.subheader("Session Settings")

#     # Session name
#     _render_session_name(session, session_id, storage)

#     # Configuration
#     SettingsManager(session=session, storage=storage).render_settings_dialog()
#     # _render_configuration_section(session, storage)

#     st.divider()
#     # Delete session
#     _render_delete_button(session_id)


# def _render_session_name(
#     session: ChatSession, session_id: str, storage: StorageInterface
# ):
#     """Handle session name editing"""
#     new_name = st.text_input("Name", session.title)
#     if new_name != session.title and st.button("Save Name"):
#         storage.rename_session(session_id, new_name)
#         st.rerun()


# def _render_configuration_section(session: ChatSession, storage: StorageInterface):
#     """Render configuration options including templates"""
#     # Initialize temp config if needed
#     if (
#         "temp_llm_config" not in st.session_state
#         or st.session_state.temp_llm_config is None
#     ):
#         st.session_state.temp_llm_config = session.config

#     # Template selection
#     templates = storage.get_chat_templates()
#     template_options = [(t.template_id, t.name) for t in templates]
#     template_options.append(("custom", "Custom"))

#     selected = st.selectbox(
#         "Template",
#         options=[t[0] for t in template_options],
#         format_func=lambda x: dict(template_options)[x],
#     )

#     # Show configuration based on selection
#     if selected != "custom":
#         template = storage.get_chat_template(selected)
#         SettingsManager.render_config_summary(template.config)
#         st.session_state.temp_llm_config = template.config.model_copy(deep=True)
#     else:
#         st.subheader("Model Configuration")
#         SettingsManager.render_model_selector()

#         st.subheader("Parameters")
#         SettingsManager(session=session, storage=storage).render_parameter_controls()

#     # Apply configuration button
#     if st.button("Apply Configuration"):
#         session.config = st.session_state.temp_llm_config
#         storage.update_session(session)
#         st.session_state.llm.update_config(st.session_state.temp_llm_config)
#         SettingsManager.clear_cached_settings_vars()
#         st.rerun()


# def _render_delete_button(session_id: str):
#     """Handle session deletion with confirmation"""
#     if st.button(":material/delete: Delete Session", type="secondary"):
#         if st.session_state.get(f"confirm_delete_{session_id}", False):
#             storage = st.session_state.storage
#             storage.delete_session(session_id)
#             if st.session_state.current_session_id == session_id:
#                 st.session_state.current_session_id = None
#                 st.session_state.messages = []
#             st.rerun()
#         else:
#             st.session_state[f"confirm_delete_{session_id}"] = True
#             st.warning("Click again to confirm deletion")


# def _render_export_tab(session: ChatSession, messages: List[ChatMessage]):
#     """Render the export functionality tab"""
#     export_data = ChatExport(
#         session=session, messages=messages, exported_at=datetime.now()
#     )

#     st.download_button(
#         label=":material/download: Export Conversation",
#         data=export_data.model_dump_json(indent=2),
#         file_name=f"conversation_{session.session_id}.json",
#         mime="application/json",
#     )


# def _render_debug_tab(
#     session: ChatSession,
#     session_id: str,
#     df_session: pd.Series,
#     messages: List[ChatMessage],
# ):
#     """Render debug information tab"""
#     st.markdown("### 🔍 Debug Information")

#     # Basic info
#     st.markdown("#### Basic Info")
#     st.code(
#         f"""Session ID: {session_id}
# Title: {session.title[:57] + '...' if len(session.title) > 57 else session.title}
# Created: {session.created_at}
# Last Active: {session.last_active}"""
#     )

#     # Raw session data
#     st.markdown("#### Raw Session Data")
#     st.json(df_session.to_dict())

#     # Recent messages
#     st.markdown("#### Recent Messages")
#     _render_recent_messages(messages)


# def _render_recent_messages(messages: List[ChatMessage]):
#     """Render recent messages with truncated image data"""
#     for msg in messages[:4]:  # Show up to 4 recent messages
#         msg_dict = msg.model_dump()

#         # Truncate image data
#         if isinstance(msg_dict.get("content"), list):
#             for item in msg_dict["content"]:
#                 if isinstance(item, dict) and item.get("type") == "image":
#                     if "data" in item.get("source", {}):
#                         item["source"]["data"] = (
#                             item["source"]["data"][:10] + "...[truncated]"
#                         )

#         st.json(msg_dict)
