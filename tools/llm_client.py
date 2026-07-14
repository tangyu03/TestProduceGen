from __future__ import annotations
"""LLM client wrapper for P3 Agent Engine.

Provides an async interface to ZAI (智谱 GLM) via the z-ai-web-dev-sdk
Node.js SDK, using subprocess calls.

Deprecated: Consider using the unified LLM client from tools.llm for new code.
"""

import json
import os
import re
import subprocess
import urllib.error
from typing import Optional

# Import unified LLM client components (using direct import to avoid circular dependency)
from tools.llm.task_types import TaskType
from prompts.title_prompt import TITLE_SYSTEM_PROMPT, TITLE_BATCH_SUFFIX


class LLMClient:
    """Wrapper for calling ZAI (智谱 GLM) via the z-ai-web-dev-sdk Node.js SDK.

    Since the SDK is JavaScript-based, this client invokes it through a
    Node.js subprocess. The SDK must be installed in the project root.
    """

    # Default model for title generation — use free/cheap model
    TITLE_MODEL = "glm-4-flash"

    def __init__(self) -> None:
        self._sdk_available: bool = self._check_sdk()

    def _check_sdk(self) -> bool:
        """Check if z-ai-web-dev-sdk is available.

        Returns:
            True if the SDK can be required from Node.js, False otherwise.
        """
        try:
            result = subprocess.run(
                ["node", "-e", "require('z-ai-web-dev-sdk')"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return result.returncode == 0
        except Exception:
            return False

    @property
    def sdk_available(self) -> bool:
        """Whether the z-ai-web-dev-sdk is available for use."""
        return self._sdk_available

    async def chat(
        self,
        system_prompt: str,
        user_message: str,
        temperature: float = 0.3,
        max_tokens: int = 8192,
        model: str | None = None,
    ) -> str:
        """Call ZAI chat completions via Node.js subprocess.

        Args:
            system_prompt: System message for the LLM.
            user_message: User message for the LLM.
            temperature: Sampling temperature (0.0–1.0). Defaults to 0.3.
            max_tokens: Maximum tokens to generate. Defaults to 8192.
            model: Model name to use. If None, uses the SDK default.

        Returns:
            The assistant's response text.

        Raises:
            RuntimeError: If the LLM call fails or returns a non-zero exit
                code.
        """
        model_line = f"    model: {json.dumps(model)},\n" if model else ""

        js_code = (
            "const ZAI = require('z-ai-web-dev-sdk').default;\n"
            "\n"
            "async function main() {\n"
            f"  const zai = await ZAI.create();\n"
            "  const completion = await zai.chat.completions.create({\n"
            + model_line +
            "    messages: [\n"
            f"      {{ role: 'system', content: {json.dumps(system_prompt)} }},\n"
            f"      {{ role: 'user', content: {json.dumps(user_message)} }}\n"
            "    ],\n"
            f"    temperature: {temperature},\n"
            f"    max_tokens: {max_tokens}\n"
            "  });\n"
            "  console.log(JSON.stringify(completion.choices[0]?.message?.content || ''));\n"
            "}\n"
            "main().catch(e => { console.error(e.message); process.exit(1); });\n"
        )

        if not self.sdk_available:
            raise RuntimeError("z-ai-web-dev-sdk is not available — cannot call LLM")

        result = subprocess.run(
            ["node", "-e", js_code],
            capture_output=True,
            text=True,
            timeout=120,
        )

        if result.returncode != 0:
            raise RuntimeError(f"LLM call failed: {result.stderr}")

        return result.stdout.strip().strip('"')

    async def chat_json(
        self,
        system_prompt: str,
        user_message: str,
        temperature: float = 0.1,
    ) -> dict | list:
        """Call chat and parse JSON response.

        Handles markdown code fences and trailing commas that LLMs commonly
        produce.

        Args:
            system_prompt: System message for the LLM.
            user_message: User message for the LLM.
            temperature: Sampling temperature. Defaults to 0.1 for more
                deterministic JSON output.

        Returns:
            Parsed JSON object (dict or list).

        Raises:
            RuntimeError: If the LLM call fails.
            json.JSONDecodeError: If the response cannot be parsed as JSON.
        """
        raw = await self.chat(system_prompt, user_message, temperature)

        # Strip markdown code fences
        text = raw.strip()
        if text.startswith("```"):
            # Use find() instead of index() — index() raises ValueError when
            # the LLM returns a single-line code fence like ```json{...}```.
            first_nl = text.find("\n")
            text = text[first_nl + 1:] if first_nl >= 0 else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

        # Fix trailing commas (common LLM artifact)
        text = re.sub(r",\s*}", "}", text)
        text = re.sub(r",\s*]", "]", text)

        return json.loads(text)

# ── Title Generator (pure HTTP, no Node.js dependency) ────────────────


class TitleGenerator:
    """Generate natural-language test-case titles via unified LLM client.

    Uses the new unified LLM client architecture with caching and monitoring.

    Configuration (priority: env var > config.json > default):

        LLM_API_BASE    — API base URL (default: https://open.bigmodel.cn/api/paas/v4)
        LLM_API_KEY     — API key
        LLM_TITLE_MODEL — Model name for titles (default: glm-4-flash, free on 智谱)

    Or create a ``config.json`` at the project root:

        {"llm": {"api_base": "...", "api_key": "...", "task_models": {"title_generation": "..."}}}
    """

    TITLE_SYSTEM_PROMPT = TITLE_SYSTEM_PROMPT  # re-export for backward compat

    def __init__(self, config_path: str | None = None) -> None:
        """Initialize TitleGenerator with unified LLM client.

        Args:
            config_path: Legacy parameter for backward compatibility, now uses unified config.
        """
        # Import unified LLM client directly to avoid circular dependency
        from tools.llm.client import LLMClient as UnifiedLLMClient

        # Use unified LLM client internally
        self._client = UnifiedLLMClient(TaskType.TITLE_GENERATION)

        # For backward compatibility, expose config attributes
        self._api_base = self._client.config.api_base
        self._api_key = self._client.config.api_key
        self._model = self._client.config.model

    @property
    def available(self) -> bool:
        """Whether the API is configured (key is set)."""
        return self._client.available

    def _build_steps_text(self, proc: dict) -> str:
        """Build a compact text representation of a BDD procedure (Given/When/Then)."""
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

        Returns the response text, or None on failure.
        Re-raises HTTP 429 errors so callers can implement adaptive backoff.
        """
        try:
            from tools.llm.http_utils import call_llm_api
            response = call_llm_api(
                api_base=self._api_base,
                api_key=self._api_key,
                model=self._model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                temperature=0.3,
                max_tokens=max_tokens,
                timeout=90,
                max_retries=1,  # Only retry once on 429, fail fast otherwise
            )
            return response
        except urllib.error.HTTPError as e:
            print(f"      [WARN] Title API call failed: HTTP Error {e.code}: {e.reason}")
            if e.code == 429:
                raise  # Let caller handle rate limiting with adaptive backoff
            return None
        except Exception as e:
            print(f"      [WARN] Title API call failed: {e}")
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
            print(f"      [WARN] Title API returned empty response")
            return [""] * len(procedures)

        # Use robust LLM response parser (handles JSONL, JSON arrays, malformed JSON)
        from tools.llm.http_utils import parse_llm_response
        try:
            result = parse_llm_response(raw, prefer_jsonl=True)
        except json.JSONDecodeError:
            # Log raw response for debugging, then fall through to empty
            preview = raw.strip()[:300]
            print(f"      [WARN] Title JSON parse failed, raw preview: {preview}")
            return [""] * len(procedures)

        # Build id→title map from parsed result (handles both list and dict)
        id_to_title: dict[str, str] = {}
        items_list: list[dict] = []
        if isinstance(result, list):
            items_list = result
        elif isinstance(result, dict):
            # Single object — wrap in list
            items_list = [result]

        for item in items_list:
            if isinstance(item, dict):
                tid = item.get("id", "")
                title = item.get("title", "")
                if tid and title:
                    id_to_title[tid] = title

        return [
            id_to_title.get(p.get("temp_id", ""), "")
            for p in procedures
        ]