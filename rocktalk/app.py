from typing import cast
import boto3
import dotenv
import streamlit as st
from datetime import datetime
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from langchain.schema import AIMessage, HumanMessage
from langchain_aws import ChatBedrockConverse
from langchain_core.messages.ai import AIMessageChunk
from storage.sqlite_storage import SQLiteChatStorage
from datetime import datetime, timedelta
import pandas as pd

# Load environment variables
dotenv.load_dotenv()

# Set page configuration
st.set_page_config(page_title="RockTalk", page_icon="🪨", layout="wide")

# Initialize storage in session state
if "storage" not in st.session_state:
    st.session_state.storage = SQLiteChatStorage(db_path="chat_database.db")
    print("--- Storage initialized ---")

if "open_menu_id" not in st.session_state:
    st.session_state.open_menu_id = None

# Initialize LLM object in session state
if "llm" not in st.session_state:
    st.session_state.llm = ChatBedrockConverse(
        region_name="us-west-2",
        model="anthropic.claude-3-sonnet-20240229-v1:0",
        temperature=0,
        max_tokens=None,
    )
    print("--- LLM initialized ---")


# Initialize session state variables
if "last_update" not in st.session_state:
    st.session_state.last_update = datetime.now()

# Create sidebar for session management
with st.sidebar:
    st.title("Chat Sessions")

    # New Chat button at the top
    if st.button("New Chat", type="primary"):
        st.session_state.messages = []
        st.session_state.current_session_id = None
        st.rerun()

    # Get recent sessions
    recent_sessions = st.session_state.storage.get_recent_sessions(limit=100)

    if recent_sessions:
        df_sessions = pd.DataFrame(recent_sessions)
        df_sessions['last_active'] = pd.to_datetime(df_sessions['last_active'])
        
        # Sort sessions by date in descending order (newest first)
        df_sessions = df_sessions.sort_values('last_active', ascending=False)
        
        now = pd.Timestamp.now()
        today = now.date()

        # Create date masks for each group
        today_mask = df_sessions['last_active'].dt.date == today
        yesterday_mask = df_sessions['last_active'].dt.date == (today - timedelta(days=1))
        this_week_mask = (df_sessions['last_active'].dt.date > (today - timedelta(days=7))) & \
                        (~today_mask) & (~yesterday_mask)
        this_month_mask = (df_sessions['last_active'].dt.date > (today - timedelta(days=30))) & \
                        (~today_mask) & (~yesterday_mask) & (~this_week_mask)
        older_mask = df_sessions['last_active'].dt.date <= (today - timedelta(days=30))

        # Dictionary of masks and their corresponding headers
        groups = [
            ("Today", today_mask),
            ("Yesterday", yesterday_mask),
            ("This Week", this_week_mask),
            ("This Month", this_month_mask),
            ("Older", older_mask)
        ]

        # Display sessions by group
        for group_name, mask in groups:
            group_sessions = df_sessions[mask]
            
            if not group_sessions.empty:
                st.subheader(group_name)
                
                # Display sessions within each group
                for _, session in group_sessions.iterrows():
                    # Container for each session row
                    with st.container():
                        col1, col2 = st.columns([0.9, 0.1])

                        with col1:
                            # Main session button
                            if st.button(
                                f"📝 {session['title']}\n🕒 {session['last_active'].strftime('%H:%M')}\n💬 {session['message_count']} messages",
                                key=f"session_{session['session_id']}",
                                use_container_width=True,
                            ):
                                st.session_state.current_session_id = session[
                                    "session_id"
                                ]
                                messages = (
                                    st.session_state.storage.get_session_messages(
                                        session["session_id"]
                                    )
                                )
                                st.session_state.messages = [
                                    (
                                        HumanMessage(
                                            content=msg["content"],
                                            additional_kwargs={"role": "user"},
                                        )
                                        if msg["role"] == "user"
                                        else AIMessage(
                                            content=msg["content"],
                                            additional_kwargs={"role": "assistant"},
                                        )
                                    )
                                    for msg in messages
                                ]
                                st.rerun()

                        with col2:
                            # Menu trigger button
                            if st.button(
                                "⋮",
                                key=f"menu_trigger_{session['session_id']}",
                                help="Session options",
                            ):
                                st.session_state.open_menu_id = session["session_id"]
                                st.rerun()

                        # Show menu modal if this session's menu is open
                        if st.session_state.open_menu_id == session["session_id"]:
                            with st.sidebar:
                                # Create a modal-like container
                                menu_container = st.empty()
                                with menu_container.container():
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
                                            st.session_state.open_menu_id = None
                                            st.rerun()

                                    with col2:
                                        if st.button(
                                            "Cancel",
                                            key=f"cancel_{session['session_id']}",
                                        ):
                                            st.session_state.open_menu_id = None
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
                                            st.session_state.storage.delete_session(
                                                session["session_id"]
                                            )
                                            if (
                                                st.session_state.current_session_id
                                                == session["session_id"]
                                            ):
                                                st.session_state.current_session_id = (
                                                    None
                                                )
                                                st.session_state.messages = []
                                            st.session_state.open_menu_id = None
                                            st.rerun()
                                        else:
                                            st.session_state[
                                                f"confirm_delete_{session['session_id']}"
                                            ] = True
                                            st.warning(
                                                "Click again to confirm deletion"
                                            )

                                    with st.expander("🔍 Debug Information"):
                                        st.markdown("### Session Details")
                                        
                                        # Display all session information in a formatted way
                                        st.markdown("#### Basic Info")
                                        st.code(f"""Session ID: {session['session_id']}
                                    Title: {session['title']}
                                    Created: {session['created_at']}
                                    Last Active: {session['last_active']}
                                    Message Count: {session['message_count']}""")
                                        
                                        # Display metadata if it exists
                                        if 'metadata' in session and session['metadata']:
                                            st.markdown("#### Metadata")
                                            st.json(session['metadata'])
                                        
                                        # Display all raw session data
                                        st.markdown("#### Raw Session Data")
                                        st.json(session.to_dict())
                                        
                                        # Add message preview
                                        st.markdown("#### Recent Messages")
                                        messages = st.session_state.storage.get_session_messages(session['session_id'])
                                        if messages:
                                            for msg in messages[-3:]:  # Show last 3 messages
                                                st.code(f"""Role: {msg['role']}
                                    Timestamp: {msg['timestamp']}
                                    Content: {msg['content'][:100]}{'...' if len(msg['content']) > 100 else ''}""")

