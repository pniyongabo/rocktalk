# __init__.py
from pathlib import Path
from typing import Dict, Optional
import streamlit.components.v1 as components
import requests
import base64
import re
from dataclasses import dataclass

# Define the frontend directory
frontend_dir = (Path(__file__).parent / "frontend").absolute()
_component_func = components.declare_component(
    "markdown_editor", path=str(frontend_dir)
)

@dataclass
class MarkdownResult:
    """Dataclass to store output of Markdown Editor Component.

    Attributes
    ----------
    content: str
        The processed markdown content with embedded images.
    raw_content: str
        The original unprocessed markdown content.
    """
    content: str | None = None
    raw_content: str | None = None

def markdown_editor(
    height: Optional[int] = 400,
    key: Optional[str] = "markdown_editor",
) -> MarkdownResult:
    """
    Create a markdown editor component that handles text and image embedding.

    Parameters
    ----------
    height : int, optional
        Height of the editor in pixels, by default 400
    key : str, optional
        Unique key for the component, by default "markdown_editor"

    Returns
    -------
    MarkdownResult
        Contains both processed and raw markdown content
    """
    raw_content = _component_func(
        key=key,
        default=None,
        height=height
    )
    
    if raw_content:
        # Process markdown content and convert images to base64
        def download_and_convert_image(url: str) -> str | None:
            try:
                response = requests.get(url)
                if response.status_code == 200:
                    content_type = response.headers.get('content-type', 'image/jpeg')
                    img_data = base64.b64encode(response.content).decode('utf-8')
                    return f"data:{content_type};base64,{img_data}"
            except Exception:
                return None
            return None

        # Find and replace image URLs with base64 data
        img_pattern = r'!\[([^\]]*)\]\(([^)]+)\)'
        def replace_image(match):
            alt_text, url = match.groups()
            base64_image = download_and_convert_image(url)
            if base64_image:
                return f'![{alt_text}]({base64_image})'
            return match.group(0)
            
        processed_content = re.sub(img_pattern, replace_image, raw_content) if raw_content else ""
        
        return MarkdownResult(
            content=processed_content,
            raw_content=raw_content
        )
    return MarkdownResult()
