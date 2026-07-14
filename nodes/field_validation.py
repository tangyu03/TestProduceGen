"""Field-level validation — LLM-driven, zero hardcoded extraction rules.

Sends attribute descriptions to the LLM and gets back concrete V-step
dicts. Results are cached per coverage model to avoid repeated calls.

Contains NO regex patterns, NO keyword lists, NO constraint templates.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from collections import defaultdict

# ---- public API (same signatures as before) ----

def parse_entity_constraints(entity_details: list | dict) -> dict[str, list[dict]]:
    """Convert entity_details.attributes into entity_id → V-step dicts via LLM.

    Cached: same entity_details → same result, no repeated API calls.
    """
    # Normalize
    if isinstance(entity_details, dict):
        details_list = [v for v in entity_details.values() if isinstance(v, dict)]
    elif isinstance(entity_details, list):
        details_list = entity_details
    else:
        return {}

    # Collect all (entity_id, attr_name, desc) triples
    items: list[dict] = []
    for ed in details_list:
        eid = ed.get('id', '')
        if not eid:
            continue
        for attr in ed.get('attributes', []):
            desc = (attr.get('desc') or '').strip()
            if not desc:
                continue
            items.append({
                'entity_id': eid,
                'attr_name': attr.get('name', ''),
                'desc': desc,
            })

    if not items:
        return {}

    # Try cache first
    cached = _load_cache(items)
    if cached is not None:
        return cached

    # Call LLM
    result = _call_llm(items)
    _save_cache(items, result)
    return result


def should_enrich(action: str) -> bool:
    """Check if action text suggests a create/edit operation (cheap heuristic)."""
    return any(tok in action for tok in ('新增', '添加', '创建', '建立', '修改', '编辑'))


def enrich_procedure_steps(
    entity_id: str,
    action: str,
    steps: list[dict],
    constraint_steps: dict[str, list[dict]],
) -> list[dict]:
    """Append pre-built field-validation V-steps to procedure."""
    if not should_enrich(action):
        return steps
    extra = constraint_steps.get(entity_id, [])
    steps.extend(extra)
    return steps


# ======================================================================
# LLM call
# ======================================================================

_SYSTEM_PROMPT = """你是一个字段校验测试用例生成器。根据属性描述，为每个有校验规则的属性生成 BDD Then 子句（可观察的校验失败结果）。

## 核心原则：每个属性至少生成 2 条 Then 子句，覆盖不同违规维度

对每个属性，输出一行或多行 JSON（JSONL 格式）：
{"target":"实体ID.属性名","expectation":"校验失败，提示'具体限制描述'","kind":"behavior"}

## 字段说明
- target：观察对象，格式为"实体ID.属性名"（如"E-USER.手机号"）
- expectation：可观察的校验失败结果，必须准确反映约束条件
- kind：固定为"behavior"（输入违规值→观察校验失败）

## 生成规则（按校验类型）

### 字符长度约束
- "最长N字符" / "长度范围N" → 至少2条：
  1. 输入{N+1}个字符（超长）
  2. 如果标注了"必填" → 留空不填

### 手机号约束
- "11位数字手机号" / "第一位为1，第二位为3-9" → 至少3条：
  1. 输入含字母的手机号（如 1234567890a）
  2. 输入位数不足（如 1234567890，10位）
  3. 输入第二位不符合规则的（如 10123456789，第二位是0）

### 邮箱格式约束
- "邮箱" / "必须包含@和." / "不能包含中文、特殊符号" → 至少4条：
  1. 不含@符号（如 notanemail）
  2. 不含.符号（如 test@testcom）
  3. 含中文字符（如 测试@test.com）
  4. 含特殊字符如中划线（如 test-user@test.com）

### 必填约束
- "必填" → 至少2条：
  1. 完全留空不填
  2. 输入纯空格字符串

### 唯一性约束
- "唯一" → 至少1条：
  1. 输入已存在的重复值（如已存在123@test.com，则再次输入123@test.com）

### 数值范围约束
- "数值M-N" / "整数M-N" → 至少2条：
  1. 输入{N+1}超出最大值
  2. 输入{M-1}低于最小值（如果M>0）
- 小数精度约束 → 输入超出精度位数的值

### 文件上传约束
- "doc/pdf等格式" → 至少2条：
  1. 上传不允许的格式（如 .txt, .xls）
  2. 上传超过大小限制的文件
- "<=N MB" → 上传{N+1}MB文件

### 枚举约束
- 有明确枚举值的 → 至少1条：输入不在枚举列表中的值

## expectation 格式要求
expectation 必须准确反映需求描述的约束条件，不能模糊：
- 需求"最长20字符" → expectation: "校验失败，提示'最长20字符'"
- 需求"不能包含中文、特殊符号" → expectation: "校验失败，提示'不能包含中文和特殊符号'"
- 需求"必须包含@和." → expectation: "校验失败，提示'邮箱必须包含@和.'"
- 不要用模糊的"格式错误"代替具体的约束描述

