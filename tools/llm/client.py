from __future__ import annotations
"""Unified LLM Client.

Provides a centralized, reusable LLM client with support for multiple task types,
caching, configuration management, and monitoring.
"""
import asyncio
import json
import re
import time
from typing import Any

from .cache import CacheManager
from .config import LLMConfig, LLMTaskConfig
from .http_utils import call_llm_api, parse_llm_response
from .task_types import TaskType, TaskConfig
from prompts.title_prompt import TITLE_SYSTEM_PROMPT, TITLE_BATCH_SUFFIX


class LLMClient:
    """Unified LLM client for multiple task types.

    Features:
    - Task-specific configuration and caching
    - Automatic retry with exponential backoff
    - Structured logging with task type prefixes
    - Performance monitoring and metrics
    - Graceful degradation on errors

    Example:
        # Create client for title generation
        client = LLMClient(TaskType.TITLE_GENERATION)

        # Simple chat call
        response = await client.chat(
            system_prompt="You are a title generator.",
            user_message="Generate a title."
        )

        # JSON call with caching
        result = await client.chat_json(
            system_prompt="You are a JSON generator.",
            user_message="Generate a JSON object."
        )

        # Batch processing
        results = client.generate_batch(items, batch_size=20)
    """

    def __init__(
        self,
        task_type: TaskType = TaskType.GENERAL,
        config_override: dict[str, Any] | None = None,
    ):
        """Initialize LLM client.

        Args:
            task_type: Task type for this client instance
            config_override: Optional configuration overrides
        """
        self._task_type = task_type
        self._config = LLMConfig.get_config(task_type, config_override)
        self._cache = CacheManager(
            cache_dir=self._config.cache_dir,
            task_type=task_type,
            ttl_days=self._config.cache_ttl_days,
        )
        self._metrics = {
            'total_calls': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'errors': 0,
            'total_duration': 0.0,
        }

    @property
    def task_type(self) -> TaskType:
        """Get the task type for this client."""
        return self._task_type

    @property
    def config(self) -> LLMTaskConfig:
        """Get the configuration for this client."""
        return self._config

    @property
    def available(self) -> bool:
        """Check if the client is available (API key is configured)."""
        return bool(self._config.api_key)

    def _log(self, message: str, level: str = 'info') -> None:
        """Log a message with task type prefix.

        Args:
            message: Message to log
            level: Log level ('info', 'warn', 'error')
        """
        prefix = f"[{self._task_type.value.upper().replace('_', '-')}]"
        if level == 'error':
            print(f"{prefix} ERROR: {message}")
        elif level == 'warn':
            print(f"{prefix} WARN: {message}")
        else:
            print(f"{prefix} {message}")

    def _record_metric(self, metric_name: str, value: float = 1.0) -> None:
        """Record a performance metric.

        Args:
            metric_name: Name of the metric
            value: Value to record (default 1.0 for counters)
        """
        if metric_name == 'duration':
            self._metrics['total_duration'] += value
        elif metric_name == 'call':
            self._metrics['total_calls'] += 1
        elif metric_name == 'cache_hit':
            self._metrics['cache_hits'] += 1
        elif metric_name == 'cache_miss':
            self._metrics['cache_misses'] += 1
        elif metric_name == 'error':
            self._metrics['errors'] += 1

    def get_metrics(self) -> dict[str, Any]:
        """Get performance metrics for this client.

        Returns:
            Dictionary with metrics:
            - total_calls: Total number of LLM calls
            - cache_hits: Number of cache hits
            - cache_misses: Number of cache misses
            - cache_hit_rate: Cache hit rate (0.0-1.0)
            - errors: Number of errors
            - total_duration: Total duration in seconds
            - avg_duration: Average duration per call in seconds
        """
        total_calls = self._metrics['total_calls']
        cache_hits = self._metrics['cache_hits']
        cache_misses = self._metrics['cache_misses']

        cache_hit_rate = 0.0
        if cache_hits + cache_misses > 0:
            cache_hit_rate = cache_hits / (cache_hits + cache_misses)

        avg_duration = 0.0
        if total_calls > 0:
            avg_duration = self._metrics['total_duration'] / total_calls

        return {
            'task_type': self._task_type.value,
            'total_calls': total_calls,
            'cache_hits': cache_hits,
            'cache_misses': cache_misses,
            'cache_hit_rate': cache_hit_rate,
            'errors': self._metrics['errors'],
            'total_duration': self._metrics['total_duration'],
            'avg_duration': avg_duration,
        }

    def reset_metrics(self) -> None:
        """Reset all performance metrics."""
        self._metrics = {
            'total_calls': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'errors': 0,
            'total_duration': 0.0,
        }

    async def chat(
        self,
        system_prompt: str,
        user_message: str,
        use_cache: bool = True,
        **kwargs,
    ) -> str:
        """Call LLM chat API.

        Args:
            system_prompt: System message for the LLM
            user_message: User message for the LLM
            use_cache: Whether to use caching
            **kwargs: Additional parameters to override (temperature, max_tokens, etc.)

        Returns:
            LLM response text

        Raises:
            RuntimeError: If API call fails and no fallback available
        """
        if not self.available:
            raise RuntimeError(f"LLM API key not configured for {self._task_type.value}")

        self._record_metric('call')

        # Build request
        messages = [
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': user_message},
        ]

        # Apply overrides
        temperature = kwargs.get('temperature', self._config.temperature)
        max_tokens = kwargs.get('max_tokens', self._config.max_tokens)

        # Check cache
        if use_cache and self._config.cache_enabled:
            # B-02: 通用 key 纳入 model/max_tokens——不同模型/长度不得串读旧缓存
            cache_key = {'messages': messages, 'temperature': temperature,
                        'model': self._config.model, 'max_tokens': max_tokens}
            cached = self._cache.load(cache_key)
            if cached is not None:
                self._record_metric('cache_hit')
                self._log(f"Loaded from cache")
                return cached
            self._record_metric('cache_miss')

        # Make API call
        start_time = time.time()
        try:
            self._log(f"Calling {self._config.model}, max_tokens={max_tokens}")
            # C-10: call_llm_api 是 urllib 同步阻塞调用——直接内联会把事件循环
            # 卡死 180s，asyncio.gather 并发实际退化为串行且无法取消。丢线程池。
            response = await asyncio.to_thread(
                call_llm_api,
                api_base=self._config.api_base,
                api_key=self._config.api_key,
                model=self._config.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=self._config.timeout,
                max_retries=self._config.retry_max_attempts,
                backoff_factor=self._config.retry_backoff_factor,
                rate_limit_wait=self._config.retry_rate_limit_wait,
            )

            duration = time.time() - start_time
            self._record_metric('duration', duration)
            self._log(f"Success in {duration:.2f}s")

            # Cache the result
            if use_cache and self._config.cache_enabled:
                self._cache.save(cache_key, response)

            return response

        except Exception as e:
            duration = time.time() - start_time
            self._record_metric('duration', duration)
            self._record_metric('error')
            self._log(f"Failed after {duration:.2f}s: {e}", level='error')
            raise

    async def chat_json(
        self,
        system_prompt: str,
        user_message: str,
        use_cache: bool = True,
        prefer_jsonl: bool = True,
        **kwargs,
    ) -> dict | list:
        """Call LLM chat API and parse JSON response.

        Args:
            system_prompt: System message for the LLM
            user_message: User message for the LLM
            use_cache: Whether to use caching
            prefer_jsonl: Whether to prefer JSONL format parsing first
            **kwargs: Additional parameters to override

        Returns:
            Parsed JSON object or list

        Raises:
            RuntimeError: If API call fails
            json.JSONDecodeError: If response cannot be parsed as JSON
        """
        if not self.available:
            raise RuntimeError(f"LLM API key not configured for {self._task_type.value}")

        self._record_metric('call')

        # Build request
        messages = [
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': user_message},
        ]

        # Apply overrides
        temperature = kwargs.get('temperature', self._config.temperature)
        max_tokens = kwargs.get('max_tokens', self._config.max_tokens)

        # Check cache
        if use_cache and self._config.cache_enabled:
            # B-02: 通用 key 纳入 model/max_tokens——不同模型/长度不得串读旧缓存
            cache_key = {'messages': messages, 'temperature': temperature,
                        'model': self._config.model, 'max_tokens': max_tokens}
            cached = self._cache.load(cache_key)
            if cached is not None:
                self._record_metric('cache_hit')
                self._log(f"Loaded from cache")
                return cached
            self._record_metric('cache_miss')

        # Make API call
        start_time = time.time()
        try:
            self._log(f"Calling {self._config.model} (JSON), max_tokens={max_tokens}")
            # C-10: 同步 urllib 调用丢线程池，避免阻塞事件循环。
            response_text = await asyncio.to_thread(
                call_llm_api,
                api_base=self._config.api_base,
                api_key=self._config.api_key,
                model=self._config.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=self._config.timeout,
                max_retries=self._config.retry_max_attempts,
                backoff_factor=self._config.retry_backoff_factor,
                rate_limit_wait=self._config.retry_rate_limit_wait,
            )

            duration = time.time() - start_time
            self._record_metric('duration', duration)
            self._log(f"Response received in {duration:.2f}s, parsing JSON...")

            # Parse JSON response
            parsed = parse_llm_response(response_text, prefer_jsonl=prefer_jsonl)

            # Cache the result
            if use_cache and self._config.cache_enabled:
                self._cache.save(cache_key, parsed)

            self._log(f"JSON parsed successfully")
            return parsed

        except json.JSONDecodeError as e:
            duration = time.time() - start_time
            self._record_metric('duration', duration)
            self._record_metric('error')
            self._log(f"JSON parsing failed after {duration:.2f}s: {e}", level='error')
            raise
        except Exception as e:
            duration = time.time() - start_time
            self._record_metric('duration', duration)
            self._record_metric('error')
            self._log(f"Failed after {duration:.2f}s: {e}", level='error')
            raise

    def generate_batch(
        self,
        items: list[dict],
        batch_processor: callable,
        batch_size: int | None = None,
        use_cache: bool = True,
    ) -> list[Any]:
        """Process items in batches with progress tracking.

        Args:
            items: List of items to process
            batch_processor: Function that processes a single batch, signature:
                           (batch: list[dict], client: LLMClient) -> list[Any]
            batch_size: Batch size (defaults to config default)
            use_cache: Whether to use caching

        Returns:
            List of results, same order as input items
        """
        if not items:
            return []

        if batch_size is None:
            batch_size = self._config.batch_size

        total_batches = (len(items) + batch_size - 1) // batch_size
        self._log(f"Processing {len(items)} items in {total_batches} batch(es)...")

        all_results = []
        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            batch_num = i // batch_size + 1

            try:
                # Process batch
                results = batch_processor(batch, self)
                all_results.extend(results)

                self._log(f"Batch {batch_num}/{total_batches}: {len(results)} results")

            except Exception as e:
                self._log(f"Batch {batch_num}/{total_batches} failed: {e}", level='error')
                # Add placeholder for failed batch
                all_results.extend([None] * len(batch))

            # Small delay between batches to avoid rate limiting
            if total_batches > 1 and batch_num < total_batches:
                time.sleep(2)

        # Report metrics
        metrics = self.get_metrics()
        self._log(f"Done: {metrics['total_calls']} calls, "
                  f"{metrics['cache_hit_rate']:.1%} cache hit rate")

        return all_results


