# -*- coding: utf-8 -*-
import subprocess, sys
cmd = [sys.executable, 'sync_md_to_ai_excel.py', 'pt_outputv1.md', r'C:\Users\15831\Desktop\能力验证平台验收\测试用例-AI版.xlsx']
r = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
print(r.stdout)
print(r.stderr)
sys.exit(r.returncode)
