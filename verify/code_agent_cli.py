#!/usr/bin/env python3
"""code_agent_cli.py — 代码修复 Agent 的 CLI 包装器（构建者角色）。

契约：
  stdin  → loop_manager 的 task JSON（见 build_task 的 output_contract）
  stdout → declaration JSON（相同 schema）
  退出码 → 0（即使 LLM 失败也输出低置信度声明，让管理者决定重试）

工作流：
  1. 从 stdin/--task-file 读取 task
  2. 读取 allowed_files（可修改）+ reference_files（只读参考）作为 LLM 上下文
  3. 调用 LLM 生成结构化修改（SEARCH/REPLACE 对）

task JSON 结构:
  {
    "failed_checks": [...],      // 失败的检查项
    "routing_hints": [...],      // 修复方向提示
    "allowed_files": [...],      // 允许修改的文件（可编辑）
    "reference_dirs": [...],     // 只读参考目录（agent 自动加载目录下所有文件）
    "prior_failed_attempts": [...] // 历史失败尝试
  }

CLI 选项:
  --task-file PATH    从文件读取 task JSON（默认从 stdin 读取）

LLM 配置（优先级：环境变量 > verify/llm_config.json > config.json > 内置默认值）：

  verify/llm_config.json（verify 目录专用，可与主流水线使用不同供应商）：
    {"api_base": "https://api.anthropic.com/v1",
     "api_key": "sk-ant-...",
     "model": "claude-sonnet-5",
     "temperature": 0.2, "max_tokens": 4096, "timeout": 120}

  若 verify/llm_config.json 不存在，则回退到项目根 config.json：
    {"llm": {"api_base": "...", "api_key": "...",
             "task_models": {"code_agent": "glm-4-flash"}}}

  环境变量（最高优先级，覆盖以上所有）：
    LLM_API_BASE          — API 基地址
    LLM_API_KEY           — API 密钥
    LLM_CODE_AGENT_MODEL  — 模型名

  典型场景：
    - 主流水线用智谱 GLM（config.json）→ 生成标题、校验等
    - verify 代码 Agent 用 Claude（verify/llm_config.json）→ 修复代码
    两套配置完全独立，互不干扰。
"""
from __future__ import annotations
import json
import os
import re
import sys
from pathlib import Path

# 确保项目根目录在 sys.path 中，使 tools 包可导入
# （loop_manager 以 subprocess 方式调用时，CWD 是 worktree 根目录）
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


SYSTEM_PROMPT = """你是一个代码修复 Agent。你的任务是根据测试门禁的失败报告，精准修复工程代码中的结构性缺陷。

核心原则（从第一性原理出发）：
1. 追溯根因而非修补症状 — 理解缺陷为什么发生，从源头修正产生错误数据的逻辑。
2. 禁止打补丁 — 不要在 pipeline 下游添加修正循环、事后校验或数据清洗步骤来掩盖上游错误。
3. 禁止硬编码 — 不得使用魔术数字、硬编码迭代上限（如 for _ in range(5)）、硬编码状态名或实体名。
4. 数据生成处修复 — 如果 s0/s1 产生了错误的拓扑数据，修 s0/s1，不要在 s2/s3/s4 做"纠偏"。

严格约束：
5. 你只能修改 task.allowed_files 列出的文件，不得修改其他任何文件。
6. 修改必须最小化、精准，只修复报告的缺陷，不要重构无关代码。
7. 你的输出必须是严格的 JSON，不得包含 markdown 代码块标记、解释性文字或任何前后缀。

输出 JSON 格式：
{
  "file_edits": [
    {
      "path": "允许修改的文件相对路径",
      "search": "要替换的原文片段，必须精确匹配包括缩进；留空表示整文件替换",
      "replace": "替换后的新内容"
    }
  ],
  "intent": "一句话说明修改意图",
  "confidence": "高 或 中 或 低",
  "known_uncertainties": ["你不确定的点"],
  "assumptions": ["你做出的假设"]
}

关键规则：
- search 片段在文件中必须唯一且精确匹配。如果需要修改的代码出现多次，在 search 里包含足够的上下文行使其唯一。
- 如果 search 留空，则 replace 将完全覆盖该文件内容（仅用于小文件）。
- 如果不确定怎么改，confidence 设为"低"，file_edits 留空，在 known_uncertainties 里说明原因。不要猜测性地修改。
- 如果根因在 allowed_files 之外（如 build_obligations.py），在 known_uncertainties 中明确指出，不要试图在下游打补丁绕过。"""


