# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""
Shows how to use the Converse API with DeepSeek-R1 (on demand) using streaming.
"""

import logging
import boto3

from botocore.client import Config
from botocore.exceptions import ClientError


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def stream_conversation(bedrock_client, model_id, system_prompts, messages):
    """
    Sends messages to a model and streams the response.
    Args:
        bedrock_client: The Boto3 Bedrock runtime client.
        model_id (str): The model ID to use.
        system_prompts (JSON): The system prompts for the model to use.
        messages (JSON): The messages to send to the model.

    Returns:
        response (JSON): The conversation that the model generated.
    """

    logger.info("Streaming message with model %s", model_id)

    # Inference parameters to use.
    temperature = 0.5
    max_tokens = 4096

    # Base inference parameters to use.
    inference_config = {
        "temperature": temperature,
        "maxTokens": max_tokens,
    }

    # Send the message and get streaming response
    response = bedrock_client.converse_stream(
        modelId=model_id,
        messages=messages,
        system=system_prompts,
        inferenceConfig=inference_config,
    )

    # Process the streaming response
    stream = response.get("stream")
    if stream:
        full_content = []
        current_text = ""
        current_reasoning_text = ""
        is_reasoning = False
        has_reasoning = False

        for event in stream:
            # print(event)
            if "messageStart" in event:
                print(f"\nRole: {event['messageStart']['role']}")

            if "contentBlockStart" in event:
                content_block = event["contentBlockStart"]
                if content_block.get("reasoningContent"):
                    is_reasoning = True
                    has_reasoning = True
                    print("\n[Reasoning Block Start]")
                    current_reasoning_text = ""
                else:
                    is_reasoning = False
                    current_text = ""

            if "contentBlockDelta" in event:
                delta = event["contentBlockDelta"]["delta"]

                # Handle reasoning content - checking the exact structure from the terminal output
                if "reasoningContent" in delta:
                    if not is_reasoning:
                        is_reasoning = True
                        print("\n[Reasoning Block Start]")
                    reason_text = delta["reasoningContent"]["text"]
                    current_reasoning_text += reason_text
                    print(f"{reason_text}", end="", flush=True)
                # Handle regular text content
                elif "text" in delta:
                    delta_text = delta["text"]
                    current_text += delta_text
                    if not is_reasoning:  # Only print non-reasoning text
                        print(delta_text, end="", flush=True)

            if "contentBlockStop" in event:
                content_block_stop = event["contentBlockStop"]
                if content_block_stop.get("reasoningContent"):
                    # Add the completed reasoning content block
                    full_content.append(
                        {
                            "reasoningContent": {
                                "reasoningText": {"text": current_reasoning_text}
                            }
                        }
                    )
                    print("\n[Reasoning Block End]")
                    is_reasoning = False
                elif current_text:
                    # Add the completed text content block
                    full_content.append({"text": current_text})
                    current_text = ""

            if "messageStop" in event:
                print(f"\nStop reason: {event['messageStop']['stopReason']}")

            if "metadata" in event:
                metadata = event["metadata"]
                if "usage" in metadata:
                    logger.info("Input tokens: %s", metadata["usage"]["inputTokens"])
                    logger.info("Output tokens: %s", metadata["usage"]["outputTokens"])
                    logger.info("Total tokens: %s", metadata["usage"]["totalTokens"])

                if "metrics" in metadata:
                    logger.info(
                        "Latency: %s milliseconds", metadata["metrics"]["latencyMs"]
                    )

        # Create a response message object with the assembled content
        output_message = {"role": "assistant", "content": full_content}

        # Log if reasoning was found
        if has_reasoning:
            logger.info("Reasoning content was included in the response")
        else:
            logger.info("No reasoning content was detected in the response")

        return output_message


def main():
    """
    Entrypoint for DeepSeek-R1 streaming example.
    """

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    model_id = "us.deepseek.r1-v1:0"

    # Setup the system prompts and messages to send to the model.
    system_prompts = [
        {
            "text": "You are an AI assistant that helps users analyze complex problems. Please include your reasoning process."
        }
    ]
    message_1 = {"role": "user", "content": [{"text": "How many r in strawberry?"}]}
    message_2 = {
        "role": "user",
        "content": [{"text": "Are you sure? Think it out carefully."}],
    }
    messages = []

    try:
        # Configure timeout for long responses if needed
        custom_config = Config(connect_timeout=840, read_timeout=840)
        bedrock_client = boto3.client(
            service_name="bedrock-runtime", config=custom_config
        )

        # Start the conversation with the 1st message.
        messages.append(message_1)
        output_message = stream_conversation(
            bedrock_client, model_id, system_prompts, messages
        )

        # Add the response message to the conversation.
        # Filter out reasoning content for conversation history
        filtered_content = []
        for content in output_message["content"]:
            if not content.get("reasoningContent"):
                filtered_content.append(content)

        messages.append({"role": "assistant", "content": filtered_content})

        print("\n\nContinuing conversation...\n")

        # Continue the conversation with the 2nd message.
        messages.append(message_2)
        output_message = stream_conversation(
            bedrock_client, model_id, system_prompts, messages
        )

        # Filter out reasoning content for conversation history again
        filtered_content = []
        for content in output_message["content"]:
            if not content.get("reasoningContent"):
                filtered_content.append(content)

        messages.append({"role": "assistant", "content": filtered_content})

        # Show the complete conversation (optional)
        print("\n\nComplete conversation history:")
        for message in messages:
            print(f"Role: {message['role']}")
            for content in message["content"]:
                if content.get("text"):
                    print(f"Text: {content['text']}")
            print()

    except ClientError as err:
        message = err.response["Error"]["Message"]
        logger.error("A client error occurred: %s", message)
        print(f"A client error occured: {message}")

    else:
        print(f"\nFinished streaming text with model {model_id}.")


if __name__ == "__main__":
    main()
