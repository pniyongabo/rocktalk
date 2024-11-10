from datetime import datetime
from typing import List

import pandas as pd
import streamlit as st
from devtools import debug
from models.interfaces import ChatExport, ChatMessage


@st.dialog("Interface Options")
def interface_options():
    # TODO: WIP code to delete all sessions
    with st.form("Reset button", clear_on_submit=False):
        st.warning("⚠️ This will delete ALL sessions and messages!")
        if st.form_submit_button("Reset All Data"):
            if st.session_state.get("confirm_reset", False):
                st.session_state.storage.delete_all_sessions()
                st.session_state.current_session_id = None
                st.session_state.messages = []
                st.rerun()
            else:
                st.session_state["confirm_reset"] = True
                st.warning("Click again to confirm reset")

    st.divider()
    with st.form("Session upload form", clear_on_submit=True):

        submitted = st.form_submit_button("UPLOAD!")
        uploaded_file = st.file_uploader(
            "Import Conversation", type=["json"], key="conversation_import"
        )

        if submitted and uploaded_file is not None:
            try:
                import_data = ChatExport.model_validate_json(uploaded_file.getvalue())
                debug(import_data)
                # Create new session
                st.session_state.storage.store_session(import_data.session)

                # Import messages
                for msg in import_data.messages:
                    st.session_state.storage.save_message(msg)

                st.success("Conversation imported successfully!")
                st.session_state.current_session_id = import_data.session.session_id
                uploaded_file.close()
                st.rerun()

            except Exception as e:
                st.error(f"Error importing conversation: {str(e)}")
                raise e


@st.dialog("Session settings")
def session_settings(df_session: pd.Series):
    st.markdown("### Session Options")
    session_id = df_session["session_id"]

    messages: List[ChatMessage] = st.session_state.storage.get_session_messages(
        session_id
    )
    session = st.session_state.storage.get_session_info(session_id)

    export_data = ChatExport(
        session=session, messages=messages, exported_at=datetime.now()
    )

    # Create download button
    st.download_button(
        label="Download Conversation",
        data=export_data.model_dump_json(indent=2),
        file_name=f"conversation_{session_id}.json",
        mime="application/json",
    )

    st.divider()

    # Rename session
    new_name = st.text_input(
        "Rename session",
        value=df_session["title"],
        key=f"rename_{df_session['session_id']}",
    )

    col1, col2 = st.columns(2)
    with col1:
        if st.button(
            "Save",
            key=f"save_{df_session['session_id']}",
            type="primary",
        ):
            if new_name != df_session["title"]:
                st.session_state.storage.rename_session(
                    session_id=session_id,
                    new_title=new_name,
                )
            st.rerun()

    with col2:
        if st.button(
            "Cancel",
            key=f"cancel_{df_session['session_id']}",
        ):
            st.rerun()

    st.divider()

    # Delete option
    if st.button(
        "🗑️ Delete Session",
        key=f"delete_{df_session['session_id']}",
        type="secondary",
        use_container_width=True,
    ):
        if st.session_state.get(
            f"confirm_delete_{df_session['session_id']}",
            False,
        ):
            st.session_state.storage.delete_session(session_id)
            if st.session_state.current_session_id == session_id:
                st.session_state.current_session_id = None
                st.session_state.messages = []
            st.rerun()
        else:
            st.session_state[f"confirm_delete_{df_session['session_id']}"] = True
            st.warning("Click again to confirm deletion")

    with st.expander("🔍 Debug Information"):
        st.markdown("### Session Details")

        # Display all session information in a formatted way
        st.markdown("#### Basic Info")
        st.code(
            f"""Session ID: {df_session['session_id']}
    Title: {df_session['title'][:57] + '...' if len(df_session['title']) > 57 and not df_session['title'][57].isspace() else df_session['title'][:60]}
    Created: {df_session['created_at']}
    Last Active: {df_session['last_active']}
    Message Count: {df_session['message_count']}"""
        )

        # Display metadata if it exists
        if "metadata" in df_session and df_session["metadata"]:
            st.markdown("#### Metadata")
            st.json(df_session["metadata"])

        # Display all raw session data
        st.markdown("#### Raw Session Data")
        st.json(df_session.to_dict())

        # Add message preview
        st.markdown("#### Recent Messages")
        debug(messages)
        recent_messages_index = min(4, len(messages))
        for msg in messages[:recent_messages_index]:
            st.json(msg.model_dump_json())
