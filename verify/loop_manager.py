#!/usr/bin/env python3
"""外层自优化循环管理者（Step 2）。

职责：编排 git worktree 快照 → 代码 Agent 修改 → 冒烟 → 跑流水线 →
Gate-S 门禁 → 失败签名路由 / 回归门控合并 / 硬停止 / 升级。

用法：
  python -m verify.loop_manager --config verify/loop_config.json --once
  python -m verify.loop_manager --config verify/loop_config.json --loop
  python -m verify.loop_manager --config verify/loop_config.json --loop --full
  python -m verify.loop_manager --config verify/loop_config.json --dry-run --once
  python -m verify.loop_manager --config verify/loop_config.json --init-baseline

  --loop        快速模式: 只跑 generate_obligation_model.py (秒级)，适合 P2 迭代
  --loop --full 完整模式: 跑 main.py 全 LLM 流水线 (分钟级)，适合最终验证
"""
from __future__ import annotations
import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path

# ───────────────────────── 失败签名路由表 ─────────────────────────
# files:    可修改的源文件
# ref_dirs: 只读参考目录（agent 自动加载目录下所有可读文件作为上下文）
#           所有 check 都会额外包含 DEFAULT_REF_DIRS

DEFAULT_REF_DIRS = ["context"]

ROUTING_TABLE = {
    "V01": {"stage": "S3", "files": ["nodes/s3_dependency.py", "tools/graph_algo.py"],
            "hint": "依赖引用悬空/环/相位倒置：dep_origins 需改用最终 temp_id 命名空间"},
    "V02": {"stage": "S3", "files": ["nodes/s3_dependency.py", "prompts/s1_prompt.py"],
            "hint": "guard 禁止语义被反转：解析前置条件时保留 polarity，禁止生成成功迁移"},
    "V03": {"stage": "S0", "files": ["nodes/s0_topology.py", "prompts/s0_prompt.py"],
            "hint": "动作挂错实体：跨实体级联只能用 indirect_via，不得直接操作从动实体"},
    "V04": {"stage": "P2", "files": ["context/generate_obligation_model.py", "nodes/field_validation.py"],
            "hint": "内置对象被误建义务：readonly/no_form_page 实体跳过 type3/9 义务"},
    "V05": {"stage": "S4", "files": ["nodes/s4_multi_instance.py", "nodes/s0_topology.py"],
            "hint": "维度组合爆炸：实例化前用 dimension_constraints 做可达性剪枝"},
    "V08": {"stage": "S0", "files": ["nodes/s0_topology.py", "nodes/s2_sorting.py"],
            "hint": "相位映射错误：终态=最大相位，沿迁移相位不倒退"},
    "V09": {"stage": "S4", "files": ["nodes/s4_multi_instance.py"],
            "hint": "多实例无差别复制：相同 (givens,when,thens) 合并；单例实体不复制"},
    "V10": {"stage": "P2", "files": ["context/generate_obligation_model.py", "prompts/s0_prompt.py"],
            "hint": "覆盖缺口：coverage_matrix 条目未命中，补义务而非事后补丁"},
}
DEFAULT_ROUTING = {"stage": "S1", "files": ["nodes/s1_generation.py"],
                   "hint": "未分类失败，附完整 verdict 定位"}


# ───────────────────────── 配置 ─────────────────────────
@dataclass
class LoopConfig:
    project_dir: str = "."
    pipeline_cmd: list = field(default_factory=lambda: ["python", "main.py",
                                                        "test_coverage_model.json",
                                                        "{run_dir}/output.json"])
    pipeline_cmd_full: list = field(default_factory=list)  # --full 时用的完整流水线
    validator_spec: str = "verify/case_spec.json"
    validator_model: str = "coverage_obligations.json"
    smoke_cmd: list = field(default_factory=list)
    agent_cmd: list = field(default_factory=list)
    max_attempts_per_signature: int = 3
    token_budget: int = 2_000_000
    wall_clock_budget_sec: int = 4 * 3600
    history_path: str = "verify/quality_history.jsonl"
    baseline_path: str = "verify/golden_baseline.json"
    runs_dir: str = "verify/runs"
    regression_metrics: list = field(default_factory=lambda: ["dedup_ratio", "coverage_misses"])

    @staticmethod
    def load(path: str) -> "LoopConfig":
        with open(path, encoding="utf-8") as f:
            return LoopConfig(**json.load(f))