## 类型跳过（仅以下类型不输出）
- 纯布尔型（true/false）
- 自动生成/自动编号（系统赋值，用户不可输入）
- 纯展示/只读字段（没有任何校验规则描述）

## 输出格式
每行一个 JSON 对象。只输出 JSONL，不要数组、不要额外文字、不要代码块。"""


def _build_user_prompt(items: list[dict]) -> str:
    """Build the user prompt listing all attributes with their descriptions.

    Each item is shown with its entity_id and attr_name so the LLM can
    construct the ``target`` field as "entity_id.attr_name" in the output
    ThenClause dict.
    """
    lines = [
        "请为以下属性生成 BDD Then 子句（字段校验失败的可观察结果）。",
        "每条输出 JSON 的 target 字段必须是 '实体ID.属性名' 格式。",
        "",
    ]
    for i, item in enumerate(items):
        lines.append(
            f"### {i+1}. 实体ID={item['entity_id']} / 属性名={item['attr_name']}\n"
            f"描述：{item['desc']}\n"
        )
    return '\n'.join(lines)


BATCH_SIZE = 30  # was 10; larger batches reduce API round-trips (102 attrs → 4 batches instead of 11)


def _repair_json(text: str) -> str:
    """Fix common JSON formatting errors in LLM output."""
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
    """Parse JSONL (one JSON object per line) format."""
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
            # BDD: accept new ThenClause format (has 'target') OR legacy format (has 'entity_id')
            if isinstance(obj, dict) and ('entity_id' in obj or 'target' in obj):
                entries.append(obj)
        except json.JSONDecodeError:
            continue
    return entries


def _extract_json_objects(text: str) -> list[dict]:
    """Fallback: extract individual {...} objects from malformed JSON array text.

    Used when json.loads() fails on the full array.
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


def _load_api_config() -> tuple[str, str, str]:
    """Load API credentials, returning (api_base, api_key, model)."""
    api_base = os.environ.get('LLM_API_BASE', 'https://open.bigmodel.cn/api/paas/v4').rstrip('/')
    api_key = os.environ.get('LLM_API_KEY', '')
    model = os.environ.get('LLM_FV_MODEL', 'glm-4-flash')

    if not api_key:
        cfg_path = os.path.join(os.path.dirname(__file__), '..', 'config.json')
        try:
            with open(cfg_path, 'r', encoding='utf-8') as f:
                cfg = json.load(f)
            llm_cfg = cfg.get('llm', {})
            api_base = llm_cfg.get('api_base', api_base).rstrip('/')
            api_key = llm_cfg.get('api_key', api_key)
            model = llm_cfg.get('fv_model', model)
        except (FileNotFoundError, json.JSONDecodeError):
            pass

    return api_base, api_key, model


def _call_llm_batch(api_base: str, api_key: str, model: str,
                    batch: list[dict], batch_num: int, total_batches: int) -> list[dict]:
    """Send one batch of attributes to LLM, return parsed entries list."""
    import urllib.request
    import urllib.error

    url = f'{api_base}/chat/completions'
    body = json.dumps({
        'model': model,
        'messages': [
            {'role': 'system', 'content': _SYSTEM_PROMPT},
            {'role': 'user', 'content': _build_user_prompt(batch)},
        ],
        'temperature': 0.1,
        'max_tokens': len(batch) * 150 + 300,
    }).encode('utf-8')

    req = urllib.request.Request(url, data=body, headers={
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {api_key}',
    })

    import time as _time
    last_error = ''
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=180) as resp:
                data = json.loads(resp.read().decode('utf-8'))
            raw = (data.get('choices') or [{}])[0].get('message', {}).get('content', '')
            break
        except urllib.error.HTTPError as e:
            last_error = str(e)
            if e.code == 429 and attempt < 2:
                wait = (attempt + 1) * 10
                print(f'      [FIELD-VAL] Rate limited, waiting {wait}s...')
                _time.sleep(wait)
                continue
            print(f'      [FIELD-VAL] Batch {batch_num}/{total_batches} failed: HTTP {e.code}')
            return []
        except Exception as e:
            last_error = str(e)
            if attempt < 2:
                _time.sleep(3)
                continue
            print(f'      [FIELD-VAL] Batch {batch_num}/{total_batches} failed: {last_error}')
            return []
    else:
        print(f'      [FIELD-VAL] Batch {batch_num}/{total_batches} failed after 3 retries: {last_error}')
        return []

    text = _repair_json(raw)

    # Try JSONL (line-by-line JSON) first — each line is a standalone object
    entries = _parse_jsonl(text)
    if entries:
        print(f'      [FIELD-VAL] Batch {batch_num}/{total_batches}: {len(entries)} JSONL entries from {len(batch)} attributes')
        return entries

    # Fallback: try JSON array
    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            print(f'      [FIELD-VAL] Batch {batch_num}/{total_batches}: {len(parsed)} array entries from {len(batch)} attributes')
            return parsed
    except json.JSONDecodeError:
        pass

    # Last resort: extract {...} objects
    parsed = _extract_json_objects(text)
    if parsed:
        print(f'      [FIELD-VAL] Batch {batch_num}/{total_batches}: salvaged {len(parsed)} objects')
        return parsed

    print(f'      [FIELD-VAL] Batch {batch_num}/{total_batches}: could not parse')
    return []


