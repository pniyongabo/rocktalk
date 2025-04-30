import json

import streamlit as st
import streamlit.components.v1 as stcomponents
from streamlit_javascript import st_javascript
from streamlit_js_eval import streamlit_js_eval

from .log import logger


def load_js_init():
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


def find_iframe_js():
    return """
    function findIFrameFunction(funcName) {
        console.log('findIFrameFunction: ', funcName);
        const iframes = window.parent.document.getElementsByClassName("stIFrame");
        for (let iframe of iframes) {
            try {
                console.log('iframe: ', iframe);
                if (iframe.contentWindow && iframe.contentWindow[funcName]) {
                    return iframe.contentWindow[funcName];
                }
            } catch (err) {
                console.error('Error accessing iframe:', err);
            }
        }
        return null;
    }
    """


def expand_button_height(target_key: str):
    return
    target_key = json.dumps(f".st-key-{target_key} button")
    streamlit_js_eval(
        js_expressions=f"""
    {find_iframe_js()}

    findIFrameFunction('expandButton')({target_key});
    """
    )


def copy_value_to_clipboard(value: str):
    value = json.dumps(value)
    # with stylized_container("copy_to_clipboard_boo"):
    streamlit_js_eval(
        js_expressions=f"""
    {find_iframe_js()}

    findIFrameFunction('initAndCopy')({value});
    """
    )
    st.toast(body="Copied to clipboard", icon="📋")
    # See note in chat.py
    st.session_state.message_copied = 3


def scroll_to_bottom() -> None:
    """Scrolls to the bottom of the chat interface.

    This method inserts a div element at the bottom of the chat and uses JavaScript
    to scroll to it, ensuring the most recent messages are visible.
    """
    if st.session_state.skip_next_scroll:
        logger.debug("Skipping scroll due to skip_next_scroll flag")
        st.session_state.skip_next_scroll = False  # Reset for future scrolls
        return

    index = st.session_state.scroll_div_index
    st.markdown(f"""<div id="end-of-chat-{index}"></div>""", unsafe_allow_html=True)

    js = (
        """
    <script>
        function scrollToBottom() {
            // Break out of iframe and get the main window
            const mainWindow = window.parent;
            const endMarker = mainWindow.document.getElementById('"""
        + f"""end-of-chat-{index}"""
        + """');

            if (endMarker) {
                endMarker.scrollIntoView({
                    behavior: 'smooth',
                    block: 'end'
                });
            } else {
                // Fallback to scrolling the whole window
                mainWindow.scrollTo({
                    top: mainWindow.document.documentElement.scrollHeight,
                    behavior: 'smooth'
                });
            }
        }

        // Call immediately and after a short delay to ensure content is loaded
        scrollToBottom();
        setTimeout(scrollToBottom, 100);
    </script>
    """
    )

    stcomponents.html(js, height=0)


