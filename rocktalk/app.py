import os
from pathlib import Path

import dotenv
import streamlit as st
import streamlit.components.v1 as stcomponents
import streamlit_authenticator as stauth
import yaml
from components.chat import ChatInterface
from components.sidebar import Sidebar
from models.llm import BedrockLLM
from storage.sqlite_storage import SQLiteChatStorage
from streamlit_float import float_init
from streamlit_theme import st_theme
from utils.js import get_user_timezone
from yaml.loader import SafeLoader

st.set_page_config(
    page_title="RockTalk",
    page_icon="🪨",
    layout="wide",
)


def initialize_auth():
    """Initialize authentication if auth.yaml exists"""
    rocktalk_dir = os.getenv("ROCKTALK_DIR", str(Path.home() / ".rocktalk"))
    auth_file = Path(rocktalk_dir) / "auth.yaml"

    if auth_file.exists():
        try:
            with open(auth_file) as f:
                config = yaml.load(f, Loader=SafeLoader)
            return stauth.Authenticate(
                str(auth_file),
                config["cookie"]["name"],
                config["cookie"]["key"],
                config["cookie"]["expiry_days"],
            )
        except Exception as e:
            st.error(f"Error loading authentication configuration: {e}")
    return None


def initialize_app():
    """Initialize app configuration and state"""
    # Load environment variables
    dotenv.load_dotenv()

    # Initialize storage
    if "storage" not in st.session_state:
        st.session_state.storage = SQLiteChatStorage(db_path="chat_database.db")

    # Initialize LLM
    if "llm" not in st.session_state:
        st.session_state.llm = BedrockLLM(storage=st.session_state.storage)

    # Initialize theme and other state variables
    st.session_state.theme = st_theme()
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
    if "user_timezone" not in st.session_state or not st.session_state.user_timezone:
        st.session_state.user_timezone = get_user_timezone()


def render_header():
    """Render app header when no session is active"""
    if not st.session_state.get("current_session_id") and not st.session_state.get(
        "temporary_session"
    ):
        st.subheader(
            "Rocktalk: Powered by AWS Bedrock 🪨 + LangChain 🦜️🔗 + Streamlit 👑"
        )


def render_app():
    chat = ChatInterface()
    chat.render()

    sidebar = Sidebar(chat_interface=chat)
    sidebar.render()


def main():
    """Main application entry point"""
    initialize_app()

    # Initialize authentication if configured
    authenticator: stauth.Authenticate | None = initialize_auth()
    using_auth: bool = authenticator is not None

    if using_auth:
        st.session_state.authenticator = authenticator

        if not st.session_state.get("authentication_status"):
            # Handle authentication
            try:
                authenticator.login("main")
                if st.session_state.get("authentication_status") is False:
                    st.error("Username/password is incorrect")
                elif st.session_state.get("authentication_status") is None:
                    st.warning("Please enter your username and password")
            except Exception as e:
                st.error(f"Authentication error: {e}")
            return

    # Only proceed if either:
    # 1. No authentication is configured
    # 2. Authentication is configured and user is authenticated
    # if not authenticator or st.session_state.get("authentication_status"):
    # Run the app
    render_header()
    if "next_run_callable" in st.session_state:
        st.session_state.next_run_callable()
        del st.session_state["next_run_callable"]
    render_app()


# Float feature initialization
float_init()

