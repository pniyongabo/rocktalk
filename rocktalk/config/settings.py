import os
from dataclasses import dataclass
from typing import Optional

import dotenv


@dataclass
class LLMConfig:
    model_name: str
    temperature: float
    max_tokens: Optional[int]
    region_name: str


@dataclass
class AppConfig:
    page_title: str = "RockTalk"
    page_icon: str = "🪨"
    layout: str = "wide"
    db_path: str = "chat_database.db"

    @classmethod
    def get_llm_config(cls) -> LLMConfig:
        return LLMConfig(
            model_name="anthropic.claude-3-sonnet-20240229-v1:0",
            temperature=0,
            max_tokens=None,
            region_name="us-west-2",
        )


# Load environment variables
dotenv.load_dotenv()
