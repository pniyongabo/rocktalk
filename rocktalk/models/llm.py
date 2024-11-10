from langchain_core.messages.base import BaseMessageChunk
from config.settings import LLMConfig
from langchain_aws import ChatBedrockConverse
from typing import Any, Iterator, List, Protocol

from langchain.schema import BaseMessage


class LLMInterface(Protocol):
    def stream(self, input: List[BaseMessage]) -> Iterator[BaseMessageChunk]: ...
    def invoke(self, input: List[BaseMessage]) -> BaseMessage: ...


class BedrockLLM(LLMInterface):
    def __init__(self, config: LLMConfig) -> None:
        self.llm = ChatBedrockConverse(
            region_name=config.region_name,
            model=config.model_name,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
        )

    def stream(self, input) -> Iterator[BaseMessageChunk]:
        return self.llm.stream(input=input)

    def invoke(self, input) -> BaseMessage:
        return self.llm.invoke(input=input)