def _find_verify_llm_config() -> Path | None:
    """查找 verify 目录专用的 LLM 配置文件。

    从当前文件所在目录开始，向上查找 verify/llm_config.json。
    在 worktree 和直接运行两种场景下都能正确定位。

    Returns:
        verify/llm_config.json 的路径，找不到则返回 None
    """
    # 优先从本文件所在目录查找（verify/code_agent_cli.py → verify/llm_config.json）
    own_dir = Path(__file__).resolve().parent
    local = own_dir / "llm_config.json"
    if local.exists():
        return local
    # 备选：从 CWD 向上查找
    cwd = Path.cwd().resolve()
    for p in [cwd] + list(cwd.parents):
        candidate = p / "verify" / "llm_config.json"
        if candidate.exists():
            return candidate
    return None


def load_code_agent_config() -> dict:
    """加载代码 Agent 的 LLM 配置。

    优先级（从高到低）：
      1. 环境变量 LLM_API_BASE / LLM_API_KEY / LLM_CODE_AGENT_MODEL
      2. verify/llm_config.json  — verify 目录专用（可与主流水线不同供应商）
      3. 项目根 config.json       — 主流水线配置（task_models.code_agent）
      4. 内置 TaskType.CODE_AGENT 模板默认值

    verify/llm_config.json 格式:
      {"api_base": "https://api.anthropic.com/v1",
       "api_key": "sk-ant-...",
       "model": "claude-sonnet-5",
       "temperature": 0.2, "max_tokens": 4096, "timeout": 120}

    Returns:
        dict with keys: api_base, api_key, model, temperature, max_tokens, timeout
    """
    from tools.llm.config import LLMConfig
    from tools.llm.task_types import TaskType

    # 基础配置：从统一配置系统加载（config.json → TaskType.CODE_AGENT 模板）
    task_cfg = LLMConfig.get_config(TaskType.CODE_AGENT)

    # verify/llm_config.json 覆盖（verify 目录专用，可指定完全不同的供应商）
    verify_cfg_path = _find_verify_llm_config()
    verify_cfg = {}
    if verify_cfg_path is not None:
        try:
            with open(verify_cfg_path, encoding="utf-8") as f:
                verify_cfg = json.load(f)
        except (json.JSONDecodeError, OSError):
            pass

    # 逐字段合并：verify_cfg > task_cfg（统一配置），环境变量最高优
    api_base = (
        os.environ.get("LLM_API_BASE")
        or verify_cfg.get("api_base")
        or task_cfg.api_base
    ).rstrip("/")
    api_key = (
        os.environ.get("LLM_API_KEY")
        or verify_cfg.get("api_key")
        or task_cfg.api_key
    )
    model = (
        os.environ.get("LLM_CODE_AGENT_MODEL")
        or verify_cfg.get("model")
        or task_cfg.model
    )

    if not api_key:
        raise RuntimeError(
            "未配置 LLM API key。请设置环境变量 LLM_API_KEY，或在 "
            "verify/llm_config.json / config.json 的 llm.api_key 中配置。"
        )

    return {
        "api_base": api_base,
        "api_key": api_key,
        "model": model,
        "temperature": verify_cfg.get("temperature", task_cfg.temperature),
        "max_tokens": verify_cfg.get("max_tokens", task_cfg.max_tokens or 4096),
        "timeout": verify_cfg.get("timeout", task_cfg.timeout),
    }


def call_llm(cfg: dict, system: str, user: str) -> tuple[str, int]:
    """调用 LLM API（使用统一的 http_utils，享受重试/退避机制）。

    Args:
        cfg: load_code_agent_config() 返回的配置字典
        system: system prompt
        user: user message

    Returns:
        (响应文本, total_tokens)
    """
    from tools.llm.http_utils import call_llm_api

    response = call_llm_api(
        api_base=cfg["api_base"],
        api_key=cfg["api_key"],
        model=cfg["model"],
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=cfg["temperature"],
        max_tokens=cfg["max_tokens"],
        timeout=cfg["timeout"],
        max_retries=2,
    )
    # call_llm_api 返回纯文本；token 计数不可用则返回 0
    return response, 0


def discover_project_files(root: Path, exclude_prefixes: list | None = None) -> list:
    """发现项目中所有可编辑的源文件（排除 verify/ 等基础设施目录）。

    当 task.allowed_files 包含 "*" 时使用此函数自动扩展为完整文件列表。
    递归扫描项目根目录，收集所有源码文件。

    Args:
        root: 项目根目录
        exclude_prefixes: 要排除的目录前缀，默认排除 verify/, __pycache__/, .git/

    Returns:
        相对文件路径列表
    """
    if exclude_prefixes is None:
        exclude_prefixes = ["verify/", "__pycache__", ".git", "cache/", ".claude/"]
    source_exts = {".py", ".md", ".json", ".txt", ".yaml", ".yml", ".cfg", ".ini"}
    files = []
    for f in sorted(root.rglob("*")):
        if not f.is_file():
            continue
        rel = str(f.relative_to(root)).replace("\\", "/")
        if any(rel.startswith(p) or p in rel.split("/") for p in exclude_prefixes):
            continue
        if f.suffix in source_exts or f.suffix == "":
            files.append(rel)
    return files


