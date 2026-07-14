from __future__ import annotations
"""Task Type Definitions and Default Configurations.

Defines supported LLM task types and their default configuration templates.
Each task type has specific parameters optimized for its use case.
"""
from enum import Enum
from dataclasses import dataclass, field


class TaskType(Enum):
    """Supported LLM task types.

    Each task type has a specific purpose and default configuration
    optimized for that use case.
    """
    TITLE_GENERATION = "title_generation"    # Generate test case titles
    FIELD_VALIDATION = "field_validation"    # Generate field validation V-steps
    SIGNAL_VALIDATION = "signal_validation"  # Generate signal-type-aware V-steps
    S0_FALLBACK = "s0_fallback"              # Fallback for S0 topology discovery
    GENERAL = "general"                       # Generic LLM tasks


@dataclass
class TaskConfigTemplate:
    """Default configuration template for a task type.

    Attributes:
        model: Default model name for this task type
        temperature: Sampling temperature (0.0-1.0)
        max_tokens: Maximum tokens to generate (None for dynamic)
        batch_size: Default batch size for processing multiple items
        timeout: Request timeout in seconds
        cache_enabled: Whether caching is enabled by default
        retry_max_attempts: Maximum retry attempts for failed requests
        retry_backoff_factor: Exponential backoff factor for retries
        retry_rate_limit_wait: Wait time in seconds for rate limit errors
    """
    model: str
    temperature: float
    max_tokens: int | None
    batch_size: int
    timeout: int
    cache_enabled: bool = True
    retry_max_attempts: int = 3
    retry_backoff_factor: float = 2.0
    retry_rate_limit_wait: int = 10


class TaskConfig:
    """Registry of task type configurations.

    Provides default configuration templates for each task type.
    """

    # Configuration templates for each task type
    TEMPLATES: dict[TaskType, TaskConfigTemplate] = {
        TaskType.TITLE_GENERATION: TaskConfigTemplate(
            model="glm-4-flash",
            temperature=0.3,
            max_tokens=256,
            batch_size=20,
            timeout=60,
            cache_enabled=True,
            retry_max_attempts=3,
            retry_backoff_factor=2.0,
            retry_rate_limit_wait=10,
        ),
        TaskType.FIELD_VALIDATION: TaskConfigTemplate(
            model="glm-4-flash",
            temperature=0.1,
            max_tokens=None,  # Dynamic calculation: len(batch) * 150 + 300
            batch_size=10,
            timeout=180,
            cache_enabled=True,
            retry_max_attempts=3,
            retry_backoff_factor=2.0,
            retry_rate_limit_wait=10,
        ),
        TaskType.SIGNAL_VALIDATION: TaskConfigTemplate(
            model="glm-4-flash",
            temperature=0.15,             # Low temp for deterministic V-step structure
            max_tokens=None,              # Dynamic: len(batch) * 300 + 400
            batch_size=8,                 # Smaller batches — richer per-BR output
            timeout=180,
            cache_enabled=True,
            retry_max_attempts=3,
            retry_backoff_factor=2.0,
            retry_rate_limit_wait=10,
        ),
        TaskType.S0_FALLBACK: TaskConfigTemplate(
            model="glm-4-plus",
            temperature=0.2,
            max_tokens=8192,
            batch_size=5,
            timeout=120,
            cache_enabled=False,  # S0 fallback should not cache
            retry_max_attempts=2,
            retry_backoff_factor=1.5,
            retry_rate_limit_wait=10,
        ),
        TaskType.GENERAL: TaskConfigTemplate(
            model="glm-4-flash",
            temperature=0.5,
            max_tokens=2048,
            batch_size=10,
            timeout=90,
            cache_enabled=False,
            retry_max_attempts=3,
            retry_backoff_factor=2.0,
            retry_rate_limit_wait=10,
        ),
    }

    @classmethod
    def get_template(cls, task_type: TaskType) -> TaskConfigTemplate:
        """Get the default configuration template for a task type.

        Args:
            task_type: The task type to get configuration for

        Returns:
            Configuration template for the task type

        Raises:
            KeyError: If task type is not registered
        """
        if task_type not in cls.TEMPLATES:
            raise KeyError(f"Unknown task type: {task_type}")
        return cls.TEMPLATES[task_type]

    @classmethod
    def register_template(cls, task_type: TaskType, template: TaskConfigTemplate) -> None:
        """Register a new or updated configuration template for a task type.

        Args:
            task_type: The task type to register configuration for
            template: The configuration template
        """
        cls.TEMPLATES[task_type] = template

    @classmethod
    def get_default_model(cls, task_type: TaskType) -> str:
        """Get the default model name for a task type.

        Args:
            task_type: The task type

        Returns:
            Default model name
        """
        return cls.get_template(task_type).model

    @classmethod
    def get_batch_size(cls, task_type: TaskType) -> int:
        """Get the default batch size for a task type.

        Args:
            task_type: The task type

        Returns:
            Default batch size
        """
        return cls.get_template(task_type).batch_size

    @classmethod
    def get_cache_enabled(cls, task_type: TaskType) -> bool:
        """Get whether caching is enabled by default for a task type.

        Args:
            task_type: The task type

        Returns:
            True if caching is enabled by default
        """
        return cls.get_template(task_type).cache_enabled


# Backward compatibility aliases for existing code
TITLE_GENERATION_CONFIG = TaskConfig.get_template(TaskType.TITLE_GENERATION)
FIELD_VALIDATION_CONFIG = TaskConfig.get_template(TaskType.FIELD_VALIDATION)
SIGNAL_VALIDATION_CONFIG = TaskConfig.get_template(TaskType.SIGNAL_VALIDATION)