# ───────────────────────── git 快照（worktree，无 git 时退化为 copytree） ─────────────────────────
class WorktreeManager:
    def __init__(self, project_dir: str):
        self.project_dir = Path(project_dir).resolve()
        self.snapshot: Path | None = None
        self._use_git = (self.project_dir / ".git").exists()
        self._wt_name = f"loop-{int(time.time())}"

    def create(self) -> Path:
        if self._use_git:
            target = self.project_dir.parent / self._wt_name
            subprocess.run(["git", "worktree", "add", "--detach", str(target), "HEAD"],
                           cwd=self.project_dir, check=True, capture_output=True)
            self.snapshot = target
        else:
            self.snapshot = Path(tempfile.mkdtemp(prefix="loop-snapshot-"))
            shutil.copytree(self.project_dir, self.snapshot, dirs_exist_ok=True,
                            ignore=shutil.ignore_patterns(".git", "verify/runs", "__pycache__"))
        return self.snapshot

    def merge_back(self):
        if self._use_git and self.snapshot:
            subprocess.run(["git", "-C", str(self.snapshot), "add", "-A"], check=True)
            subprocess.run(["git", "-C", str(self.snapshot), "commit", "-m", "loop: agent fix"],
                           check=True, capture_output=True)
            subprocess.run(["git", "merge", "--no-ff", self.snapshot.name],
                           cwd=self.project_dir, check=True, capture_output=True)

    def discard(self):
        if not self.snapshot:
            return
        if self._use_git:
            subprocess.run(["git", "worktree", "remove", "--force", str(self.snapshot)],
                           cwd=self.project_dir, capture_output=True)
        else:
            shutil.rmtree(self.snapshot, ignore_errors=True)
        self.snapshot = None


