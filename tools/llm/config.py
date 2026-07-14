from __future__ import annotations
"""Unified LLM Configuration Management.

Provides centralized configuration loading and management for all LLM tasks.
Configuration priority: Environment variables > config.json > Task defaults.
"""
import json
import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any

from .task_types import TaskType, TaskConfig, TaskConfigTemplate


@dataclass
class LLMTaskConfig:
    """Configuration for a specific LLM task type.

    Contains all parameters needed for LLM API calls, caching, and retry logic.

    Attributes:
        api_base: Base URL for the LLM API
        api_key: API key for authentication
        model: Model name to use
        temperature: Sampling temperature (0.0-1.0)
        max_tokens: Maximum tokens to generate (None for dynamic calculation)
        batch_size: Default batch size for processing multiple items
        timeout: Request timeout in seconds
        cache_enabled: Whether caching is enabled
        retry_max_attempts: Maximum retry attempts for failed requests
        retry_backoff_factor: Exponential backoff factor for retries
        retry_rate_limit_wait: Wait time in seconds for rate limit errors
        cache_dir: Directory for cache storage
        cache_ttl_days: Cache time-to-live in days
    """
    api_base: str
    api_key: str
    model: str
    temperature: float
    max_tokens: int | None
    batch_size: int
    timeout: int
    cache_enabled: bool
    retry_max_attempts: int
    retry_backoff_factor: float
    retry_rate_limit_wait: int
    cache_dir: str
    cache_ttl_days: int = 7

    def get_cache_enabled(self) -> bool:
        """Check if caching is enabled and API key is available."""
        return self.cache_enabled and bool(self.api_key)


