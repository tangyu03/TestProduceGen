python verify/validators.py -s verify/case_spec.json -o test_output.json --json verdict.json


# 调试
# 先用 --dry-run 跑一次 loop_manager，拿到真实 task.json
python -m verify.loop_manager -c verify/loop_config.json --dry-run --once
# task.json 在 verify/runs/<timestamp>/task.json

# 单独跑 Agent，看它怎么改
python verify/code_agent_cli.py --task-file verify/runs/<timestamp>/task.json
# stdout 输出 declaration JSON，文件已被修改（在当前工作目录）
