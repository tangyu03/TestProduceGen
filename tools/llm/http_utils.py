from __future__ import annotations
"""HTTP Utilities for LLM API Calls.

Provides unified HTTP calling logic with retry, backoff, and error handling.
Reuses patterns from existing field_validation.py implementation.
"""
import json
import re
import time
import urllib.error
import urllib.request
from typing import Any

# JSON repair utilities (reused from field_validation.py)


def _repair_json(text: str) -> str:
    """Fix common JSON formatting errors in LLM output.

    Args:
        text: Raw LLM output text

    Returns:
        Repaired JSON string
    """
    # Remove code fences
    if text.startswith('```'):
        nl = text.find('\n')
        text = text[nl + 1:] if nl >= 0 else text[3:]
    if text.endswith('```'):
        text = text[:-3]
    text = text.strip()

    # Extract [...] if there's text before/after
    start = text.find('[')
    end = text.rfind(']')
    if start >= 0 and end > start:
        text = text[start:end + 1]

    # Trailing commas
    text = re.sub(r',\s*}', '}', text)
    text = re.sub(r',\s*]', ']', text)

    # Chinese double quotes inside JSON strings: replace them
    for ch_quote, escaped in [('“', '\\u201c'), ('”', '\\u201d')]:
        text = text.replace(ch_quote, escaped)

    return text


def _parse_jsonl(text: str) -> list[dict]:
    """Parse JSONL (one JSON object per line) format.

    Args:
        text: JSONL text to parse

    Returns:
        List of parsed JSON objects
    """
    entries = []
    for line in text.split('\n'):
        line = line.strip()
        if not line or line.startswith('//') or line.startswith('#'):
            continue
        # Remove trailing comma (common LLM artifact)
        line = line.rstrip(',').rstrip()
        # Fix Chinese quotes
        for cq, esc in [('“', '\\u201c'), ('”', '\\u201d')]:
            line = line.replace(cq, esc)
        try:
            obj = json.loads(line)
            if isinstance(obj, dict):
                entries.append(obj)
        except json.JSONDecodeError:
            continue
    return entries


def _extract_json_objects(text: str) -> list[dict]:
    """Fallback: extract individual {...} objects from malformed JSON array text.

    Args:
        text: Text containing JSON objects

    Returns:
        List of extracted JSON objects
    """
    objects = []
    # Find all {...} blocks, being careful about nested braces
    depth = 0
    start = -1
    for i, ch in enumerate(text):
        if ch == '{':
            if depth == 0:
                start = i
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0 and start >= 0:
                candidate = text[start:i + 1]
                # Clean up
                candidate = re.sub(r',\s*}', '}', candidate)
                candidate = re.sub(r',\s*]', ']', candidate)
                for cq, esc in [('“', '\\u201c'), ('”', '\\u201d')]:
                    candidate = candidate.replace(cq, esc)
                try:
                    obj = json.loads(candidate)
                    if isinstance(obj, dict):
                        objects.append(obj)
                except json.JSONDecodeError:
                    pass
                start = -1
    return objects


def build_chat_request(
    model: str,
    messages: list[dict],
    temperature: float = 0.3,
    max_tokens: int | None = None,
) -> dict[str, Any]:
    """Build chat completion request body.

    Args:
        model: Model name to use
        messages: List of message dicts with 'role' and 'content'
        temperature: Sampling temperature
        max_tokens: Maximum tokens to generate

    Returns:
        Request body dictionary
    """
    body = {
        'model': model,
        'messages': messages,
        'temperature': temperature,
    }
    if max_tokens is not None:
        body['max_tokens'] = max_tokens
    return body


def extract_response_content(response: dict) -> str:
    """Extract content from chat completion API response.

    Args:
        response: API response dictionary

    Returns:
        Response content string, empty string if extraction fails
    """
    # Check for API-level error first (some APIs return 200 with error body)
    if 'error' in response:
        err = response['error']
        if isinstance(err, dict):
            print(f"      [HTTP] API returned error: {err.get('code', '')} — {err.get('message', str(err))}")
        return ''
    try:
        raw = (response.get('choices') or [{}])[0].get('message', {}).get('content', '')
        return raw
    except (KeyError, TypeError, IndexError):
        return ''


