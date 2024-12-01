import functools
import json
import uuid
from datetime import datetime
from enum import Enum
from typing import Dict, List, Literal, Optional

import streamlit as st
import streamlit.components.v1 as stcomponents
from langchain.schema import AIMessage, BaseMessage, HumanMessage, SystemMessage
from PIL.ImageFile import ImageFile
from pydantic import BaseModel, Field
from streamlit_chat_prompt import ImageData, PromptReturn, prompt
from streamlit_js_eval import streamlit_js_eval
from streamlit_theme import st_theme, stylized_container
from utils.image_utils import MAX_IMAGE_WIDTH, image_from_b64_image
from utils.log import logger
from utils.streamlit_utils import close_dialog


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


# def copy_value_to_clipboard(value: str):
#     value = json.dumps(value)
#     # with stylized_container("copy_to_clipboard_boo"):
#     stcomponents.html(
#         """<script>
# function copyFunction(textToCopy) {
#     try {
#         const parentDoc = window.parent.document;

#         console.log("textToCopy:", textToCopy);

#         // Try using the parent window's clipboard API first
#         if (window.parent.navigator.clipboard) {
#             window.parent.navigator.clipboard.writeText(textToCopy)
#                 .then(() => {
#                     console.log('Text copied successfully');
#                 })
#                 .catch((err) => {
#                     console.error('Clipboard API failed:', err);
#                     fallbackCopy(textToCopy, parentDoc);
#                 });
#         } else {
#             fallbackCopy(textToCopy, parentDoc);
#         }
#     } catch (err) {
#         console.error('Copy failed:', err);
#     }
# }

# function fallbackCopy(text, parentDoc) {
#     try {
#         const textarea = parentDoc.createElement('textarea');
#         textarea.value = text;
#         textarea.style.position = 'fixed';
#         textarea.style.opacity = '0';

#         parentDoc.body.appendChild(textarea);
#         textarea.focus();
#         textarea.select();

#         try {
#             parentDoc.execCommand('copy');
#             console.log('Text copied using fallback method');
#         } catch (execErr) {
#             console.error('execCommand failed:', execErr);
#         }

#         parentDoc.body.removeChild(textarea);
#     } catch (err) {
#         console.error('Fallback copy failed:', err);

#         // Last resort fallback
#         try {
#             const tempInput = parentDoc.createElement('input');
#             tempInput.value = text;
#             tempInput.style.position = 'fixed';
#             tempInput.style.opacity = '0';

#             parentDoc.body.appendChild(tempInput);
#             tempInput.select();
#             tempInput.setSelectionRange(0, 99999);

#             parentDoc.execCommand('copy');
#             parentDoc.body.removeChild(tempInput);
#             console.log('Text copied using last resort method');
#         } catch (finalErr) {
#             console.error('All copy methods failed:', finalErr);
#         }
#     }
# }

# // For the clipboard API not working on subsequent loads,
# // try to reinitialize it each time
# function initAndCopy(textToCopy) {
#     if (window.parent.navigator.clipboard) {
#         // Force clipboard permission check
#         window.parent.navigator.permissions.query({name: 'clipboard-write'})
#             .then(result => {
#                 console.log('Clipboard permission:', result.state);
#                 copyFunction(textToCopy);
#             })
#             .catch(() => {
#                 copyFunction(textToCopy);
#             });
#     } else {
#         copyFunction(textToCopy);
#     }
# }"""
#         + f"""
#     initAndCopy({value});
#     </script>
#     """,
#         height=0,
#         # width=0,
#     )
#     st.toast(body="Copied to clipboard", icon="📋")


class LLMParameters(BaseModel):
    temperature: float
    max_output_tokens: Optional[int] = None
    top_p: Optional[float] = None
    top_k: Optional[int] = None  # Additional parameter for Anthropic models


class LLMPresetName(Enum):
    BALANCED = "Balanced"
    DETERMINISTIC = "Deterministic"
    CREATIVE = "Creative"
    CUSTOM = "Custom"


PRESET_CONFIGS: Dict[LLMPresetName, LLMParameters] = {
    LLMPresetName.DETERMINISTIC: LLMParameters(temperature=0.0),
    LLMPresetName.CREATIVE: LLMParameters(temperature=0.9),
    LLMPresetName.BALANCED: LLMParameters(temperature=0.5),
}


_DEFAULT_LLM_CONFIG: Optional["LLMConfig"] = None