st.markdown(
    """
    <style>
        .element-container:has(
            iframe[title="streamlit_js_eval.streamlit_js_eval"]
        ) {
            //height: 0 !important;
            display: none;
        }
        div[data-testid="InputInstructions"] > span:nth-child(1) {
            visibility: hidden;
        }
    </style>
    """,
    unsafe_allow_html=True,
)
stcomponents.html(
    """
<script>

function updateButtonHeight(targetKey) {
    const parentDoc = window.parent.document;

    const targetButton = parentDoc.querySelector(targetKey);
    if (!targetButton) {
        console.error('Target button not found');
        return;
    }

    // Check if window width is >= 640px
    const isColumnMode = window.parent.innerWidth >= 640;
    //console.log('Window width:', window.parent.innerWidth, 'Column mode:', isColumnMode);

    if (isColumnMode) {
        // Find the shared horizontal block container
        let horizontalBlock = targetButton.closest('.stHorizontalBlock');
        if (!horizontalBlock) {
            console.error('Horizontal block not found');
            return;
        }

        // Find the chat message within this horizontal block
        let chatMessage = horizontalBlock.querySelector('.stChatMessage');

        // If not found, try one level up
        if (!chatMessage && horizontalBlock.parentElement) {
            horizontalBlock = horizontalBlock.parentElement.closest('.stHorizontalBlock');
            if (horizontalBlock) {
                chatMessage = horizontalBlock.querySelector('.stChatMessage');
            }
        }

        if (!chatMessage) {
            console.error('Related chat message not found in current or parent horizontal block');
            return;
        }

        const computedStyle = window.getComputedStyle(chatMessage);
        const height = computedStyle.height;
        //console.log('Related chat message height:', height);

        // Set gap to 0 for the immediate verticalBlock
        const immediateBlock = targetButton.closest('.stVerticalBlock');
        if (immediateBlock) {
            immediateBlock.style.gap = '0';
        }

        // Make button fill height
        targetButton.style.height = height;
        targetButton.style.boxSizing = 'border-box';
        //console.log('Applied height:', height);
    } else {
        // Reset button height in wrapped mode
        targetButton.style.height = '';
        //console.log('Reset button height (wrapped mode)');

        // Optionally reset gap
        const immediateBlock = targetButton.closest('.stVerticalBlock');
        if (immediateBlock) {
            immediateBlock.style.gap = '';
        }
    }
}

function expandButton(targetKey) {
    try {
        console.log(`expandButton target key '${targetKey}'`);

        // Initial update
        setTimeout(() => updateButtonHeight(targetKey), 1);

        // Add resize listener
        const resizeObserver = new ResizeObserver(entries => {
            updateButtonHeight(targetKey);
        });
        resizeObserver.observe(parentDoc.body);

    } catch (error) {
        console.error('Error occurred:', error.message);
    }
}

function copyFunction(textToCopy) {
    try {
        const parentDoc = window.parent.document;

        console.log("textToCopy:", textToCopy);

        // Try using the parent window's clipboard API first
        if (window.parent.navigator.clipboard) {
            window.parent.navigator.clipboard.writeText(textToCopy)
                .then(() => {
                    console.log('Text copied successfully');
                })
                .catch((err) => {
                    console.error('Clipboard API failed:', err);
                    fallbackCopy(textToCopy, parentDoc);
                });
        } else {
            fallbackCopy(textToCopy, parentDoc);
        }
    } catch (err) {
        console.error('Copy failed:', err);
    }
}

function fallbackCopy(text, parentDoc) {
    try {
        const textarea = parentDoc.createElement('textarea');
        textarea.value = text;
        textarea.style.position = 'fixed';
        textarea.style.opacity = '0';

        parentDoc.body.appendChild(textarea);
        textarea.focus();
        textarea.select();

        try {
            parentDoc.execCommand('copy');
            console.log('Text copied using fallback method');
        } catch (execErr) {
            console.error('execCommand failed:', execErr);
        }

        parentDoc.body.removeChild(textarea);
    } catch (err) {
        console.error('Fallback copy failed:', err);

        // Last resort fallback
        try {
            const tempInput = parentDoc.createElement('input');
            tempInput.value = text;
            tempInput.style.position = 'fixed';
            tempInput.style.opacity = '0';

            parentDoc.body.appendChild(tempInput);
            tempInput.select();
            tempInput.setSelectionRange(0, 99999);

            parentDoc.execCommand('copy');
            parentDoc.body.removeChild(tempInput);
            console.log('Text copied using last resort method');
        } catch (finalErr) {
            console.error('All copy methods failed:', finalErr);
        }
    }
}

// For the clipboard API not working on subsequent loads,
// try to reinitialize it each time
function initAndCopy(textToCopy) {
    if (window.parent.navigator.clipboard) {
        // Force clipboard permission check
        window.parent.navigator.permissions.query({name: 'clipboard-write'})
            .then(result => {
                console.log('Clipboard permission:', result.state);
                copyFunction(textToCopy);
            })
            .catch(() => {
                copyFunction(textToCopy);
            });
    } else {
        copyFunction(textToCopy);
    }
}
console.log("js functions loaded");
</script>
""",
    width=0,
    height=0,
)

if __name__ == "__main__":
    main()