# Backward compatibility: Legacy TitleGenerator interface wrapper
class LegacyTitleGeneratorWrapper:
    """Wrapper for legacy TitleGenerator interface.

    Maintains backward compatibility with existing code that uses the
    old TitleGenerator interface while internally using the new LLMClient.

    Deprecated: Use LLMClient directly for new code.
    """

    TITLE_SYSTEM_PROMPT = TITLE_SYSTEM_PROMPT  # re-export for backward compat

    def __init__(self, config_path: str | None = None):
        """Initialize legacy title generator wrapper.

        Args:
            config_path: Legacy parameter, ignored (uses unified config)
        """
        self._client = LLMClient(TaskType.TITLE_GENERATION)
        self._api_base = self._client.config.api_base
        self._api_key = self._client.config.api_key
        self._model = self._client.config.model

    @property
    def available(self) -> bool:
        """Whether the API is configured (key is set)."""
        return self._client.available

    def _build_steps_text(self, proc: dict) -> str:
        """Build a compact text representation of a BDD procedure (Given/When/Then).

        Args:
            proc: Procedure dict with givens/when/thens/operation_hints

        Returns:
            Text representation
        """
        lines: list[str] = []
        for g in proc.get("givens", []):
            desc = g.get("description", "")
            desc_str = f" ({desc})" if desc else ""
            lines.append(f"  GIVEN: {g.get('target', '')} = {g.get('state', '')}{desc_str}")
        w = proc.get("when", {})
        if w:
            actor = f" by {w.get('actor')}" if w.get("actor") else ""
            lines.append(f"  WHEN: {w.get('target', '')} {w.get('event', '')}{actor}")
        for t in proc.get("thens", []):
            lines.append(f"  THEN: {t.get('target', '')} {t.get('expectation', '')}")
        for h in proc.get("operation_hints", []):
            lines.append(f"  HINT: {h}")
        return "\n".join(lines)

    def _call_api(self, system_prompt: str, user_message: str,
                   max_tokens: int = 256) -> str | None:
        """Make a single synchronous HTTP call to the LLM API.

        Args:
            system_prompt: System prompt
            user_message: User message
            max_tokens: Max tokens to generate

        Returns:
            Response text, or None on failure
        """
        import urllib.error
        try:
            response = call_llm_api(
                api_base=self._api_base,
                api_key=self._api_key,
                model=self._model,
                messages=[
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': user_message},
                ],
                temperature=0.3,
                max_tokens=max_tokens,
                timeout=60,
                max_retries=3,
            )
            return response
        except urllib.error.HTTPError as e:
            self._client._log(f"Title API call failed: HTTP Error {e.code}: {e.reason}", level='warn')
            if e.code == 429:
                raise  # Let caller handle rate limiting with adaptive backoff
            return None
        except Exception as e:
            self._client._log(f"Title API call failed: {e}", level='warn')
            return None

    def generate_batch(self, procedures: list[dict]) -> list[str]:
        """Generate titles for a batch of procedures in one API call.

        Args:
            procedures: List of procedure dicts (each has "temp_id" + "steps").

        Returns:
            List of titles, same order. Empty string for failed items.
        """
        if not procedures or not self.available:
            return [""] * len(procedures)

        # Build the batch prompt
        items: list[str] = []
        for i, proc in enumerate(procedures):
            lines = [f"### 用例{i+1} (ID: {proc.get('temp_id', '?')})"]
            lines.append(self._build_steps_text(proc))
            items.append("\n".join(lines))

        batch_system = self.TITLE_SYSTEM_PROMPT + TITLE_BATCH_SUFFIX

        user_msg = "请为以下测试用例各生成一句话标题，输出 JSON 数组：\n\n" + "\n\n".join(items)

        raw = self._call_api(batch_system, user_msg,
                             max_tokens=len(procedures) * 80 + 200)
        if not raw:
            return [""] * len(procedures)

        # Parse JSON array from response
        text = raw.strip()
        # Strip markdown code fences
        if text.startswith("```"):
            idx = text.find("\n")
            text = text[idx + 1:] if idx >= 0 else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

        # Fix common JSON artifacts
        text = re.sub(r",\s*}", "}", text)
        text = re.sub(r",\s*]", "]", text)

        try:
            result = json.loads(text)
            if isinstance(result, list):
                id_to_title: dict[str, str] = {}
                for item in result:
                    if isinstance(item, dict):
                        tid = item.get("id", "")
                        title = item.get("title", "")
                        if tid and title:
                            id_to_title[tid] = title
                return [
                    id_to_title.get(p.get("temp_id", ""), "")
                    for p in procedures
                ]
        except json.JSONDecodeError:
            pass

        # Fallback: return empty titles
        return [""] * len(procedures)