class LLMConfig:
    """Unified LLM configuration manager.

    Handles configuration loading with the following priority:
    1. Environment variables (highest priority)
    2. config.json file
    3. Task type defaults (lowest priority)
    """

    # Default configuration values
    DEFAULT_API_BASE = "https://open.bigmodel.cn/api/paas/v4"
    DEFAULT_CACHE_DIR = "cache"
    DEFAULT_CACHE_TTL_DAYS = 7

    # Environment variable names
    ENV_API_BASE = "LLM_API_BASE"
    ENV_API_KEY = "LLM_API_KEY"
    ENV_CACHE_DIR = "LLM_CACHE_DIR"
    ENV_CACHE_TTL_DAYS = "LLM_CACHE_TTL_DAYS"

    # Legacy environment variables for backward compatibility
    ENV_TITLE_MODEL = "LLM_TITLE_MODEL"
    ENV_FV_MODEL = "LLM_FV_MODEL"

    @classmethod
    def load_config_file(cls, config_path: str | None = None) -> dict[str, Any]:
        """Load configuration from config.json file.

        Args:
            config_path: Path to config.json. If None, looks in project root.

        Returns:
            Configuration dictionary, empty dict if file not found or invalid
        """
        if config_path is None:
            # Default to config.json in project root
            config_path = str(Path(__file__).parent.parent.parent / "config.json")

        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    @classmethod
    def get_config(
        cls,
        task_type: TaskType,
        config_override: dict[str, Any] | None = None,
    ) -> LLMTaskConfig:
        """Get configuration for a specific task type.

        Configuration priority:
        1. config_override dict (highest)
        2. Environment variables
        3. config.json file
        4. Task type defaults (lowest)

        Args:
            task_type: The task type to get configuration for
            config_override: Optional override dictionary

        Returns:
            LLMTaskConfig instance with all parameters resolved
        """
        # Start with task type defaults
        template = TaskConfig.get_template(task_type)

        # Load config.json
        file_config = cls.load_config_file()
        llm_config = file_config.get('llm', {})

        # Build configuration with priority chain
        api_base = cls._resolve_value(
            override=config_override.get('api_base') if config_override else None,
            env_var=cls.ENV_API_BASE,
            file_key='api_base',
            file_value=llm_config.get('api_base'),
            default=cls.DEFAULT_API_BASE,
        ).rstrip('/')

        api_key = cls._resolve_value(
            override=config_override.get('api_key') if config_override else None,
            env_var=cls.ENV_API_KEY,
            file_key='api_key',
            file_value=llm_config.get('api_key'),
            default='',
        )

        # Resolve model: check task-specific config first
        model = cls._resolve_model(
            task_type=task_type,
            override=config_override.get('model') if config_override else None,
            file_config=llm_config,
            template=template,
        )

        # Resolve other parameters
        temperature = cls._resolve_value(
            override=config_override.get('temperature') if config_override else None,
            env_var=None,  # No env var for temperature
            file_key=None,
            file_value=None,
            default=template.temperature,
        )

        max_tokens = cls._resolve_value(
            override=config_override.get('max_tokens') if config_override else None,
            env_var=None,
            file_key=None,
            file_value=None,
            default=template.max_tokens,
        )

        batch_size = cls._resolve_value(
            override=config_override.get('batch_size') if config_override else None,
            env_var=None,
            file_key=None,
            file_value=None,
            default=template.batch_size,
        )

        timeout = cls._resolve_value(
            override=config_override.get('timeout') if config_override else None,
            env_var=None,
            file_key=None,
            file_value=None,
            default=template.timeout,
        )

        # Cache configuration
        cache_config = llm_config.get('cache', {})
        cache_dir = cls._resolve_value(
            override=config_override.get('cache_dir') if config_override else None,
            env_var=cls.ENV_CACHE_DIR,
            file_key='dir',
            file_value=cache_config.get('dir'),
            default=cls.DEFAULT_CACHE_DIR,
        )

        cache_enabled = cls._resolve_value(
            override=config_override.get('cache_enabled') if config_override else None,
            env_var=None,
            file_key='enabled',
            file_value=cache_config.get('enabled'),
            default=template.cache_enabled,
        )

        cache_ttl_days = cls._resolve_value(
            override=config_override.get('cache_ttl_days') if config_override else None,
            env_var=cls.ENV_CACHE_TTL_DAYS,
            file_key='ttl_days',
            file_value=cache_config.get('ttl_days'),
            default=cls.DEFAULT_CACHE_TTL_DAYS,
        )

        # Retry configuration
        retry_config = llm_config.get('retry', {})
        retry_max_attempts = cls._resolve_value(
            override=config_override.get('retry_max_attempts') if config_override else None,
            env_var=None,
            file_key='max_attempts',
            file_value=retry_config.get('max_attempts'),
            default=template.retry_max_attempts,
        )

        retry_backoff_factor = cls._resolve_value(
            override=config_override.get('retry_backoff_factor') if config_override else None,
            env_var=None,
            file_key='backoff_factor',
            file_value=retry_config.get('backoff_factor'),
            default=template.retry_backoff_factor,
        )

        retry_rate_limit_wait = cls._resolve_value(
            override=config_override.get('retry_rate_limit_wait') if config_override else None,
            env_var=None,
            file_key='rate_limit_wait',
            file_value=retry_config.get('rate_limit_wait'),
            default=template.retry_rate_limit_wait,
        )

        return LLMTaskConfig(
            api_base=api_base,
            api_key=api_key,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            batch_size=batch_size,
            timeout=timeout,
            cache_enabled=cache_enabled,
            retry_max_attempts=retry_max_attempts,
            retry_backoff_factor=retry_backoff_factor,
            retry_rate_limit_wait=retry_rate_limit_wait,
            cache_dir=cache_dir,
            cache_ttl_days=cache_ttl_days,
        )

    @classmethod
    def _resolve_value(
        cls,
        override: Any | None,
        env_var: str | None,
        file_key: str | None,
        file_value: Any | None,
        default: Any,
    ) -> Any:
        """Resolve a configuration value with priority chain.

        Priority: override > env_var > file_value > default

        Args:
            override: Explicit override value
            env_var: Environment variable name
            file_key: Key in config.json
            file_value: Value from config.json
            default: Default value

        Returns:
            Resolved configuration value
        """
        if override is not None:
            return override

        if env_var:
            env_value = os.environ.get(env_var)
            if env_value is not None:
                return env_value

        if file_key and file_value is not None:
            return file_value

        return default

    @classmethod
    def _resolve_model(
        cls,
        task_type: TaskType,
        override: str | None,
        file_config: dict[str, Any],
        template: TaskConfigTemplate,
    ) -> str:
        """Resolve model name with backward compatibility support.

        Args:
            task_type: The task type
            override: Override model name
            file_config: LLM configuration from config.json
            template: Task configuration template

        Returns:
            Resolved model name
        """
        if override is not None:
            return override

        # Check task-specific model config
        task_models = file_config.get('task_models', {})
        if task_type.value in task_models:
            return task_models[task_type.value]

        # Backward compatibility: check legacy environment variables
        if task_type == TaskType.TITLE_GENERATION:
            legacy_env = os.environ.get(cls.ENV_TITLE_MODEL)
            if legacy_env:
                return legacy_env
            legacy_file = file_config.get('title_model')
            if legacy_file:
                return legacy_file

        if task_type == TaskType.FIELD_VALIDATION:
            legacy_env = os.environ.get(cls.ENV_FV_MODEL)
            if legacy_env:
                return legacy_env

        # Use template default
        return template.model

    @classmethod
    def validate_config(cls, config: dict[str, Any]) -> tuple[bool, list[str]]:
        """Validate configuration dictionary.

        Args:
            config: Configuration dictionary to validate

        Returns:
            Tuple of (is_valid, list of error messages)
        """
        errors = []

        if 'llm' in config:
            llm_cfg = config['llm']
            if not isinstance(llm_cfg, dict):
                errors.append("'llm' must be a dictionary")
                return False, errors

            # Validate api_base
            api_base = llm_cfg.get('api_base', '')
            if api_base and not api_base.startswith(('http://', 'https://')):
                errors.append("'api_base' must start with http:// or https://")

            # Validate task_models
            if 'task_models' in llm_cfg:
                task_models = llm_cfg['task_models']
                if not isinstance(task_models, dict):
                    errors.append("'task_models' must be a dictionary")

        return len(errors) == 0, errors


# Backward compatibility functions
def load_api_config() -> tuple[str, str, str]:
    """Legacy function for backward compatibility.

    Returns:
        Tuple of (api_base, api_key, model) for default/general usage
    """
    config = LLMConfig.get_config(TaskType.GENERAL)
    return config.api_base, config.api_key, config.model