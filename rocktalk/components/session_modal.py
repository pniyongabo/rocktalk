import streamlit as st


@st.dialog("Session settings")
def session_settings(session):
    st.markdown("### Session Options")

    # Rename input
    new_name = st.text_input(
        "Rename session",
        value=session["title"],
        key=f"rename_{session['session_id']}",
    )

    col1, col2 = st.columns(2)
    with col1:
        if st.button(
            "Save",
            key=f"save_{session['session_id']}",
            type="primary",
        ):
            if new_name != session["title"]:
                st.session_state.storage.rename_session(
                    session_id=session["session_id"],
                    new_title=new_name,
                )
            st.rerun()

    with col2:
        if st.button(
            "Cancel",
            key=f"cancel_{session['session_id']}",
        ):
            st.rerun()

    st.divider()

    # Delete option
    if st.button(
        "🗑️ Delete Session",
        key=f"delete_{session['session_id']}",
        type="secondary",
        use_container_width=True,
    ):
        if st.session_state.get(
            f"confirm_delete_{session['session_id']}",
            False,
        ):
            st.session_state.storage.delete_session(session["session_id"])
            if st.session_state.current_session_id == session["session_id"]:
                st.session_state.current_session_id = None
                st.session_state.messages = []
            st.rerun()
        else:
            st.session_state[f"confirm_delete_{session['session_id']}"] = True
            st.warning("Click again to confirm deletion")

    with st.expander("🔍 Debug Information"):
        st.markdown("### Session Details")

        # Display all session information in a formatted way
        st.markdown("#### Basic Info")
        st.code(
            f"""Session ID: {session['session_id']}
    Title: {session['title'][:57] + '...' if len(session['title']) > 57 and not session['title'][57].isspace() else session['title'][:60]}
    Created: {session['created_at']}
    Last Active: {session['last_active']}
    Message Count: {session['message_count']}"""
        )

        # Display metadata if it exists
        if "metadata" in session and session["metadata"]:
            st.markdown("#### Metadata")
            st.json(session["metadata"])

        # Display all raw session data
        st.markdown("#### Raw Session Data")
        st.json(session.to_dict())

        # Add message preview
        st.markdown("#### Recent Messages")
        messages = st.session_state.storage.get_session_messages(session["session_id"])
        if messages:
            for msg in messages[-3:]:  # Show last 3 messages
                st.code(
                    f"""Role: {msg['role']}
    Timestamp: {msg['timestamp']}
    Content: {msg['content'][:100]}{'...' if len(msg['content']) > 100 else ''}"""
                )
