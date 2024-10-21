from typing import cast
import boto3
import dotenv
import streamlit as st
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from langchain.schema import AIMessage, HumanMessage
from langchain_aws import ChatBedrockConverse
from langchain_core.messages.ai import AIMessageChunk

# Load environment variables
## DO NOT COMMIT .env --> ADD to .gitignore
dotenv.load_dotenv()

# Set page configuration
st.set_page_config(page_title="RockTalk", page_icon="🪨", layout="wide")

st.header("RockTalk: Powered by AWS Bedrock 🪨 + LangChain 🦜️🔗 + Streamlit 👑")


# Initialize chat history stored in Streamlit session
if "messages" not in st.session_state:
    st.session_state.messages = []
    print("--- Chat history initialized ---")


# Initialize LLM object stored in Streamlit session
if "llm" not in st.session_state:
    st.session_state.llm = ChatBedrockConverse(
        region_name="us-west-2",
        model="anthropic.claude-3-sonnet-20240229-v1:0",
        temperature=0,
        max_tokens=None,
        # stop_sequences: Optional[List[str]] = Field(default=None, alias="stop")
        # temperature: Optional[float] = None
        # top_p: Optional[float] = None
    )
    print("--- LLM initialized ---")

# Reuse LLM object stored in Streamlit session
llm = st.session_state.llm

# Loop through messages list (chat history) and display in streamlit chat message container
for message in st.session_state.messages:
    # The "role" key in the additional_kwargs dict is used to determine the role icon (user or assistant) to use
    with st.chat_message(message.additional_kwargs["role"]):
        st.markdown(message.content)

# st.chat_input creates a chat input box in the Streamlit app. The user can enter a message and it will be displayed in the chat message container.
# The string "Hello!" is used as a placeholder for the user's message.
if prompt := st.chat_input("Hello!"):
    print(f"\nHuman: {prompt}")
    print("AI: ")

    # Display user message in chat message container
    with st.chat_message("user"):
        st.markdown(prompt)

    # Add user message to session chat history
    human_input = HumanMessage(content=prompt, additional_kwargs={"role": "user"})
    st.session_state.messages.append(human_input)

    # Stream response from LLM and display in chat message container
    # Notice we send the list of messages so the bot remembers previous dialogues within the chat session
    # stream_iterator = llm.stream(st.session_state.messages)
    with st.chat_message("assistant"):
        # Start with an empty message container for the assistant
        message_placeholder = st.empty()

        # Stream response from LLM in chunks and display in chat message container for real time chat experience
        full_response = ""
        for chunk in llm.stream(st.session_state.messages):
            chunk = cast(AIMessageChunk, chunk)
            for item in chunk.content:
                if isinstance(item, dict) and "text" in item:
                    text = item["text"]
                    full_response += text
                    print(text, end="", flush=True)
                elif "index" in item and item["index"] == 0:  # type:ignore
                    print("\nEOF?\n")
                else:
                    print(f"Unexpected chunk type: {item}")

                # Add a blinking cursor to simulate typing
                message_placeholder.markdown(full_response + "▌")

            # print metadata information
            if chunk.response_metadata:
                print(chunk.response_metadata)
            if chunk.usage_metadata:
                print(type(chunk))
                print(chunk.usage_metadata)

        # Add the final response to the chat history
        ai_response = AIMessage(
            content=full_response, additional_kwargs={"role": "assistant"}
        )
        st.session_state.messages.append(ai_response)

        # display in chat message container
        message_placeholder.markdown(full_response)
