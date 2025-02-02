from typing import Callable, Dict, List, TypeAlias, TypedDict, Unpack

import streamlit as st
import streamlit.components.v1 as components


# Note that st.segmented_control also takes the same inputs so these methods for st.pill
# so these can be used interchangeably with both
# TODO add docs/examples for using these classes/methods
class PillOptionMap(TypedDict):
    label: str
    callback: Callable[[], None]


PillOptions: TypeAlias = List[PillOptionMap] | Dict[int, PillOptionMap]


class OnPillsChange(TypedDict):
    key: str
    options_map: PillOptions


def on_pills_change(**kwargs: Unpack[OnPillsChange]):
    """Handle pill/segmented control selection changes by executing the callback for the selected option.

    Args:
        **kwargs: Dictionary containing:
            key (str): The key of the pill/segmented control component
            options_map (PillOptions): Mapping of options to their callbacks

    Examples:
        Basic usage with st.pill:
        ```python
        def new_chat():
            st.session_state.messages = []
            st.rerun()

        def open_settings():
            st.session_state.show_settings = True

        # Define options with labels and callbacks
        options_map: PillOptions = [
            {
                "label": "New Chat",
                "callback": new_chat
            },
            {
                "label": "Settings",
                "callback": open_settings
            }
        ]

        # Create pill group with callbacks
        st.pill(
            "Actions",
            options=range(len(options_map)),
            format_func=lambda x: options_map[x]["label"],
            key="action_pills",
            on_change=on_pills_change,
            kwargs=dict(
                OnPillsChange(
                    key="action_pills",
                    options_map=options_map
                )
            )
        )
        ```

        Using with message actions:
        ```python
        def copy_text(text: str):
            st.toast(f"Copied: {text}")

        def edit_message(msg: ChatMessage):
            st.session_state.editing_message = msg

        # Create options with partial functions to pass arguments
        options_map: PillOptions = [
            {
                "label": ":material/edit: Edit",
                "callback": partial(edit_message, message)
            },
            {
                "label": ":material/content_copy: Copy",
                "callback": partial(copy_text, message.content)
            }
        ]

        # Use with segmented control
        st.segmented_control(
            "Message Actions",
            options=range(len(options_map)),
            format_func=lambda x: options_map[x]["label"],
            key=f"msg_actions_{message.id}",
            on_change=on_pills_change,
            kwargs=dict(
                OnPillsChange(
                    key=f"msg_actions_{message.id}",
                    options_map=options_map
                )
            ),
            label_visibility="collapsed"
        )
        ```
    """
    key = kwargs["key"]
    options_map = kwargs["options_map"]
    val: int = st.session_state[key]
    if key in st.session_state:
        st.session_state[key] = None
        options_map[val]["callback"]()


def escape_dollarsign(raw_string: str) -> str:
    """Escape dollar signs in a string to prevent LaTeX rendering in markdown.

    Args:
        raw_string (str): The input string.

    Returns:
        str: The string with dollar signs escaped.
    """
    return raw_string.replace("$", r"\$")


def close_dialog() -> None:
    components.html(
        """\
            <script>
            parent.document.querySelector('div[data-baseweb="modal"]').remove();
            </script>
            """,
        height=0,
        scrolling=False,
    )