# ───────────────────────── 历史与回归门控 ─────────────────────────
class History:
    def __init__(self, path: str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.records = [json.loads(l) for l in self.path.read_text(encoding="utf-8").splitlines()
                        if l.strip()] if self.path.exists() else []

    def append(self, rec: dict):
        rec["ts"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        self.records.append(rec)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    def count(self, signature: str) -> int:
        return sum(1 for r in self.records if r.get("signature") == signature)

    def same_diff_failed(self, signature: str, diff_hash: str) -> bool:
        return any(r.get("signature") == signature and r.get("diff_hash") == diff_hash
                   and not r.get("merged") for r in self.records)

    def trace(self, signature: str) -> list:
        return [r for r in self.records if r.get("signature") == signature]


def load_baseline(path: str) -> dict:
    p = Path(path)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def regressing(baseline: dict, metrics: dict, keys: list) -> bool:
    """只许向好：dedup_ratio 不得更低，其余计数型指标不得更高。"""
    if not baseline:
        return False
    bm = baseline.get("metrics", {})
    for k in keys:
        if k not in bm or k not in metrics:
            continue
        if k == "dedup_ratio" and metrics[k] < bm[k]:
            return True
        if k != "dedup_ratio" and metrics[k] > bm[k]:
            return True
    return False


# ───────────────────────── 代码 Agent 接入 ─────────────────────────
def run_code_agent(cfg: LoopConfig, task: dict, cwd: Path) -> dict:
    """约定：agent_cmd 从 stdin 接收 task JSON，stdout 输出构建者结构化声明。"""
    if not cfg.agent_cmd:
        return {"skipped": True, "reason": "agent_cmd not configured",
                "confidence": "低", "usage": {"tokens": 0}}
    proc = subprocess.run(cfg.agent_cmd, input=json.dumps(task, ensure_ascii=False),
                          cwd=cwd, capture_output=True, text=True, timeout=1800)
    out = proc.stdout.strip()
    try:                                            # 容错：取第一个 JSON 对象
        start = out.index("{")
        return json.loads(out[start:])
    except (ValueError, json.JSONDecodeError):
        return {"skipped": False, "parse_error": True, "raw_tail": out[-500:],
                "confidence": "低", "usage": {"tokens": 0}}


def failure_signature(verdict: dict) -> str | None:
    """check_id + 主要证据键的稳定签名（同一缺陷簇归并计数）。"""
    parts = []
    for c in verdict.get("checks", []):
        if c["result"] != "fail" or c["severity"] != "blocker":
            continue
        keys = sorted({str(sorted(e.items())[0])[:48] for e in c.get("evidence", [])[:5]
                       if isinstance(e, dict) and e})
        parts.append(c["check_id"] + ":" + ",".join(keys[:3]))
    if not parts:
        return None
    return hashlib.sha1("|".join(sorted(parts)).encode()).hexdigest()[:12]


def build_task(verdict: dict, signature: str, history: History) -> dict:
    """上下文最小化：只喂失败签名相关的检查证据 + 路由文件 + 历史尝试摘要。"""
    failed = [c for c in verdict.get("checks", [])
              if c["result"] == "fail" and c["severity"] == "blocker"]
    files, ref_dirs, hints = set(), set(DEFAULT_REF_DIRS), []
    for c in failed:
        r = ROUTING_TABLE.get(c["check_id"], DEFAULT_ROUTING)
        files.update(r.get("files", []))
        ref_dirs.update(r.get("ref_dirs", []))
        hints.append(f"[{c['check_id']}] {r['hint']}")
    prior = [{"diff_summary": t.get("diff_summary"), "verdict": t.get("verdict")}
             for t in history.trace(signature)[-3:]]
    return {
        "role": "builder",
        "objective": "修复 Gate-S 骨架门禁报告的结构性缺陷，从第一性原理修复根因",
        "failed_checks": failed,
        "routing_hints": hints,
        "primary_files": sorted(files),
        "allowed_files": ["*"],
        "reference_dirs": sorted(ref_dirs),
        "prior_failed_attempts": prior,
        "output_contract": {
            "deliverable": {"changed_files": [], "diff_summary": ""},
            "intent": "", "confidence": "高|中|低",
            "known_uncertainties": [], "assumptions": [], "usage": {"tokens": 0},
        },
    }


def escalate(cfg: LoopConfig, signature: str, history: History, reason: str):
    run_dir = Path(cfg.runs_dir) / time.strftime("%Y%m%d-%H%M%S")
    run_dir.mkdir(parents=True, exist_ok=True)
    report = {"signature": signature, "reason": reason,
              "trace": history.trace(signature)}
    (run_dir / f"escalation_{signature}.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[ESCALATE] {signature}: {reason} → {run_dir}")


# ───────────────────────── 主循环 ─────────────────────────
def one_attempt(cfg: LoopConfig, history: History, dry_run: bool,
                full_pipeline: bool = False) -> str:
    """返回 done | retry | escalated | budget_exceeded。"""
    run_dir = Path(cfg.runs_dir) / time.strftime("%Y%m%d-%H%M%S")
    run_dir.mkdir(parents=True, exist_ok=True)

    # 0. 先跑一轮基线判定（不修也能知道当前水位）
    wt = WorktreeManager(cfg.project_dir)
    snap = wt.create()
    try:
        verdict_path = run_dir / "verdict.json"
        output_json = run_dir / "output.json"

        # ── 管线步骤 ──
        if full_pipeline and cfg.pipeline_cmd_full:
            # --full: 跑完整 LLM 流水线 (main.py)
            pipeline_cmd = [c.format(run_dir=str(run_dir.resolve()))
                            for c in cfg.pipeline_cmd_full]
            r = subprocess.run(pipeline_cmd, cwd=snap, capture_output=True,
                               text=True, timeout=3600)
            (run_dir / "pipeline.log").write_text(
                r.stdout[-8000:] + r.stderr[-8000:], encoding="utf-8")
            if r.returncode != 0:
                print("[FAIL] full pipeline crashed, see pipeline.log")
                return "retry"
        elif cfg.pipeline_cmd:
            # 默认: 跑快速生成 (generate_obligation_model.py)
            pipeline_cmd = [c.format(run_dir=str(run_dir.resolve()))
                            for c in cfg.pipeline_cmd]
            r = subprocess.run(pipeline_cmd, cwd=snap, capture_output=True,
                               text=True, timeout=300)
            (run_dir / "pipeline.log").write_text(
                r.stdout[-8000:] + r.stderr[-8000:], encoding="utf-8")
            if r.returncode != 0:
                print("[FAIL] pipeline crashed, see pipeline.log")
                return "retry"
        else:
            # 无 pipeline: 直接读已有结果文件
            existing = Path(cfg.project_dir) / "coverage_obligations.json"
            if not existing.exists():
                print(f"[FAIL] no existing output found: {existing}")
                return "escalated"
            shutil.copy(existing, output_json)
            (run_dir / "pipeline.log").write_text(
                f"skipped pipeline, copied from {existing}\n", encoding="utf-8")

        v = subprocess.run([sys.executable, "-m", "verify.validators",
                            "-s", cfg.validator_spec,
                            "-m", cfg.validator_model,
                            "-o", str((run_dir / "output.json").resolve()),
                            "--json", str(verdict_path.resolve())],
                           cwd=snap, capture_output=True, text=True)
        (run_dir / "validator_stdout.log").write_text(v.stdout, encoding="utf-8")
        (run_dir / "validator_stderr.log").write_text(v.stderr, encoding="utf-8")

        if v.returncode != 0:
            # validators may exit non-zero when failures are found — check if
            # verdict.json was still produced before treating it as a crash
            if verdict_path.exists():
                print(f"[WARN] validators exited {v.returncode} but verdict.json exists, "
                      f"proceeding with verdict")
            else:
                print(f"[FAIL] validators exited {v.returncode} and no verdict.json")
                print("── validator stderr (last 2000 chars) ──")
                print(v.stderr[-2000:])
                print("── validator stdout (last 1000 chars) ──")
                print(v.stdout[-1000:])
                history.append({"signature": "VALIDATOR_CRASH", "verdict": "fail",
                                "merged": False,
                                "detail": f"exit={v.returncode}; stderr_tail={v.stderr[-300:]}"})
                return "escalated"

        if not verdict_path.exists():
            print(f"[FAIL] validators exit 0 but verdict.json missing: {verdict_path}")
            print("── validator stdout ──")
            print(v.stdout[-2000:])
            history.append({"signature": "NO_VERDICT_FILE", "verdict": "fail",
                            "merged": False, "path": str(verdict_path)})
            return "escalated"

        try:
            verdict = json.loads(verdict_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            print(f"[FAIL] verdict.json corrupt: {e}")
            print("── verdict.json content ──")
            print(verdict_path.read_text(encoding="utf-8")[:1000])
            return "escalated"

        sig = failure_signature(verdict)

        if verdict["skeleton_pass"]:
            baseline = load_baseline(cfg.baseline_path)
            if regressing(baseline, verdict["metrics"], cfg.regression_metrics):
                history.append({"signature": "REGRESSION", "verdict": "fail",
                                "metrics": verdict["metrics"], "merged": False})
                print("[FAIL] quality regression vs golden baseline, snapshot discarded")
                return "escalated" if not dry_run else "done"
            if not dry_run:
                wt.merge_back()
                Path(cfg.baseline_path).write_text(json.dumps(
                    {"metrics": verdict["metrics"], "ts": time.strftime("%F %T")},
                    ensure_ascii=False, indent=2), encoding="utf-8")
                history.append({"signature": None, "verdict": "pass",
                                "metrics": verdict["metrics"], "merged": True})
            print("[PASS] skeleton gate green, merged" if not dry_run
                  else "[PASS] (dry-run) skeleton gate green")
            return "done"

        # 1. 失败 → 路由给代码 Agent
        if not sig:
            print("[FAIL] gate failed but no signature (check crashed?)")
            return "escalated"
        if history.count(sig) >= cfg.max_attempts_per_signature:
            escalate(cfg, sig, history, "max attempts reached for signature")
            return "escalated"

        task = build_task(verdict, sig, history)
        (run_dir / "task.json").write_text(json.dumps(task, ensure_ascii=False, indent=2),
                                           encoding="utf-8")
        declaration = run_code_agent(cfg, task, snap)
        (run_dir / "declaration.json").write_text(
            json.dumps(declaration, ensure_ascii=False, indent=2), encoding="utf-8")
        diff_hash = hashlib.sha1(json.dumps(
            declaration.get("deliverable", {}), sort_keys=True,
            ensure_ascii=False).encode()).hexdigest()[:12]
        if history.same_diff_failed(sig, diff_hash):
            escalate(cfg, sig, history, "same diff already failed once; refusing repeat")
            return "escalated"

        if cfg.smoke_cmd:                              # 冒烟不过，直接判失败不重跑流水线
            s = subprocess.run(cfg.smoke_cmd, cwd=snap, capture_output=True, text=True)
            if s.returncode != 0:
                history.append({"signature": sig, "verdict": "smoke_fail",
                                "diff_hash": diff_hash,
                                "diff_summary": declaration.get("deliverable", {})
                                .get("diff_summary", ""), "merged": False})
                print("[FAIL] smoke test failed")
                return "retry"

        history.append({"signature": sig, "verdict": "fail",
                        "diff_hash": diff_hash,
                        "diff_summary": declaration.get("deliverable", {})
                        .get("diff_summary", ""),
                        "confidence": declaration.get("confidence"),
                        "tokens": (declaration.get("usage") or {}).get("tokens", 0),
                        "merged": False})
        print(f"[RETRY] signature={sig} attempt={history.count(sig)}"
              f"/{cfg.max_attempts_per_signature}")
        return "retry"
    finally:
        wt.discard() if not dry_run else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", "-c", required=True)
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--loop", action="store_true")
    ap.add_argument("--full", action="store_true",
                    help="Run full LLM pipeline (main.py); default: fast P2 generation only")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--init-baseline", action="store_true")
    args = ap.parse_args()

    cfg = LoopConfig.load(args.config)
    history = History(cfg.history_path)
    t0 = time.monotonic()
    tokens_used = 0

    if args.init_baseline:
        Path(cfg.baseline_path).write_text(json.dumps({"metrics": {}}, indent=2),
                                           encoding="utf-8")
        print("baseline initialized (empty); first pass will populate it")
        return

    if args.full:
        pipeline_mode = "FULL (main.py LLM pipeline)"
    elif cfg.pipeline_cmd:
        pipeline_mode = "FAST (generate_obligation_model.py)"
    else:
        pipeline_mode = "DIRECT (validate existing output, no regeneration)"
    print(f"[LOOP] mode={pipeline_mode}, once={args.once}, dry_run={args.dry_run}")

    while True:
        tokens_used = sum(r.get("tokens", 0) for r in history.records)
        if tokens_used > cfg.token_budget or time.monotonic() - t0 > cfg.wall_clock_budget_sec:
            print(f"[STOP] budget exceeded (tokens={tokens_used})")
            break
        status = one_attempt(cfg, history, args.dry_run, full_pipeline=args.full)
        if status in ("done", "escalated") or args.once:
            break
    print("loop finished")


if __name__ == "__main__":
    main()
