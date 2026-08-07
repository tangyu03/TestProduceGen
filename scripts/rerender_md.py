#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""渲染层确定性重渲染 p3_agent_output.md（不跑流水线、不碰 JSON 数据）。

背景：P3 流水线含 LLM 标题生成（随机），完整重跑会改 JSON、破坏确定性。
本脚本只消费已落档的 `p3_agent_output.json`（procedures）+ P2 coverage_model
（`coverage_obligations.json` 的 `_context.state_info`），对 `main._generate_markdown`
做纯渲染层调用，并双跑哈希校验确定性。

用法：
  python scripts/rerender_md.py [output.md] [chk.md]
"""
import sys
import json
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import main  # noqa: E402  (repo root 已在 sys.path)
MD_PATH = sys.argv[1] if len(sys.argv) > 1 else str(ROOT / "p3_agent_output.md")
CHK_PATH = sys.argv[2] if len(sys.argv) > 2 else str(ROOT / "_chk.md")


def load_json(p: str) -> dict:
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def run():
    procs = load_json(ROOT / "p3_agent_output.json")["procedures"]
    cm = load_json(ROOT / "coverage_obligations.json")

    # 正式文件：真实路径
    main._generate_markdown(procs, MD_PATH, cm)
    # 校验副本：双跑哈希
    main._generate_markdown(procs, CHK_PATH, cm)

    h_md = hashlib.sha256(Path(MD_PATH).read_bytes()).hexdigest()
    h_chk = hashlib.sha256(Path(CHK_PATH).read_bytes()).hexdigest()
    print(f"[OK] deterministic double-run: {h_md == h_chk}")
    print(f"[OK] wrote {Path(MD_PATH)} ({Path(MD_PATH).stat().st_size} bytes)")
    if h_md != h_chk:
        sys.exit(1)
    Path(CHK_PATH).unlink(missing_ok=True)


if __name__ == "__main__":
    run()
