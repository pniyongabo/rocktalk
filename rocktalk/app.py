import streamlit as st
from components.chat import ChatInterface
from components.sidebar import Sidebar
from config.settings import DEPLOYED, app_config, check_password
from models.llm import BedrockLLM, LLMInterface
from storage.sqlite_storage import SQLiteChatStorage

if "stop_chat_stream" not in st.session_state:
    st.session_state.stop_chat_stream = False
if "user_input_default" not in st.session_state:
    st.session_state.user_input_default = None


st.subheader(
    f"{app_config.page_title}: Powered by AWS Bedrock 🪨 + LangChain 🦜️🔗 + Streamlit 👑"
)
# Password check
if DEPLOYED and not check_password():
    st.stop()


# Initialize storage in session state
if "storage" not in st.session_state:
    st.session_state.storage = SQLiteChatStorage(
        db_path="chat_database.db"
    )  # StorageInterface


# Initialize LLM object in session state
if "llm" not in st.session_state:
    llm: LLMInterface = BedrockLLM()
    st.session_state.llm = llm

chat = ChatInterface()
chat.render()

sidebar = Sidebar(chat_interface=chat)
sidebar.render()
