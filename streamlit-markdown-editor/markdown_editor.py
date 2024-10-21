import streamlit as st
import streamlit.components.v1 as components
import os
import re
import requests
import base64
from io import BytesIO
from urllib.parse import urlparse
from datetime import datetime

# Get the directory of the current script
current_dir = os.path.dirname(os.path.abspath(__file__))

# Path to the frontend files
frontend_dir = os.path.join(current_dir, "frontend")

def markdown_editor_input():
    _component_func = components.declare_component(
        "markdown_editor", path=frontend_dir
    )
    return _component_func(key="markdown_editor", default=None, height=400)

def download_image(url):
    try:
        response = requests.get(url)
        if response.status_code == 200:
            content_type = response.headers.get('content-type', 'image/jpeg')
            img_data = base64.b64encode(response.content).decode('utf-8')
            return f"data:{content_type};base64,{img_data}"
    except Exception as e:
        st.error(f"Error downloading image: {e}")
    return None

def process_markdown(markdown_content):
    if markdown_content is None:
        return ""
    
    # Regular expression to find image markdown
    img_pattern = r'!\[([^\]]*)\]\(([^)]+)\)'
    
    def replace_image(match):
        alt_text, url = match.groups()
        base64_image = download_image(url)
        if base64_image:
            return f'![{alt_text}]({base64_image})'
        return match.group(0)  # Return original if download failed
    
    # Replace all image URLs with base64 data
    processed_markdown = re.sub(img_pattern, replace_image, markdown_content)
    return processed_markdown

st.set_page_config(page_title="Markdown Editor")
st.title("Markdown Editor")

markdown_content = markdown_editor_input()

if st.button("Submit"):
    if markdown_content:
        processed_content = process_markdown(markdown_content)
        st.session_state.submitted_content = processed_content
        st.success("Content submitted successfully!")
        st.write(f"Content length: {len(processed_content)} characters")

        st.subheader("Processed Markdown Content:")
        st.code(processed_content, language="markdown")

        st.subheader("Rendered Markdown:")
        st.markdown(processed_content)
        if processed_content:
            print(process_markdown)
    else:
        st.warning("No content to submit.")

# Debug information
st.subheader("Debug Information:")
st.write(f"markdown_content type: {type(markdown_content)}")
st.write("markdown_content value:")
st.code(markdown_content)