# Main chat interface
st.header("RockTalk: Powered by AWS Bedrock 🪨 + LangChain 🦜️🔗 + Streamlit 👑")

# Initialize messages list if not exists
if "messages" not in st.session_state:
    st.session_state.messages = []
    print("--- Chat history initialized ---")

# Initialize current session ID if not exists
if "current_session_id" not in st.session_state:
    st.session_state.current_session_id = None

# Display existing messages
for message in st.session_state.messages:
    with st.chat_message(message.additional_kwargs["role"]):
        st.markdown(message.content)

# Chat input
if prompt := st.chat_input("Hello!"):
    print(f"\nHuman: {prompt}")
    print("AI: ")

    # Create new session if none exists
    if not st.session_state.current_session_id:
        # Use first sentence as title, fallback to timestamp
        title = prompt.split(".")[0][:50] if "." in prompt else f"Chat {datetime.now()}"
        st.session_state.current_session_id = st.session_state.storage.create_session(
            title=title,
            subject=title,
            metadata={"model": "anthropic.claude-3-sonnet-20240229-v1:0"},
        )
        # Don't rerun here - let the conversation flow continue

    # Display and save user message
    with st.chat_message("user"):
        st.markdown(prompt)

    human_input = HumanMessage(content=prompt, additional_kwargs={"role": "user"})
    st.session_state.messages.append(human_input)

    # Save user message to storage
    st.session_state.storage.save_message(
        session_id=st.session_state.current_session_id, role="user", content=prompt
    )

    # Generate and display AI response
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""

        for chunk in st.session_state.llm.stream(st.session_state.messages):
            chunk = cast(AIMessageChunk, chunk)
            for item in chunk.content:
                if isinstance(item, dict) and "text" in item:
                    text = item["text"]
                    full_response += text
                    print(text, end="", flush=True)
                elif "index" in item and item["index"] == 0:
                    print("\nEOF?\n")
                else:
                    print(f"Unexpected chunk type: {item}")

                message_placeholder.markdown(full_response + "▌")

            if chunk.response_metadata:
                print(chunk.response_metadata)
            if chunk.usage_metadata:
                print(type(chunk))
                print(chunk.usage_metadata)

        # Save AI response
        ai_response = AIMessage(
            content=full_response, additional_kwargs={"role": "assistant"}
        )
        st.session_state.messages.append(ai_response)

        # Save to storage
        st.session_state.storage.save_message(
            session_id=st.session_state.current_session_id,
            role="assistant",
            content=full_response,
        )

        message_placeholder.markdown(full_response)

        # Update last_update timestamp
        st.session_state.last_update = datetime.now()

        # Now rerun after the complete conversation turn is saved
        st.rerun()