def call_http_api_with_retry(
    url: str,
    body: dict,
    headers: dict,
    timeout: int = 60,
    max_retries: int = 1,
    backoff_factor: float = 2.0,
    rate_limit_wait: int = 30,
) -> dict[str, Any]:
    """Call HTTP API with minimal retry logic.

    Only retries on 429 (rate limit) errors — all other errors fail fast.
    Creates a fresh request object on each attempt to avoid connection reuse issues.

    Args:
        url: API endpoint URL
        body: Request body dictionary
        headers: Request headers dictionary
        timeout: Request timeout in seconds
        max_retries: Maximum retry attempts (only for 429 errors)
        backoff_factor: Unused — kept for API compatibility
        rate_limit_wait: Wait time in seconds for rate limit errors

    Returns:
        API response dictionary

    Raises:
        urllib.error.HTTPError: If all retries fail with HTTP error
        RuntimeError: If all retries fail
    """
    last_error = ''
    for attempt in range(max_retries + 1):
        # Fresh request each attempt (urllib may not resend data on retry)
        encoded_body = json.dumps(body).encode('utf-8')
        req = urllib.request.Request(url, data=encoded_body, headers=headers)

        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode('utf-8'))
            return data

        except urllib.error.HTTPError as e:
            last_error = str(e)
            # Only retry on 429; all other HTTP errors fail immediately
            if e.code == 429 and attempt < max_retries:
                print(f"      [HTTP] Rate limited (429), waiting {rate_limit_wait}s before retry...")
                time.sleep(rate_limit_wait)
                continue
            raise

        except (urllib.error.URLError, OSError, Exception) as e:
            last_error = str(e)
            if attempt < max_retries:
                time.sleep(2)
                continue
            raise RuntimeError(f"HTTP API call failed after {max_retries + 1} attempts: {last_error}")

    raise RuntimeError(f"HTTP API call failed: {last_error}")


def call_llm_api(
    api_base: str,
    api_key: str,
    model: str,
    messages: list[dict],
    temperature: float = 0.3,
    max_tokens: int | None = None,
    timeout: int = 60,
    max_retries: int = 3,
) -> str:
    """Call LLM chat completion API and extract content.

    Args:
        api_base: Base URL for the LLM API
        api_key: API key for authentication
        model: Model name to use
        messages: List of message dicts
        temperature: Sampling temperature
        max_tokens: Maximum tokens to generate
        timeout: Request timeout in seconds
        max_retries: Maximum retry attempts

    Returns:
        LLM response content string

    Raises:
        RuntimeError: If API call fails
    """
    url = f'{api_base}/chat/completions'
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {api_key}',
    }
    body = build_chat_request(model, messages, temperature, max_tokens)

    response = call_http_api_with_retry(url, body, headers, timeout, max_retries)
    content = extract_response_content(response)
    if not content:
        # Log response structure for debugging (exclude large fields)
        safe = {k: ('<redacted>' if k in ('choices',) else v) for k, v in response.items()}
        print(f"      [HTTP] Empty content — response keys: {list(response.keys())}, "
              f"model={model}, error={response.get('error', 'none')}")
    return content


def parse_llm_response(text: str, prefer_jsonl: bool = True) -> dict | list:
    """Parse LLM response handling various output formats.

    Supports:
    - JSONL (line-by-line JSON objects)
    - JSON arrays
    - Individual JSON objects
    - Malformed JSON with common artifacts

    Args:
        text: Raw LLM response text
        prefer_jsonl: Whether to prefer JSONL format parsing first

    Returns:
        Parsed JSON object or list

    Raises:
        json.JSONDecodeError: If parsing fails completely
    """
    # First, repair the text
    text = _repair_json(text)

    if prefer_jsonl:
        # Try JSONL format first (common for batched outputs)
        entries = _parse_jsonl(text)
        if entries:
            return entries

    # Try JSON array format
    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return parsed
        elif isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    # Fallback: extract individual objects
    objects = _extract_json_objects(text)
    if objects:
        return objects

    # All parsing attempts failed
    raise json.JSONDecodeError(f"Could not parse LLM response as JSON: {text[:200]}...", text, 0)