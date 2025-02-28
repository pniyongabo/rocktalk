from langchain_aws import ChatBedrockConverse
from langchain.schema import BaseMessage, HumanMessage, SystemMessage
from langchain_aws import ChatBedrockConverse
from langchain_core.messages.base import BaseMessageChunk

# pip install -e "git+https://github.com/langchain-ai/langchain-aws.git1c507397c9b037826f25d5181983a9e7ee4c6c8e#egg=langchain-aws&subdirectory=libs/aws" # install a python package from a repo subdirectory

think_params = {"thinking": {"type": "enabled", "budget_tokens": 16000}}

llm_converse = ChatBedrockConverse(
    model="us.anthropic.claude-3-7-sonnet-20250219-v1:0",
    temperature=1,
    max_tokens=16001,
    region_name="us-west-2",
    additional_model_request_fields=think_params,
)

messages = [
    SystemMessage(content="You are a helpful assistant."),
    HumanMessage(content="Come up with an explanation on how to calculate Pi."),
]

# ai_msg = llm_converse.invoke(messages)

for chunk in llm_converse.stream(messages):
    print(chunk)
