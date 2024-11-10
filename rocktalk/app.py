from datetime import datetime
from typing import cast

import dotenv
import streamlit as st
from langchain.schema import AIMessage, HumanMessage
from langchain_aws import ChatBedrockConverse

from components.chat import ChatInterface
from components.sidebar import Sidebar
from models.interfaces import StorageInterface
from storage.sqlite_storage import SQLiteChatStorage

# Load environment variables
dotenv.load_dotenv()

# Set page configuration
st.set_page_config(page_title="RockTalk", page_icon="🪨", layout="wide")
st.subheader("RockTalk: Powered by AWS Bedrock 🪨 + LangChain 🦜️🔗 + Streamlit 👑")

# Initialize storage in session state
if "storage" not in st.session_state:
    st.session_state.storage: StorageInterface = SQLiteChatStorage(
        db_path="chat_database.db"
    )
    print("--- Storage initialized ---")

if "additional_text" not in st.session_state:
    st.session_state.additional_text = None

# Initialize LLM object in session state
if "llm" not in st.session_state:
    st.session_state.llm = ChatBedrockConverse(
        region_name="us-west-2",
        model="anthropic.claude-3-sonnet-20240229-v1:0",
        temperature=0,
        max_tokens=None,
    )
    print("--- LLM initialized ---")

sidebar = Sidebar(storage=st.session_state.storage)
sidebar.render()

chat = ChatInterface(storage=st.session_state.storage, llm=st.session_state.llm)
chat.render()