class LLMConfig(BaseModel):
    bedrock_model_id: str
    region_name: str
    parameters: LLMParameters
    stop_sequences: List[str] = Field(default_factory=list)
    system: Optional[str] = None

    # guardrail_config: Optional[Dict[str, Any]] = None
    # additional_model_request_fields: Optional[Dict[str, Any]] = None
    # additional_model_response_field_paths: Optional[List[str]] = None
    # disable_streaming: bool = False
    # supports_tool_choice_values: Optional[Sequence[Literal["auto", "any", "tool"]]] = (
    #     None
    # )

    def get_parameters(self) -> LLMParameters:
        return self.parameters

    @staticmethod
    def get_default() -> "LLMConfig":
        global _DEFAULT_LLM_CONFIG
        if _DEFAULT_LLM_CONFIG is None:
            preset_parm = PRESET_CONFIGS[LLMPresetName.BALANCED]
            _DEFAULT_LLM_CONFIG = LLMConfig(
                bedrock_model_id="anthropic.claude-3-5-sonnet-20241022-v2:0",
                region_name="us-west-2",  # TODO use AWS_REGION
                parameters=preset_parm,
            )

        return _DEFAULT_LLM_CONFIG.model_copy(deep=True)

    @staticmethod
    def set_default(llm_config: "LLMConfig") -> None:
        global _DEFAULT_LLM_CONFIG
        _DEFAULT_LLM_CONFIG = llm_config.model_copy(deep=True)


class TurnState(Enum):
    """Enum representing the current turn state in the conversation.

    Attributes:
        HUMAN_TURN: Waiting for human input.
        AI_TURN: Waiting for AI response.
        COMPLETE: Conversation is complete.
    """

    HUMAN_TURN = "human_turn"
    AI_TURN = "ai_turn"
    COMPLETE = "complete"


