from langchain_aws import ChatBedrockConverse
from config.settings import LLMConfig
from models.interfaces import LLMInterface

class BedrockLLM(LLMInterface):
    def __init__(self, config: LLMConfig):
        self.llm = ChatBedrockConverse(
            region_name=config.region_name,
            model=config.model_name,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
        )
    
    def stream(self, messages):
        return self.llm.stream(messages)
