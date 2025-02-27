import streamlit as st
from streamlit_lexical import streamlit_lexical


def on_change_editor():
    st.session_state["editor_content"] = st.session_state["editor"]
    st.session_state[
        "editor_content"
    ] = """Hello, how are you?

## markdown

- item 1
- item 2
- item 3"""

    # Add this line to prevent full re-run
    st.session_state["update_editor"] = False


st.write("#")
st.header("Lexical Rich Text Editor")

# Initialize the session state for editor content
if "editor_content" not in st.session_state:
    st.session_state[
        "editor_content"
    ] = """Hello, how are you?

## markdown

- item 1
- item 2
- item 3"""

    st.session_state["update_editor"] = True

# Create an instance of our component
streamlit_lexical(
    value=(
        st.session_state["editor_content"]
        if st.session_state.get("update_editor", True)
        else None
    ),
    placeholder="Enter some rich text",
    key="editor",
    height=800,
    overwrite=False,
    on_change=on_change_editor,
)

st.markdown(st.session_state["editor_content"])
st.markdown("---")

# Display the current content in session state (for debugging)
st.write("Current content in session state:", st.session_state["editor_content"])
