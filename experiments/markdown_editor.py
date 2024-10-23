import os

import streamlit as st

from streamlit_markdown_editor import markdown_editor

# Get the directory of the current script
current_dir = os.path.dirname(os.path.abspath(__file__))

# Path to the frontend files
frontend_dir = os.path.join(current_dir, "frontend")

st.set_page_config(page_title="Markdown Editor")
st.title("Markdown Editor")

result = markdown_editor()
if result.content:
    st.markdown(result.content)
    st.code(result.content, language="markdown")
    print(result.content)

