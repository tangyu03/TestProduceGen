"""Unified LLM Client Module.

Provides a centralized, reusable LLM client architecture that supports
multiple task types, caching, configuration management, and monitoring.

Usage:
    from tools.llm import LLMClient, TaskType

    # Create client for a specific task type
    client = LLMClient(TaskType.TITLE_GENERATION)

    # Make a simple chat call
    response = await client.chat(
        system_prompt="You are a helpful assistant.",
        user_message="Generate a title for this test case."
    )

    # Make a JSON call with caching
    result = await client.chat_json(
        system_prompt="You are a JSON generator.",
        user_message="Generate a JSON object."
    )
"""

from .client import LLMClient
from .config import LLMConfig, LLMTaskConfig
from .task_types import TaskType, TaskConfig

__all__ = [
    'LLMClient',
    'LLMConfig',
    'LLMTaskConfig',
    'TaskType',
    'TaskConfig',
]