def _call_llm(items: list[dict]) -> dict[str, list[dict]]:
    """Send attribute descriptions to LLM, merge results."""
    api_base, api_key, model = _load_api_config()

    if not api_key:
        print('      [FIELD-VAL] LLM_API_KEY not set — skipping field validation')
        return {}

    total_batches = (len(items) + BATCH_SIZE - 1) // BATCH_SIZE
    print(f'      [FIELD-VAL] Calling {model}, {len(items)} attributes in {total_batches} batch(es)...')

    all_entries: list[dict] = []
    for i in range(0, len(items), BATCH_SIZE):
        batch = items[i:i + BATCH_SIZE]
        batch_num = i // BATCH_SIZE + 1
        entries = _call_llm_batch(api_base, api_key, model, batch, batch_num, total_batches)
        all_entries.extend(entries)
        # Small delay between batches to avoid rate limiting
        if total_batches > 1 and batch_num < total_batches:
            import time
            time.sleep(2)

    # Build entity_id → ThenClause list map.
    # BDD: LLM now outputs ThenClause dicts directly (target/expectation/kind).
    # Backward compat: also accept legacy {entity_id, attr_name, input, expected}
    # and legacy nested {entity_id, steps:[{input, expected}]} formats.
    result: dict[str, list[dict]] = defaultdict(list)
    for entry in all_entries:
        # ── Format A (new BDD): {target, expectation, kind, ...} ──
        if entry.get('target') and entry.get('expectation'):
            target = entry.get('target', '')
            # Infer entity_id from target (e.g. "E-USER.手机号" → "E-USER")
            eid = target.split('.', 1)[0] if '.' in target else target
            result[eid].append({
                'target': target,
                'expectation': entry.get('expectation', ''),
                'kind': entry.get('kind', 'behavior'),
                'br_refs': entry.get('br_refs', []),
                'cross_refs': entry.get('cross_refs', []),
            })
            continue
        # ── Format B (legacy flat): {entity_id, attr_name, input, expected} ──
        eid = entry.get('entity_id', '')
        attr = entry.get('attr_name', '')
        location = f"{eid}.{attr}" if eid and attr else eid
        inp = entry.get('input', '')
        exp = entry.get('expected', '')
        if eid and exp:
            result[eid].append({
                'target': location,
                'expectation': exp,
                'kind': 'behavior',
                'br_refs': [],
                'cross_refs': [],
            })
        # ── Format C (legacy nested): {entity_id, steps: [{input, expected}]} ──
        steps = entry.get('steps', [])
        if isinstance(steps, list):
            for s in steps:
                si = s.get('input', '')
                se = s.get('expected', '')
                if eid and se:
                    result[eid].append({
                        'target': location,
                        'expectation': se,
                        'kind': 'behavior',
                        'br_refs': [],
                        'cross_refs': [],
                    })

    n_steps = sum(len(v) for v in result.values())
    print(f'      [FIELD-VAL] Total: {n_steps} field-validation V-steps for {len(result)} entities')
    return dict(result)


# ======================================================================
# Cache (avoid repeated LLM calls for the same coverage model)
# ======================================================================

def _cache_path(items: list[dict]) -> str:
    """Derive a stable cache path from the items content."""
    stable = json.dumps(sorted(items, key=lambda x: x['entity_id'] + x['attr_name']),
                        ensure_ascii=True, sort_keys=True)
    h = hashlib.sha256(stable.encode()).hexdigest()[:16]
    return os.path.join(os.path.dirname(__file__), '..', 'cache', f'fv_{h}.json')


def _load_cache(items: list[dict]) -> dict[str, list[dict]] | None:
    """Try to load cached result; return None if cache miss."""
    cpath = _cache_path(items)
    if not os.path.exists(cpath):
        return None
    try:
        with open(cpath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        # Convert back from serialized format
        result: dict[str, list[dict]] = {}
        for eid, steps in data.items():
            result[eid] = steps
        print(f'      [FIELD-VAL] Loaded from cache ({len(result)} entities)')
        return result
    except (json.JSONDecodeError, TypeError, AttributeError):
        # BUGFIX #25: KeyError was unreachable (no [] access on dicts above).
        # Use TypeError/AttributeError to catch malformed cache files where
        # `data` is not a dict or `.items()` fails.
        return None


def _save_cache(items: list[dict], result: dict[str, list[dict]]) -> None:
    """Save result to cache file."""
    cpath = _cache_path(items)
    os.makedirs(os.path.dirname(cpath), exist_ok=True)
    try:
        with open(cpath, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
    except OSError:
        pass  # cache write failure is non-fatal
