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

# Load environment variables
dotenv.load_dotenv()

# Set page configuration
st.set_page_config(page_title="RockTalk", page_icon="🪨", layout="wide")

# Initialize storage in session state
if "storage" not in st.session_state:
    st.session_state.storage = SQLiteChatStorage(db_path="chat_database.db")
    print("--- Storage initialized ---")

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
    recent_sessions = st.session_state.storage.get_recent_sessions(limit=30)
    
    # Display sessions in sidebar
    for session in recent_sessions:
        # Format the session title/subject
        title = session.get("title", "Untitled")
        timestamp = datetime.fromisoformat(session["last_active"])
        message_count = session.get("message_count", 0)
        
        # Create a clickable session title with better formatting
        if st.button(
            f"📝 {title}\n🕒 {timestamp.strftime('%Y-%m-%d %H:%M')}\n💬 {message_count} messages",
            key=f"session_{session['session_id']}",
            use_container_width=True,
        ):
            # Load selected session
            st.session_state.current_session_id = session["session_id"]
            messages = st.session_state.storage.get_session_messages(session["session_id"])
            
            # Convert stored messages to LangChain message format
            st.session_state.messages = [
                HumanMessage(content=msg["content"], additional_kwargs={"role": "user"})
                if msg["role"] == "user"
                else AIMessage(content=msg["content"], additional_kwargs={"role": "assistant"})
                for msg in messages
            ]
            st.rerun()

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
        title = prompt.split('.')[0][:50] if '.' in prompt else f"Chat {datetime.now()}"
        st.session_state.current_session_id = st.session_state.storage.create_session(
            title=title,
            subject=title,
            metadata={"model": "anthropic.claude-3-sonnet-20240229-v1:0"}
        )
        # Don't rerun here - let the conversation flow continue

    # Display and save user message
    with st.chat_message("user"):
        st.markdown(prompt)
    
    human_input = HumanMessage(content=prompt, additional_kwargs={"role": "user"})
    st.session_state.messages.append(human_input)
    
    # Save user message to storage
    st.session_state.storage.save_message(
        session_id=st.session_state.current_session_id,
        role="user",
        content=prompt
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
            content=full_response, 
            additional_kwargs={"role": "assistant"}
        )
        st.session_state.messages.append(ai_response)
        
        # Save to storage
        st.session_state.storage.save_message(
            session_id=st.session_state.current_session_id,
            role="assistant",
            content=full_response
        )

        message_placeholder.markdown(full_response)
        
        # Update last_update timestamp
        st.session_state.last_update = datetime.now()
        
        # Now rerun after the complete conversation turn is saved
        st.rerun()