class ChatMessage(BaseModel):
    session_id: str
    role: str
    content: str | list[str | dict]
    index: int
    metadata: Optional[Dict] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)

    @st.dialog("Edit Message")
    def edit_message(self):
        previous_prompt = self.to_prompt_return()
        logger.debug(f"Editing message: {previous_prompt}")
        st.warning(
            "Editing message will re-run conversation from this point and will replace any existing conversation past this point!",
            icon="⚠️",
        )
        prompt_return = prompt(
            "edit prompt",
            key=f"edit_prompt_{id(self)}",
            placeholder=previous_prompt.text or "",
            main_bottom=False,
            default=previous_prompt,
        )

        if prompt_return:
            st.session_state.edit_message_value = self, prompt_return
            close_dialog()
            st.rerun()

        st.divider()
        # Delete option
        if st.button(
            "🗑️ Delete Messages Hence",
            key=f"delete_message_edit_dialog",
            type="secondary",
            use_container_width=True,
        ):
            if st.session_state.get(
                f"confirm_delete_message_edit_dialog",
                False,
            ):
                st.session_state.edit_message_value = self, None
                st.session_state["confirm_delete_message_edit_dialog"] = None
                close_dialog()
                st.rerun()
            else:
                st.session_state[f"confirm_delete_message_edit_dialog"] = True
                st.warning("Click again to confirm deletion")

    def display(self) -> None:
        # Only show edit button for user messages
        text: str = ""
        with st.container(border=True, key=f"message_container_{id(self)}"):
            with st.chat_message(self.role):
                if isinstance(self.content, str):
                    text = self.content
                elif isinstance(self.content, list):
                    for item in self.content:
                        if isinstance(item, dict):
                            if item["type"] == "text":
                                text += item["text"]
                            elif item["type"] == "image":
                                pil_image: ImageFile = image_from_b64_image(
                                    item["source"]["data"]
                                )
                                width: int = pil_image.size[0]
                                st.image(
                                    image=pil_image, width=min(width, MAX_IMAGE_WIDTH)
                                )
                        else:
                            text = str(item)
                if text:
                    st.markdown(text)

            def copy_button():
                copy_key = f"copy_{id(self)}"
                # expand_button_height(target_key=copy_key)
                return st.button(
                    "📋",
                    key=copy_key,
                    # on_click=functools.partial(copy_value_to_clipboard, text),
                    # use_container_width=True,
                )

            message_button_container_key = f"message_button_container_{id(self)}"
            message_button_container = st.container(
                border=False, key=message_button_container_key
            )
            with message_button_container:
                st.markdown(
                    f"<div style='text-align: right; font-size: 0.8em; color: grey;'>{self.created_at.strftime('%Y-%m-%d %H:%M:%S')}</div>",
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f"""
                        <style>
                        .st-key-{message_button_container_key} button {{
                            padding: 2px 8px;  /* Reduce padding */
                            font-size: 14px;   /* Smaller font */
                            height: auto;      /* Override default height */
                            min-height: 32px;  /* Set minimum height */
                            border-radius: 4px; /* Slightly rounded corners */
                            background-color: transparent;
                            //border: none;
                            //color: #666;
                        }}

                        /* Force columns to maintain width */
                        .st-key-{message_button_container_key} .row-widget {{
                            display: flex;
                            justify-content: center;
                            //gap: 2rem;
                            width: auto !important;
                            max-width: 300px; /* Adjust max-width as needed */
                            margin: 0 auto;
                        }}

                        .st-key-{message_button_container_key} [data-testid="column"] {{
                            width: auto !important;
                            flex: 0 1 auto !important;
                            min-width: unset !important;
                        }}

                        /* Center the button container */
                        .st-key-{message_button_container_key} {{
                            display: flex;
                            flex-direction: column;
                            align-items: center;
                        }}
                        </style>
                    """,
                    unsafe_allow_html=True,
                )
                subcol1, subcol2 = st.columns((1) * 2)
                with subcol1:
                    copy_text = copy_button()
                if self.role == "user":
                    with subcol2:
                        button_key = f"edit_{id(self)}"
                        # expand_button_height(target_key=f"{button_key}")
                        if st.button(
                            "✎",
                            key=button_key,
                            # use_container_width=True,
                        ):
                            self.edit_message()
                if copy_text:

                    # with st.container(
                    #     height=0,
                    #     key="foo",
                    # ):
                    #     # with stylized_container(key="foo"):
                    #     # ...
                    #     st.markdown(
                    #         """<style>
                    # .st-key-foo {
                    #     display: none !important;
                    # }
                    # .st-key-foo [data-testid="stVerticalBlockBorderWrapper"],
                    # .st-key-foo + [data-testid="stVerticalBlockBorderWrapper"],
                    # .st-key-foo:closest([data-testid="stVerticalBlockBorderWrapper"]) {
                    #     display: none !important;
                    # }
                    # </style>""",
                    #         unsafe_allow_html=True,
                    #     )
                    copy_value_to_clipboard(text)

    def convert_to_llm_message(self) -> BaseMessage:
        """Convert ChatMessage to LangChain message format.

        Args:
            message: ChatMessage to convert.

        Returns:
            LangChain message object (either HumanMessage or AIMessage).
        """
        if self.role == "system":
            return SystemMessage(
                content=self.content, additional_kwargs={"role": "system"}
            )
        elif self.role == "user":
            return HumanMessage(
                content=self.content, additional_kwargs={"role": "user"}
            )
        elif self.role == "assistant":
            return AIMessage(
                content=self.content, additional_kwargs={"role": "assistant"}
            )
        raise ValueError(f"Unsupported message role: {self.role}")

    @staticmethod
    def create_from_prompt(
        prompt_data: PromptReturn,
        session_id: Optional[str] = None,
        index: Optional[int] = None,
    ) -> "ChatMessage":
        """Create ChatMessage from user input.

        Args:
            prompt_data: User input containing message and optional images.
            session_id: Optional session ID for the message.
            index: Optional index for the message.

        Returns:
            ChatMessage object containing the user input.
        """
        content = []
        if prompt_data.text:
            content.append({"type": "text", "text": prompt_data.text})
        if prompt_data.images:
            for image in prompt_data.images:
                content.append(
                    {
                        "type": "image",
                        "source": {
                            "type": image.format,
                            "media_type": image.type,
                            "data": image.data,
                        },
                    }
                )

        return ChatMessage(
            session_id=session_id or "",
            role="user",
            content=content,
            index=index if index is not None else len(st.session_state.messages),
        )

    def to_prompt_return(self) -> PromptReturn:
        """Convert ChatMessage back to PromptReturn format.

        Returns:
            PromptReturn object containing the message text and any images.
        """
        text = None
        images = []
        logger.info(self.content)
        if isinstance(self.content, list):
            for item in self.content:
                if isinstance(item, dict):
                    if item["type"] == "text":
                        text = item["text"]
                    elif item["type"] == "image":
                        images.append(
                            ImageData(
                                format=item["source"]["type"],
                                type=item["source"]["media_type"],
                                data=item["source"]["data"],
                            )
                        )
        elif isinstance(self.content, str):
            text = self.content

        return PromptReturn(text=text, images=images if images else None)


class ChatSession(BaseModel):
    session_id: str
    title: str
    metadata: Optional[Dict] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)
    last_active: datetime = Field(default_factory=datetime.now)
    message_count: Optional[int] = None
    first_message: Optional[datetime] = None
    last_message: Optional[datetime] = None
    config: LLMConfig = Field(default_factory=LLMConfig.get_default)

    @staticmethod
    def create(
        title: str,
        metadata: Optional[Dict] = None,
        created_at: Optional[datetime] = None,
        last_active: Optional[datetime] = None,
        config: Optional[LLMConfig] = None,
    ) -> "ChatSession":
        """Create a new chat session"""
        session_id = str(uuid.uuid4())
        current_time = datetime.now()
        created_at = created_at or current_time
        last_active = last_active or created_at

        return ChatSession(
            session_id=session_id,
            title=title,
            metadata=metadata or {},
            created_at=created_at,
            last_active=last_active,
            config=config or st.session_state.llm.get_config(),
        )


class ChatExport(BaseModel):
    session: ChatSession
    messages: List[ChatMessage]
    exported_at: datetime = Field(default_factory=datetime.now)
