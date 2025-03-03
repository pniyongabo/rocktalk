# rocktalk/app_context.py
from pathlib import Path

import dotenv
import streamlit as st
import streamlit_authenticator as stauth
import yaml
from models.llm import BedrockLLM, LLMInterface
from models.storage.sqlite import SQLiteChatStorage
from models.storage.storage_interface import StorageInterface
from utils.js import get_user_timezone
from utils.log import ROCKTALK_DIR, logger
from yaml.loader import SafeLoader


class AppContext:
    """
    Central application context that manages services and dependencies.

    This class initializes and provides access to core services like storage,
    LLM interface, and authentication. It serves as a service locator pattern
    implementation for the application.
    """

    def __init__(self):
        """Initialize the application context and all required services."""
        # Load environment variables
        dotenv.load_dotenv()

        # Initialize core services
        self._storage = self._init_storage()
        st.session_state.storage = self._storage
        self._llm = self._init_llm()
        st.session_state.llm = self._llm
        self._auth = self._init_auth()
        st.session_state.auth = self._auth

        # Initialize state
        self._init_state()

    def _init_storage(self) -> StorageInterface:
        """Initialize the storage service."""
        storage_instance = SQLiteChatStorage(db_path="chat_database.db")
        logger.debug("Storage service initialized")
        return storage_instance

    def _init_llm(self) -> LLMInterface:
        """Initialize the LLM service with storage dependency."""
        llm_instance = BedrockLLM(storage=self._storage)
        logger.debug("LLM service initialized")
        return llm_instance

    def _init_auth(self) -> stauth.Authenticate | None:
        """Initialize authentication if auth.yaml exists."""
        auth_file = Path(ROCKTALK_DIR) / "auth.yaml"

        if auth_file.exists():
            try:
                with open(auth_file) as f:
                    config = yaml.load(f, Loader=SafeLoader)
                    auth = stauth.Authenticate(
                        str(auth_file),
                        config["cookie"]["name"],
                        config["cookie"]["key"],
                        config["cookie"]["expiry_days"],
                    )
                logger.debug("Authentication service initialized")
                return auth
            except Exception as e:
                logger.error(f"Error loading authentication configuration: {e}")

        logger.debug("No authentication configuration found")
        return None

    def _init_state(self):
        """Initialize application state variables."""
        # These are session state values that need to be set during initialization

        if "stop_chat_stream" not in st.session_state:
            st.session_state.stop_chat_stream = False

        if "user_input_default" not in st.session_state:
            st.session_state.user_input_default = None

        if "message_copied" not in st.session_state:
            st.session_state.message_copied = 0

        if "stored_user_input" not in st.session_state:
            st.session_state.stored_user_input = None

        if "temporary_session" not in st.session_state:
            st.session_state.temporary_session = False

    @property
    def storage(self) -> StorageInterface:
        """Get the storage service."""
        return self._storage

    @property
    def llm(self) -> LLMInterface:
        """Get the LLM service."""
        return self._llm

    @property
    def auth(self) -> stauth.Authenticate | None:
        """Get the authentication service if available."""
        return self._auth

    @property
    def using_auth(self) -> bool:
        """Check if authentication is enabled."""
        return self._auth is not None

    def handle_authentication(self) -> bool:
        """
        Handle authentication flow.

        Returns:
            bool: True if authenticated or auth not required, False otherwise
        """
        if not self.using_auth:
            return True

        try:
            if not st.session_state.get("authentication_status"):
                assert self._auth, "Authentication service not available"
                self._auth.login("main")
                if st.session_state.get("authentication_status") is False:
                    st.error("Username/password is incorrect")
                elif st.session_state.get("authentication_status") is None:
                    st.warning("Please enter your username and password")
                return False
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            st.error(f"Authentication system error. Proceeding without authentication.")
            # Allow access despite auth error
            return True

        return True
