import streamlit as st
import streamlit.components.v1 as components
import os
import re

# Get the directory of the current script
current_dir = os.path.dirname(os.path.abspath(__file__))

# Path to the frontend files
frontend_dir = os.path.join(current_dir, "frontend")


def html_to_markdown_input():
    _component_func = components.declare_component(
        "html_to_markdown", path=frontend_dir
    )
    return _component_func(key="html_to_markdown", default=None, height=200)

import requests
import base64
from urllib.parse import urlparse
from datetime import datetime

current_time = datetime.now().strftime("%I:%M %p")
print(f"App running at {current_time}")
def parse_markdown(markdown_content):
    text_content = []
    images = []

    # Regular expression to find image markdown with data URL or regular URL
    img_pattern = r'\[([^\]]+)\]\(((?:data:image/[^;]+;base64,[^)]+)|(?:https?://[^)]+))\)'

    # Split the content by newlines
    lines = markdown_content.split("\n")

    for line in lines:
        img_matches = re.findall(img_pattern, line)
        if img_matches:
            for alt_text, image_url in img_matches:
                print(f"found image: {img_matches}")
                if image_url.startswith('data:'):
                    # It's already a data URL
                    data_url = image_url
                else:
                    # It's a regular URL, try to fetch and convert to data URL
                    try:
                        response = requests.get(image_url)
                        if response.status_code == 200:
                            content_type = response.headers.get('content-type', 'image/jpeg')
                            img_data = base64.b64encode(response.content).decode('utf-8')
                            data_url = f"data:{content_type};base64,{img_data}"
                        else:
                            # If fetch fails, keep the original URL
                            data_url = image_url
                    except requests.RequestException:
                        # If there's an error in fetching, keep the original URL
                        data_url = image_url

                # Replace the image markdown with a placeholder
                line = line.replace(
                    f"[{alt_text}]({image_url})", f"[IMAGE_{len(images)}]"
                )
                images.append((alt_text, data_url))

        if line.strip():  # Only add non-empty lines
            text_content.append(line)

    return "\n".join(text_content), images

st.set_page_config(page_title="HTML to Markdown Converter")
st.title("HTML to Markdown Converter")

markdown_content = html_to_markdown_input()

if st.button("Submit"):
    if markdown_content:
        st.session_state.submitted_content = markdown_content
        st.success("Content submitted successfully!")
        st.write(f"Content length: {len(markdown_content)} characters")

        # Parse the markdown content
        text_content, images = parse_markdown(markdown_content)

        st.subheader("Parsed Content:")
        st.code(text_content, language="markdown")

        st.subheader("Images:")
        for i, (alt_text, data_url) in enumerate(images):
            st.write(f"Image {i+1}: {alt_text}")

        # Prepare content for LLM API
        llm_input = [{"type": "text", "text": text_content}]
        for i, (alt_text, data_url) in enumerate(images):
            # Extract the base64 data and media type from the data URL
            media_type, base64_data = data_url.split(",", 1)
            media_type = media_type.split(":")[1].split(";")[0]

            llm_input.append(
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": media_type,
                        "data": base64_data,
                    },
                }
            )

        st.subheader("LLM API Input:")
        st.json(llm_input)

    else:
        st.warning("No content to submit.")

# Debug information
st.subheader("Debug Information:")
st.write(f"markdown_content type: {type(markdown_content)}")
st.write(f"markdown_content value: {markdown_content}")
