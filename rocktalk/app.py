import dotenv
import streamlit as st
from components.chat import ChatInterface
from components.sidebar import Sidebar
from storage.sqlite_storage import SQLiteChatStorage
from config.settings import AppConfig
from models.llm import BedrockLLM, LLMInterface

# Load environment variables
dotenv.load_dotenv()

# Set page configuration
app_config: AppConfig
if "app_config" not in st.session_state:
    app_config = AppConfig()
    st.session_state.app_config = app_config
else:
    app_config = st.session_state.app_config

st.set_page_config(
    page_title=app_config.page_title,
    page_icon=app_config.page_icon,
    layout=app_config.layout,
)
st.subheader(
    f"{app_config.page_title}: Powered by AWS Bedrock 🪨 + LangChain 🦜️🔗 + Streamlit 👑"
)

# Initialize storage in session state
if "storage" not in st.session_state:
    st.session_state.storage = SQLiteChatStorage(
        db_path="chat_database.db"
    )  # StorageInterface


# # Initialize LLM object in session state
if "llm" not in st.session_state:
    llm: LLMInterface = BedrockLLM()
    st.session_state.llm = llm

chat = ChatInterface()
chat.render()

sidebar = Sidebar(chat_interface=chat)
sidebar.render()
