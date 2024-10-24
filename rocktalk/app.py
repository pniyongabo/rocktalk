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
from utils.date_utils import create_date_masks
from components.sidebar import Sidebar
from components.chat import ChatInterface

# Load environment variables
dotenv.load_dotenv()

# Set page configuration
st.set_page_config(page_title="RockTalk", page_icon="🪨", layout="wide")
st.subheader("RockTalk: Powered by AWS Bedrock 🪨 + LangChain 🦜️🔗 + Streamlit 👑")

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

# Initialize messages list if not exists
if "messages" not in st.session_state:
    st.session_state.messages = []
    print("--- Chat history initialized ---")

# Initialize session state variables
if "last_update" not in st.session_state:
    st.session_state.last_update = datetime.now()

# Initialize current session ID if not exists
if "current_session_id" not in st.session_state:
    st.session_state.current_session_id = None

sidebar = Sidebar(storage=st.session_state.storage)
sidebar.render()

chat = ChatInterface(storage=st.session_state.storage, llm=st.session_state.llm)
chat.render()