def read_allowed_files(allowed: list, root: Path) -> dict:
    """读取白名单文件的当前内容，用于注入 LLM 上下文。

    源码文件不截断（根因可能在文件深处），仅受限于模型上下文窗口。
    """
    contents = {}
    for rel in allowed:
        p = root / rel
        if not p.exists():
            contents[rel] = f"[FILE NOT FOUND: {rel}]"
            continue
        text = p.read_text(encoding="utf-8")
        contents[rel] = text
    return contents


def read_reference_dirs(ref_dirs: list, root: Path) -> dict:
    """加载参考目录下的所有可读文件（只读上下文，不可修改）。

    遍历 reference_dirs 中每个目录，递归读取所有文本文件。
    跳过二进制、隐藏文件和 __pycache__。

    Args:
        ref_dirs: 目录路径列表（相对于 root，由 routing table 的 ref_dirs 决定）
        root: 项目根目录

    Returns:
        {rel_path: content} dict
    """
    contents = {}
    for ref_dir in ref_dirs:
        d = root / ref_dir
        if not d.is_dir():
            continue
        for f in sorted(d.rglob("*")):
            if not f.is_file():
                continue
            if any(p.startswith(".") for p in f.parts):
                continue
            if "__pycache__" in f.parts:
                continue
            if f.suffix in {".pyc", ".pyo", ".pyd", ".png", ".jpg", ".gif", ".ico", ".bin"}:
                continue
            rel = str(f.relative_to(root))
            try:
                text = f.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            contents[rel] = text
    return contents


def build_user_message(task: dict, file_contents: dict,
                       ref_contents: dict | None = None) -> str:
    """组装 user prompt：失败检查 + 提示 + 历史 + 参考文档 + 文件内容。

    Args:
        task: 任务字典
        file_contents: 允许修改的文件内容
        ref_contents: 只读参考文件内容（如 context/ 目录），不可修改
    """
    parts = []
    primary_files = set(task.get("primary_files", []))

    # 失败检查项
    parts.append("## 失败的检查项\n")
    for c in task.get("failed_checks", []):
        parts.append(f"### {c['check_id']} ({c.get('severity', 'blocker')})")
        parts.append(f"失败数: {c.get('fail_count', 0)}")
        for ev in c.get("evidence", [])[:8]:
            parts.append(f"  - {json.dumps(ev, ensure_ascii=False)}")
        parts.append("")

    # 路由提示
    hints = task.get("routing_hints", [])
    if hints:
        parts.append("## 修复方向提示\n")
        for h in hints:
            parts.append(f"- {h}")
        parts.append("")

    # 历史尝试
    prior = task.get("prior_failed_attempts", [])
    if prior:
        parts.append("## 历史失败尝试（避免重复同样的修法）\n")
        for a in prior:
            parts.append(f"- 意图: {a.get('diff_summary', '?')}")
            parts.append(f"  结果: {a.get('verdict', '?')}")
        parts.append("")

    # 只读参考文档
    if ref_contents:
        parts.append("## 参考文档（只读上下文，不可修改这些文件）\n")
        for rel, content in ref_contents.items():
            parts.append(f"### [参考] {rel}")
            parts.append(f"```\n{content}\n```\n")

    # 重点怀疑文件（先列，详细）
    if primary_files:
        parts.append("## 重点怀疑文件（优先检查根因）\n")
        for rel in sorted(primary_files):
            if rel in file_contents:
                parts.append(f"### [重点] {rel}")
                parts.append(f"```\n{file_contents[rel]}\n```\n")

    # 其他可修改文件
    other_files = {k: v for k, v in file_contents.items() if k not in primary_files}
    if other_files:
        parts.append("## 其他可修改文件\n")
        for rel, content in other_files.items():
            parts.append(f"### {rel}")
            parts.append(f"```\n{content}\n```\n")

    parts.append("请根据以上信息输出修复 JSON。记住：只输出 JSON，不要任何其他文字。")
    return "\n".join(parts)


def parse_llm_json(text: str) -> dict | None:
    """解析 LLM 输出为 JSON，容错：尝试提取 ```json 块、裸 JSON。"""
    text = text.strip()
    # 直接解析
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # 提取 ```json ... ``` 块
    m = re.search(r"```(?:json)?\s*\n?(.*?)```", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1).strip())
        except json.JSONDecodeError:
            pass
    # 提取第一个 { 到最后一个 } 的子串
    start, end = text.find("{"), text.rfind("}")
    if 0 <= start < end:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            pass
    return None


