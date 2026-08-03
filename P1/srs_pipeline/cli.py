# srs_pipeline/cli.py —— 完整替换
from __future__ import annotations
import argparse
import importlib
import json
import sys

from .model import CriticalAmbiguity, interrupt_schema

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="srs-pipeline",
                                 description="需求文档结构化 JSON 生成框架（P1.5）")
    ap.add_argument("module", help="数据模块路径，需暴露 build() -> DomainModel")
    ap.add_argument("-o", "--output", required=True)
    ap.add_argument("--doc", help="需求原文路径；提供后启用 C15 反幻觉审计与双通道对账")
    ap.add_argument("--strict", action="store_true",
                    help="存在 error 时退出码非 0（接 CI 用）")
    args = ap.parse_args(argv)

    model = importlib.import_module(args.module).build()
    if args.doc:
        with open(args.doc, encoding="utf-8") as f:
            model.attach_document(f.read())
    try:
        output, report = model.assemble()
    except CriticalAmbiguity as ca:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(interrupt_schema(model.meta["source"], ca.items),
                      f, ensure_ascii=False, indent=2)
        print(f"critical 歧义，已输出中断 Schema: {args.output}")
        return 2
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    report.print()
    if model.review_queue:
        print(f"评审队列 {len(model.review_queue)} 项:")
        for item in model.review_queue:
            print(f"  - [{item['kind']}] {item['concept']}")
    print(f"输出: {args.output} | consistency_check="
          f"{output['_meta']['consistency_check']}")
    return 1 if (args.strict and report.errors) else 0

if __name__ == "__main__":
    sys.exit(main())