def scroll_to_bottom_streaming(selector: str = ".stMarkdown") -> None:
    """Automatically scrolls the chat window during streaming responses.

    This method adds a JavaScript script that handles auto-scrolling behavior during
    message streaming. The scrolling continues until the user manually scrolls,
    at which point auto-scrolling is disabled to respect user control.

    The script implements the following features:
        - Detects user scroll events (both wheel and touch)
        - Automatically scrolls to the latest message every 100ms
        - Stops auto-scrolling if user manually scrolls
        - Automatically cleans up after 30 seconds

    The scrolling behavior is implemented using smooth scrolling for better user
    experience and targets the last markdown element in the chat window.
    """
    # Add scroll script with user interaction detection
    js = (
        """
    <script>
        let userHasScrolled = false;
        let scrollInterval;

        // Detect user scroll
        window.parent.addEventListener('wheel', function() {
            userHasScrolled = true;
            if (scrollInterval) {
                clearInterval(scrollInterval);
            }
            // Set a flag in localStorage that we can check later
            window.localStorage.setItem('userScrolledDuringStream', 'true');
        }, { passive: true });

        window.parent.addEventListener('touchmove', function() {
            userHasScrolled = true;
            if (scrollInterval) {
                clearInterval(scrollInterval);
            }
            // Set a flag in localStorage that we can check later
            window.localStorage.setItem('userScrolledDuringStream', 'true');
        }, { passive: true });

        function keepInView() {
            if (!userHasScrolled) {
                const items = window.parent.document.querySelectorAll('"""
        + f"{selector}"
        + """');
                if (items.length > 0) {
                    const lastItem = items[items.length - 1];
                    lastItem.scrollIntoView({
                        behavior: 'smooth',
                        block: 'end'
                    });
                    window.parent.document.documentElement.scrollTop += 100;  // 100px padding
                }
            }
        }

        // Start auto-scroll only if user hasn't manually scrolled
        scrollInterval = setInterval(keepInView, 100);

        // Clear interval after 30 seconds as a safety measure
        setTimeout(() => {
            if (scrollInterval) {
                clearInterval(scrollInterval);
            }
        }, 30000);
    </script>
    """
    )
    stcomponents.html(js, height=0)

    # Add JavaScript to check the localStorage flag and communicate back to Streamlit

    check_scroll_js = """
<script>
    function notifyStreamlit() {
        try {
            if (window.localStorage.getItem('userScrolledDuringStream') === 'true') {
                window.localStorage.removeItem('userScrolledDuringStream');
                if (window.parent && window.parent.streamlitReady) {
                    // Use Streamlit's built-in setComponentValue
                    window.parent.Streamlit.setComponentValue(true);
                }
            }
        } catch (e) {
            console.error('Error in notifyStreamlit:', e);
        }
    }

    // Try multiple times to ensure we catch the flag
    setTimeout(notifyStreamlit, 100);
    setTimeout(notifyStreamlit, 500);
    setTimeout(notifyStreamlit, 1000);
</script>
"""

    val = stcomponents.html(check_scroll_js, height=0)
    if val:
        st.session_state.skip_next_scroll = True
        logger.debug("User scrolled during stream, will skip next auto-scrolls")


def focus_prompt(container_key: str) -> None:
    """Focuses the prompt input box.

    This method adds JavaScript that focuses an iframe containing the prompt input
    based on a provided container key. This ensures cursor focus returns to the prompt
    when needed.

    Args:
        container_key: The Streamlit key for the container with the prompt input
    """

    js = (
        """<script>
                function focusPromptTextarea() {
                    const allIframes = window.parent.document.querySelectorAll('iframe');
                    // Find the container with the st-key-... class
                    const container = window.parent.document.querySelector('[class*="st-key-"""
        + container_key
        + """"]');
                    if (container) {
                        // Find the iframe within this container
                        const promptIframe = container.querySelector('iframe') ||
                                            container.querySelector('.stCustomComponentV1');
                        if (promptIframe) {
                            // First focus the iframe itself
                            promptIframe.focus();

                            // Then try to focus the textarea inside the iframe
                            const iframeWindow = promptIframe.contentWindow;
                            if (iframeWindow) {
                                iframeWindow.postMessage({
                                    type: 'focus_textarea'
                                }, '*');
                                console.log("focus_textarea posted");
                            }
                        } else {
                            console.log('Could not find iframe in container:', container.innerHTML);
                        }
                    }
                }
                setTimeout(focusPromptTextarea, 100);
                setTimeout(focusPromptTextarea, 1000);
            </script>
            """
    )

    stcomponents.html(js, height=0)


def adjust_chat_message_style():
    """Adds CSS styling adjustments to format chat message containers.

    This method injects custom CSS styles to modify:
    - Background color of user message containers
    - Message container padding
    - Message button alignment
    """
    st.markdown(
        f"""
            <style>
                /* propogate the background color to entire user message container */
                [class*='st-key-user_message_container_']
                {{
                    background-color: {st.session_state.theme['secondaryBackgroundColor']};
                    /* border-radius: 0.5rem; */
                }}

                /* add padding to message containers to make some space for buttons */
                [class*='st-key'][class*='_message_container_']
                {{
                    padding: 1rem;
                }}

                /*  right align message buttons */
                [class*='st-key-message_buttons_']
                {{
                    display: flex !important;
                    justify-content: flex-end !important; /* Right align */
                }}
            </style>
            """,
        unsafe_allow_html=True,
    )


def refresh_window():
    """Refreshes the parent window from within an iframe.

    This function injects JavaScript code that refreshes the entire Streamlit app
    by reloading the parent window.
    """
    js = """
    <script>
        function refreshParentWindow() {
            try {
                // Access the parent window and reload it
                window.parent.location.reload();
                console.log("Parent window refresh triggered");
            } catch (error) {
                console.error("Error refreshing parent window:", error);
            }
        }
        
        // Execute the refresh
        refreshParentWindow();
    </script>
    """

    stcomponents.html(js, height=0)