def apply_edits(file_edits: list, allowed: set, root: Path) -> tuple[list, list]:
    """应用 SEARCH/REPLACE 编辑，返回 (已应用列表, 跳过列表)。"""
    applied, skipped = [], []
    for edit in file_edits or []:
        path = edit.get("path", "")
        search = edit.get("search", "") or ""
        replace = edit.get("replace", "") or ""

        # 白名单校验（安全防线）
        if path not in allowed:
            skipped.append({"path": path, "reason": "path not in allowed_files"})
            continue

        p = root / path
        if not p.exists():
            skipped.append({"path": path, "reason": "file not found"})
            continue

        content = p.read_text(encoding="utf-8")

        if search == "":
            # 整文件替换
            p.write_text(replace, encoding="utf-8")
            applied.append({"path": path, "mode": "full_replace"})
        elif search in content:
            # 首处替换
            new_content = content.replace(search, replace, 1)
            p.write_text(new_content, encoding="utf-8")
            applied.append({"path": path, "mode": "search_replace"})
        else:
            skipped.append({"path": path, "reason": "search fragment not found in file"})
    return applied, skipped


def build_declaration(parsed: dict | None, applied: list, skipped: list,
                      tokens: int, error: str | None) -> dict:
    """组装符合 output_contract 的 declaration。"""
    if parsed is None or error:
        return {
            "deliverable": {"changed_files": [], "diff_summary": ""},
            "intent": f"agent failed: {error or 'LLM output unparseable'}",
            "confidence": "低",
            "known_uncertainties": [error or "LLM 返回无法解析为 JSON"],
            "assumptions": [],
            "usage": {"tokens": tokens},
        }
    return {
        "deliverable": {
            "changed_files": [a["path"] for a in applied],
            "diff_summary": parsed.get("intent", "") + (
                f" | applied={len(applied)} skipped={len(skipped)}" if skipped else ""
            ),
            "applied_edits": applied,
            "skipped_edits": skipped,
        },
        "intent": parsed.get("intent", ""),
        "confidence": parsed.get("confidence", "低"),
        "known_uncertainties": parsed.get("known_uncertainties", []) + [
            s["reason"] for s in skipped
        ],
        "assumptions": parsed.get("assumptions", []),
        "usage": {"tokens": tokens},
    }


def main():
    # 读取 task
    task_file = None
    if "--task-file" in sys.argv:
        idx = sys.argv.index("--task-file")
        task_file = Path(sys.argv[idx + 1])
        with open(task_file, encoding="utf-8") as f:
            task = json.load(f)
    else:
        task = json.loads(sys.stdin.read())

    allowed_files = task.get("allowed_files", [])
    reference_dirs = task.get("reference_dirs", [])
    primary_files = set(task.get("primary_files", []))
    root = Path(os.environ.get("PROJECT_DIR", ".") or ".").resolve()
    if not (root / "config.json").exists():
        root = Path.cwd()

    # 展开 "*" → 整个项目（排除 verify/ 等基础设施）
    if "*" in allowed_files:
        allowed_files = discover_project_files(root)
    allowed_set = set(allowed_files)

    # 读取文件内容作为上下文（优先 primary_files）
    file_contents = read_allowed_files(allowed_files, root)
    ref_contents = read_reference_dirs(reference_dirs, root)

    # 调用 LLM
    error = None
    parsed = None
    tokens = 0
    try:
        cfg = load_code_agent_config()
        user_msg = build_user_message(task, file_contents, ref_contents)
        response_text, tokens = call_llm(cfg, SYSTEM_PROMPT, user_msg)
        parsed = parse_llm_json(response_text)
        if parsed is None:
            error = "LLM 输出无法解析为 JSON"
            # 保存原始响应用于调试
            if task_file:
                raw_path = task_file.parent / "llm_raw_response.txt"
                raw_path.write_text(response_text, encoding="utf-8")
                print(f"[debug] raw LLM response saved to {raw_path}", file=sys.stderr)
    except Exception as e:
        error = f"{type(e).__name__}: {e}"

    # 应用修改
    applied, skipped = [], []
    if parsed and not error:
        file_edits = parsed.get("file_edits", [])
        # 规范化 path 分隔符
        for fe in file_edits:
            if "path" in fe:
                fe["path"] = fe["path"].replace("\\", "/").lstrip("./")
        applied, skipped = apply_edits(file_edits, allowed_set, root)

    # 输出声明
    declaration = build_declaration(parsed, applied, skipped, tokens, error)
    declaration_json = json.dumps(declaration, ensure_ascii=False, indent=2)

    # 自动落盘到 task.json 同目录
    if task_file:
        out_path = task_file.parent / "declaration.json"
        out_path.write_text(declaration_json, encoding="utf-8")
        print(f"[saved] {out_path}", file=sys.stderr)

    # stdout 供 loop_manager subprocess 捕获
    print(declaration_json)
    sys.exit(0)


if __name__ == "__main__":
    main()
