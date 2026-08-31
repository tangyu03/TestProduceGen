# srs_pipeline/cli.py —— 完整替换
from __future__ import annotations
import argparse
import importlib
import json
import sys

from .model import (CriticalAmbiguity, build_deviation_feedback,
                    build_downgrade_feedback, build_feedback, interrupt_schema)

def main(argv=None) -> int:
    # GBK 控制台（Windows 中文默认 cp936）打印 Unicode 描述（如 ↔）会
    # UnicodeEncodeError，使错误/歧义列表打印中断；统一改 UTF-8 + 替换符。
    for _stream in (sys.stdout, sys.stderr):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(prog="srs-pipeline",
                                 description="需求文档结构化 JSON 生成框架（P1.5）")
    ap.add_argument("module", help="数据模块路径，需暴露 build() -> DomainModel")
    ap.add_argument("-o", "--output", required=True)
    ap.add_argument("--feedback",
                    help="可选：回喂 JSON 落盘路径（glm5pr §5 [check/labels/expected]，"
                         "投给 LLM 再生成）；缺省不落盘，仅控制台打印")
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
        print(f"critical 歧义（{len(ca.items)} 项），已输出中断 Schema: {args.output}")
        feedback = build_feedback(ca.items)
        if args.feedback:
            with open(args.feedback, "w", encoding="utf-8") as f:
                json.dump(feedback, f, ensure_ascii=False, indent=2)
            print(f"回喂 JSON（glm5pr §5，投给 LLM 再生成）: {args.feedback}")
        else:
            print("回喂 JSON（glm5pr §5，投给 LLM 再生成）:")
            print(json.dumps(feedback, ensure_ascii=False, indent=2))
        for i, item in enumerate(ca.items, 1):
            aid = item.get('amb_id', '?')
            conc = item.get('concept', '')
            print(f"  [{i}] {aid} [{conc}] {item.get('description', '')}")
            if item.get('assumption'):
                print(f"      assumption: {item['assumption']}")
            if item.get('suggestion'):
                print(f"      suggestion: {item['suggestion']}")
        return 2
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    report.print()
    if model.review_queue:
        print(f"评审队列 {len(model.review_queue)} 项:")
        for item in model.review_queue:
            print(f"  - [{item['kind']}] {item['concept']}")
    # 自动降级（C03 锚点/C08 组合）＋分支回填偏差（C31 warn）闭合修复回路：
    # 正常完成也回喂 §5 格式给 LLM（无原文依据的修补须在数据源头修正）。
    downgrade_fb = build_downgrade_feedback(report)
    deviations = model.meta.get("branch_tt_deviations", [])
    fb = downgrade_fb + (build_deviation_feedback(deviations) if deviations else [])
    if fb:
        tags = []
        if downgrade_fb:
            tags.append(f"自动降级 {len(downgrade_fb)} 项")
        if deviations:
            tags.append(f"分支回填偏差 {len(deviations)} 项")
        tag = " + ".join(tags)
        if args.feedback:
            with open(args.feedback, "w", encoding="utf-8") as f:
                json.dump(fb, f, ensure_ascii=False, indent=2)
            print(f"回喂 JSON（{tag}）: {args.feedback}")
        else:
            print(f"回喂 JSON（glm5pr §5，{tag}，投给 LLM 再生成）:")
            print(json.dumps(fb, ensure_ascii=False, indent=2))
    print(f"输出: {args.output} | consistency_check="
          f"{output['_meta']['consistency_check']}")
    return 1 if (args.strict and report.errors) else 0

if __name__ == "__main__":
    sys.exit(main())
