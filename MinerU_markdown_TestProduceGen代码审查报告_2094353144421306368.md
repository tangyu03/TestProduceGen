# TestProduceGen代码审查报告

对测试规程编排引擎（约4.4万行Python，97个源文件）的全量深度审查： 覆盖 P1/P2/P3 流水线、Gate-S 门禁、LLM工具层与工程规范，共确认68项细目问题，关键发现均附实测复现证据与修复代码。

审查对象 final_pkgV（TestProduceGen v29）

审查方式 核心逐行+外围全量+实测复现

问题规模 Blocker 6 · Critical 12 · Major 14 · Minor 36

## 目录

第一章 执行摘要 1
第二章 审查范围与方法 3
第三章 Blocker 级问题（P0） 4
第四章 Critical 级问题（P1） 8
第五章 Major 级问题（P2） 16
第六章 Minor 级问题（P3） 22
第七章 架构级坏气味专题 26
第八章 工程规范专题 27
第九章 修复路线图 28

## 第一章 执行摘要

本报告是对 TestProduceGen 测试规程编排引擎的全量代码审查结论。该项目通过 P1（结构化抽取）、P2（覆盖义务建模）、P3（LangGraph 测试规程编排）三阶段流水线，将 SRS 自然语言需求转化为可执行的 BDD 测试规程，并由 Gate-S 骨架门禁校验质量。审查范围内包含 97 个Python 源文件、约 4.4 万行代码，重点对 P3 流水线核心（main.py、graph.py、models/、nodes/s0~s4）进行了逐行级阅读，对其余模块进行了全量通读与模式化排查。

审查共确认 68 项细目问题：Blocker（必然出错或安全漏洞）6 项，Critical（特定条件下必然出错）12 项，Major（显著正确性风险或坏气味）14 项，Minor（局部缺陷与卫生问题）36 项。其中 5 项关键发现已在独立环境中实测复现（缓存 key 退化、门禁导入崩溃、schema 校验时机陷阱、V05 匹配模式语义反向、spec_lint 自相矛盾），其余基于代码路径的逐行推演，全部给出精确的文件与行号定位，可直接抽查核实。

总体判断：该项目的领域建模与校验器设计（co_derivation 的 fail-closed、constraint_fields 的 fail-fast 注册表、P1 的 C01~C31 校验矩阵）体现了相当的工程思考，但存在三条贯穿性的系统性风险：一是质量闸门的纸面强度显著高于实际拦截力（fatal 退出码为 0、校验器不设退出码、自检恒真）；二是复制粘贴式演进已经产生多处行为漂移（双份置信度表、两套相似度口径、三份标题生成器）；三是安全底线失守（两把明文 API key 随 Git 历史分发）。建议按第九章的三批修复路线图处理，第一批安全与退出码问题应在当日完成。

<table><tr><td>严重度</td><td>数量</td><td>界定与代表问题</td></tr><tr><td>Blocker</td><td>6</td><td>安全漏洞或主链路必然失败:密钥泄露、缓存 key 退化、门禁导入崩溃、自优化闭环双断点、破坏性脚本</td></tr><tr><td>Critical</td><td>12</td><td>特定条件必然出错:覆盖索引漏传播、schema 时机陷阱、V05/V08 检查失效、退出码失效、假异步客户端</td></tr><tr><td>Major</td><td>14</td><td>显著正确性风险或结构性坏气味:状态解析垃圾值、覆盖丢失合并、死代码簇、三份平行实现、无锁缓存</td></tr><tr><td>Minor</td><td>36</td><td>局部缺陷与卫生问题:正则边界、重复实现、死分支、资源泄漏、路径硬编码、词表漂移</td></tr></table>


表 1：本次审查问题严重度分布


![image](https://cdn-mineru.openxlab.org.cn/result/2026-08-31/f41bff49-f29e-49ef-a9e4-9cca468ea403/6ffe7f08a8d57466985253b0cafac5befd7c066274b157f1976475794732b4a3.jpg)



图 1：各模块问题数量按严重度分布


表 2 列出建议最优先处理的 10 项问题，选取标准为：影响安全、使主链路或门禁必然失效、且修复成本低。

<table><tr><td>编号</td><td>问题</td><td>位置</td></tr><tr><td>B-01</td><td>两把明文 API key 随 Git 历史分发</td><td>config.json:3; verify/llm_config.json:7</td></tr><tr><td>B-02</td><td>TITLE 缓存 key 恒定,不同请求互相命中(已复现)</td><td>tools/llm/cache.py:86-111</td></tr><tr><td>B-03</td><td>门禁导入在 try 外,无 langgraph 环境整机崩溃(已复现)</td><td>verify/validators.py:45-52</td></tr><tr><td>B-06</td><td>run_pipeline 破坏性清空 config.json 的 api_key</td><td>scripts/run_pipeline.py:23-28</td></tr><tr><td>B-04</td><td>merge_back 把 worktree 目录名当 revision,合并必失败</td><td>verify/loop_manager.py:104-110</td></tr><tr><td>B-05</td><td>Agent 修复随快照丢弃,自优化闭环空转</td><td>verify/loop_manager.py:347-389</td></tr><tr><td>C-01</td><td>条款覆盖聚合漏传播(父级 4.9.7(3) 恒未覆盖,已复现)</td><td>main.py:1156-1179</td></tr><tr><td>C-03</td><td>V05 match_mode=exact 未定义,语义反向静默降级(已复现)</td><td>verify/checks/v05_dimension_combo.py:103</td></tr><tr><td>C-08</td><td>P2 fatal 退出码 0、validate_p2 无退出码,门禁不 gate</td><td>context/generate_obligation_model.py:199</td></tr><tr><td>C-09</td><td>required 校验死分支,空列表绕过必填检查</td><td>srs_pipeline/schema.py:332-336</td></tr></table>


表 2：Top 10 必修问题清单


## 第二章 审查范围与方法

本次审查采取「核心逐行 + 外围全量 + 实测复现」的三层方法。P3 流水线核心（main.py、graph.py、models/、nodes/ 五个节点及其辅助模块）为委托方指定的重点，采用逐行阅读方式完成，覆盖全部约 1.2 万行；Gate-S 门禁（verify/）、P1/P2（srs_pipeline/、context/）、数据层（srs_data/）、工具层（tools/ 与 scripts/）采用逐文件通读加模式化排查方式完成。工程规范维度独立核查了 Git 历史、配置与密钥、依赖声明、测试资产与硬编码路径。

为避免「读代码想当然」的误报，我们对五类可疑点搭建了独立运行环境做实测复现：包括在无 langgraph 的干净环境中运行门禁调度器、用两个不同请求验证缓存 key 碰撞、用 S1 形态的过程字典触发 schema 校验、用合成用例验证 V05 匹配模式降级、以及运行 spec_lint 检验其与检查器基础库的数据契约。五项全部复现成功，报告中以「实测复现」标注。对 srs_data 六个版本数据文件实际执行了 diff 与 build/assemble 运行，确认其中三个版本已与当前校验器不兼容。

严重度分级标准如下：Blocker 指安全漏洞或主链路必然失败的问题；Critical 指在特定但常见的条件下必然出错、或使质量闸门失效的问题；Major 指有显著正确性风险、或已经造成维护成本的结构性坏气味；Minor 指局部缺陷、卫生问题与低风险不一致。同一根因的多个表现合并为一个条目编号，统计时按细目展开。

<table><tr><td>模块</td><td>规模</td><td>审查方式</td><td>重点结论</td></tr><tr><td>nodes/+main.py+graph.py+models/</td><td>约12,600行</td><td>逐行阅读+复现实验</td><td>覆盖索引漏传播、schema时机陷阱、依赖绑定不一致、死代码簇</td></tr><tr><td>verify/(门禁与自优化循环)</td><td>17个文件</td><td>逐文件通读+实测运行</td><td>导入崩溃、V05/V08检查失效、闭环双断点、超时未捕获</td></tr><tr><td>srs_pipeline/+context/(P1/P2)</td><td>约8,900行</td><td>逐文件通读+运行验证</td><td>退出码失效、required绕过、单文件巨石、假自检</td></tr><tr><td>srs_data/(数据层)</td><td>6版本数据</td><td>diff+build/assemble实跑</td><td>三版本死数据、复制式版本管理、最新版未入库</td></tr><tr><td>tools/+scripts/(工具与脚本)</td><td>25个文件</td><td>逐文件通读</td><td>缓存key退化、假异步、三份实现、破坏性脚本、路径硬编码</td></tr><tr><td>工程规范(git/配置/测试)</td><td>全仓库</td><td>命令核查</td><td>明文密钥、46/62个fix提交、.ab_tmp入库、零依赖声明</td></tr></table>


表 3：审查范围与方式


## 第三章 Blocker 级问题（P0）

本章 6 项问题属于必须立即处理的类别：两项直接泄露付费 API 凭证，两项使 LLM 标题链路与 Gate-S 门禁在常规使用方式下必然产生错误结果或直接崩溃，两项使自优化循环与无 LLM 回归脚本完全不可用。除 B-04、B-05 为代码路径推演外，其余四项均可一步复现。每项均附修复代码。

## B-01 两把明文 API Key 随 Git 历史分发

```txt
位置：config.json:3；verify/llm_config.json:7（另见scripts/llm_e2e_check.py:243的部分泄露）
```

验证：代码路径推演（行号可抽查）

问题。仓库配置文件中存在两把真实可用的付费 API key：config.json 的 llm.api_key 为 49 字符智谱 key（形如 1d85da…，本报告已脱敏），verify/llm_config.json 为 35 字符 DeepSeekkey（形如 sk-f44…）。git log 显示 config.json 随 58ecec3 fix、69c59b4 V3 等多次提交进入历史，仅删除文件而不清洗历史无法挽回。此外 code_agent_cli.py 在装配 LLM 上下文时会自动加载 llm_config.json，进一步扩大了该 key 的暴露面。

## 证据

```python
config.json
    "llm": { "api_base": "https://open.bigmodel.cn/api/paas/v4",
    "api_key": "1d85da****(49 chars, 已脱敏)", ... }
verify/llm_config.json
    "api_base": "https://api.deepseek.com/v1",
    "api_key": "sk-f44****(35 chars, 已脱敏)"
```

影响。任何拿到仓库（含全部历史）的人可直接盗刷对应账户额度；key 一旦在公开渠道出现即被自动化爬虫捕获。这是全项目风险最高、修复成本最低的一项。

## 修复

```shell
# 1) 立即在两家平台吊销并轮换 key（删文件不够，历史里仍在）
# 2) 清洗历史（git filter-repo）
git filter-repo --path config.json --path verify/llm_config.json --invert-paths
# 3) 配置只走环境变量，配置文件留空模板并加入 .gitignore
# config.json -> "api_key": ""
# .gitignore 追加：config.json
export LLM_API_KEY="${LLM_API_KEY:?need api key}"
```

B-02 TITLE_GENERATION 缓存 key退化为常量，不同请求互相命中（实测复现）

```txt
位置：tools/llm/cache.py:86-111（配合 tools/llm/client.py:207、验证：实测复现（独立环境复现成功）288）
```

问题。LLMClient 构造的缓存 key 是 {'messages': …, 'temperature': …} 字典，而CacheManager._get_cache_key 按 task_type 分派时，把该字典当作「过程列表」交给_get_title_cache_key 处理：对每个元素取 proc.get('steps', []) 恒得空列表，最终所有请求的key 都是同一个哈希值。实测两个完全不同的请求得到相同 key 788daa6857a69fc0，且请求 B 命中了请求 A 写入的缓存。

## 证据

```python
# client.py:207 (TITLE 与 GENERAL 共用同一构造方式)
cache_key = {'messages': messages, 'temperature': temperature}
# cache.py:97-107 request_data 实为 dict，被误当 procedure 列表
if isinstance(procedures, dict): procedures = [procedures]
proc_data = {'steps': proc.get('steps', [])} # 恒为 []
# 实测：请求A/请求B key 均为 788daa6857a69fc0，B 读到 A 的结果
```

影响。config.json 中 cache.enabled=true。凡以

LLMClient(TaskType.TITLE_GENERATION) 方式调用（如 scripts/llm_e2e_check.py:31）并启用缓存时，第一条响应会在 TTL 7 天内被所有不同请求共享：全部标题相同、与输入内容无关、且无任何报错。主链路 main.py 因仍走旧版 llm_client.TitleGenerator（无缓存）暂未踩中，但新版统一客户端一旦被主链路采纳即触发。另注：通用 key 也未包含 model/max_tokens，换模型会读到旧模型缓存。

## 修复

```python
def _get_cache_key(self, request_data):
    if self._task_type == TaskType.TITLE_GENERATION:
    # 请求形态不是 procedure 列表时降级为通用 key，防止 key 恒定
    if isinstance(request_data, dict) and 'messages' in request_data:
    return self._get_generic_cache_key(request_data)
    return self._get_title_cache_key(request_data)
...
# 同时把 model/max_tokens 纳入通用 key:
stable = json.dumps({**request_data, 'model': self._model, 'max_tokens': self._max_tokens}, sort_keys=True)
```

## B-03 门禁检查器导入在 try 块之外，无 langgraph环境整机崩溃（实测复现）

```txt
位置：verify/validators.py:45-52；根因链 v03:16 -> models/_init_.py:10 -> models/state.py:16
```

验证：实测复现（独立环境复现成功）

问题。validators.run_all 逐个加载检查器，但 importlib.import_module 写在 try 块之外，其后才进入逐检查器的异常隔离。v03/v07/v08 顶层执行 from models.schema importObligationType，而 models/__init__.py 又副作用导入 models/state.py，后者依赖langgraph 与 langchain_core。实测在未安装 langgraph 的干净环境中运行 python -mverify.validators 直接 ModuleNotFoundError 崩溃，10 项检查一个都没跑、verdict.json 根本不生成。

## 证据

```python
for name in CHECK_MODULES:
    mod = importlib.import_module(f"verify.checks.{name}")  # <- try 外
    t0 = time.time()
    try:
    r = mod.check(output, spec)
    except Exception as e:  # 注释宣称"检查器自身崩溃不得静默"
# 实测：ModuleNotFoundError: No module named 'langgraph' (整机退出)
```

影响。骨架门禁与主流水线运行时强耦合，无法独立部署；任何一个检查器的导入失败都使全部校验失效而非单检查 fail，使「Gate-S 门禁」在最需要它的环境（干净 CI 机）恰好不可用。

## 修复

```python
for name in CHECK_MODULES:
    try:
    mod = importlib.import_module(f"verify.checks.{name}")
except Exception as e:
    results.append(CheckResult(name[:3].upper(), "error", "blocker",
    note=f"import failed: {e}"))
continue
# 治本：把 ObligationType 常量下沉到 verify/checks/base.py（仅 IntEnum，无副作用导入），
# v03/v07/v08 改从 base 导入，切断对 models/__init__ 的依赖
```

B-04 merge_back 把 worktree 目录名当作 git revision，合并必然失败

```txt
位置：verify/loop_manager.py:104-110（结合:95的--detach创建） 验证：代码路径推演（行号可抽查）
```

问题。WorktreeManager 以 git worktree add --detach 创建快照，该快照不存在名为 loop-<时间戳> 的分支或引用；随后 merge_back 执行 git merge --no-ff <目录名>，git 必然报 notsomething we can merge，check=True 抛出 CalledProcessError，而 one_attempt 未捕获该异常。此外 :107 的 git commit 未加 --allow-empty，DIRECT 模式（pipeline_cmd=[]）下快照没有任何改动，commit 退出码 1 同样崩溃。

## 证据

```python
subprocess.run(["git", "-C", str(self.snapshot), "commit", "-m", "loop: agent fix"], check=True, capture_output=True)
subprocess.run(["git", "merge", "--no-ff", self.snapshot.name], # 目录名不是 revision
cwd=self.project_dir, check=True, capture_output=True)
```

影响。「合并回主干」这条唯一成功路径 100% 走不通，长跑循环在第一次尝试合并时崩溃。

## 修复

```python
rev = subprocess.run(["git", "-C", str(self.snapshot), "rev-parse", "HEAD"], check=True, capture_output=True, text=True).stdout.strip()
dirty = subprocess.run(["git", "-C", str(self.snapshot), "status", "--porcelain"], capture_output=True, text=True).stdout.strip()
if dirty:
    subprocess.run(["git", "-C", str(self.snapshot), "commit", "-am", "loop: agent fix", "--allow-empty"], check=True)
subprocess.run(["git", "merge", "--no-ff", rev], cwd=self.project_dir, check=True, capture_output=True) 
```

## B-05 Agent 的修复随快照一起丢弃，自优化闭环整体空转

```txt
位置：verify/loop_manager.py:347-389（结合 92-120 与 174-175） 验证：代码路径推演（行号可抽查）
```

问题。one_attempt 的时序是：先跑流水线与 Gate-S 得到 verdict，失败后才调用代码 Agent 在快照里修改，但修改之后本轮不再重跑 validators，直接 return "retry"；finally 把快照连同全部修改一起删除。下一轮 WorktreeManager.create() 从未修改的 HEAD/原目录重建快照。git模式下 merge_back 只在 pass 分支调用，而 pass 判定发生在 Agent 运行之前；非 git 模式merge_back 直接 no-op。

## 证据

```python
declaration = run_code_agent(cfg, task, snap) # agent 只改快照
...
history.append({..., "merged": False})
return "retry"
finally:
    wt.discard() if not dry_run else None # 快照连同修改一起删除
```

影响。Agent 的修复永远无法进入下一轮验证，循环只能依赖首轮裸过或耗尽 4 小时/200 万token预算收场——签名去重、同 diff 拒绝、预算熔断等周边工程做得越细，越掩盖「修复根本进不了下一轮」这一空洞。自优化机制名存实亡。

## 修复

```python
# agent 修改后立即重跑 validators，把 pass 判定移到 agent 之后：
declaration = run_code_agent(cfg, task, snap)
verdict2 = run_validators(snap)    # 对快照内产物复检
if verdict2.skeleton_pass:
    merge_back(snap)    # git: merge HEAD SHA; 非 git: copytree 回写
    return "done"
history.append({..., "merged": False, "verdict2": verdict2.signature})
# retry 时保留快照供下轮增量修复（budget 内）
```

## B-06 run_pipeline.py 硬编码外部机器路径，并永久清空仓库config.json 的 api_key

```csv
位置：scripts/run_pipeline.py:6,9,23-28
```

验证：代码路径推演（行号可抽查）

问题。脚本顶部 PROJECT_DIR 硬编码为另一个目录（…/TestProduceGen_bdd_v29），随后os.chdir 过去——在本仓库内运行必然失败。更严重的是其「无 LLM 模式」实现方式：把config.json 备份为 config.json.bak（备份文件仍含明文 key，新增泄露面），然后把仓库config.json 的 api_key 永久置空，运行结束不还原。

## 证据

```javascript
PROJECT_DIR = '/home/z/my-project/work/extracted/TestProduceGen_bdd_v29'
os.chdir(PROJECT_DIR)    # 本仓库内必崩
...
bak = json.load(open('config.json')); ...    # 备份含明文 key
cfg['llm']['api_key'] = ''    # 永久清空，不还原
```

影响。换机器即崩；本机跑一次则抹掉配置里的 key，下一个运行 llm_e2e_check 的人直接FATAL；.bak 文件本身又成为新的密钥泄露点。

## 修复

```python
# 删除整段破坏性逻辑。无 LLM 模式用环境变量覆盖即可（脚本本就 export LLM_API_KEY='')
PROJECT_DIR = Path(__file__).resolve().parent.parent
# main.py 读取顺序已是 环境变量 > config.json，无需改写仓库配置
```

## 第四章 Critical 级问题（P1）

本章 12 项问题的共同特征是：在特定但相当常见的条件下必然出错，或使某条质量闸门失效。其中 C-01、C-02、C-03、C-06 四项已实测复现。它们多数不表现为崩溃，而表现为「静默地给出错误结论」——覆盖索引漏报、维度检查漏报、校验必然抛异常、CI 把致命错误当成功——这类问题比崩溃更危险，因为使用者会继续信任错误的结果。

## C-01 条款覆盖聚合漏传播：直接父级永不被子条款覆盖（实测复现）

位置：main.py:1156-1179（_build_clause_coverage Step 5） 验证：实测复现（独立环境复现成功）问题。父条款覆盖传播使用单遍 sorted 循环，且子条款判定要求 rest[0] in '(['。实测三级链{4.9.7, 4.9.7(3), 4.9.7(3)b}：叶子 b 已覆盖时，祖父 4.9.7 因 startswith 跨级命中被直接标记，但直接父级 4.9.7(3) 的后缀是字母 b（不在 '([' 之中），永远不会被其子条款传播——复现结果4.9.7(3) covered=False。另外以「.」分隔的父子（如 4.9 与 4.9.7）同样因 rest='.' 不在 '([' 而永不传播。

## 证据

```python
for other in clause_keys:
    if other != clause and other.startswith(prefix):
    rest = other[len(prefix):]
    if rest and rest[0] in '('[':    # 字母后缀 "."分隔 均不命中
    if clauses_output[other]["covered']: ...
# 实测：4.9.7(3)b 已覆盖 -> 4.9.7 covered=True，4.9.7(3) covered=False
```

影响。clause_coverage.summary 虚报 uncovered（或经由跨级命中虚报 covered），下游V10/验收若引用该索引将产生假缺口或假覆盖，覆盖统计不可信。

## 修复

```python
def _parent_of(clause):    # 4.9.7(3)b -> 4.9.7(3) -> 4.9.7 -> 4.9
    m = re.match(r'^(.*)((^[^])*|[a-z])$', clause)
    return m.group(1) if m else clause.rsplit('.', 1)[0]

changed = True

while changed:    # 迭代到不动点，替代单遍循环
    changed = False
    for clause in clause_keys:
    p = _parent_of(clause)
    if p in clauses_output and not clauses_output[p]["covered"] \
    and clauses_output[clause]["covered"]:
    clauses_output[p]["covered"] = True
    clauses_output[p]["covered_by_child"] = True
    covered_count += 1; changed = True
```

C-02 Procedure schema 的阶段字段必填，S1产物校验必然抛异常（实测复现）

```txt
位置：models/schema.py:284-286
```

```txt
验证：实测复现（独立环境复现成功）
```

问题。Procedure 的 _S2_fields/_S3_fields/_S4_fields 三个别名字段均无默认值。模块docstring 声称「每个 stage transition 都应校验其输出」，但 S1 刚产出、S2 尚未运行的过程字典没有这些键，validate_procedure 必然抛 ValidationError。实测用 S1 形态字典调用，异常指向缺失字段 _S2_fields。

## 证据

```txt
S2_fields: "S2Fields" = Field(alias="_S2_fields") # 无 default
S3_fields: "S3Fields" = Field(alias="_S3_fields")
S4_fields: "S4Fields" = Field(alias="_S4_fields")
# 实测：validate_procedure(S1形态dict) -> ValidationError: _S2_fields
```

影响。所谓 invariant guard 实际只能在 S4 之后运行，S1/S2/S3 的 fail-fast 承诺落空；任何试图在流水线中途校验的调用方都会被误导性地判定全部数据非法。

## 修复

```txt
位置：verify/checks/v05_dimension_combo.py:29-33, 44-46 验证：代码路径推演（行号可抽查）
```

```python
S2_fields: "S2Fields" = Field(default_factory=lambda: S2Fields(
    phase=0, phase_name="", phase_basis="", topology_level=0,
    sort_key=[], operation_lifecycle=0, chain_depth=0,
    type_label="", type_priority=0, dimension_priority=0),
    alias="_S2_fields")
# 或按阶段拆分 S1Procedure / S4Procedure 两个 schema，避免用一把尺子量所有阶段
```

## C-03 V05 的 match_mode=exact 未定义，合法用例被按语义相反的 any处理（实测复现）

```txt
位置：verify/checks/v05_dimension_combo.py:103-105（配合验证：实测复现（独立环境复现成功）verify/case_spec.json 全部 29 个 combo）
```

问题。代码只实现 all/any 两种匹配模式，而 spec 数据 29/29 个维度组合全部使用 "

match_mode": "exact"——不在文档声明之列，于是全部落入 else 分支按 any 处理（任一探针命中即违规）。实测合成用例：givens 同时含「计划状态=暂停」与「暂停前状态=待评审」这一完全合法的组合被判 violated。

## 证据

```txt
mode = str(combo.get("match_mode", "all")).lower()
hits = sum(1 for _, probe in probes if probe and probe in g_text)
violated = (hits == len(probes)) if mode == "all" else (hits > 0)
# case_spec.json: 29/29 使用 "exact" -> 全部走 else (any) 分支
```

影响。V05 的判定在两个方向上都不可信：探针文本与 givens 格式相符时误杀合法用例；不相符时整体恒 pass 形成漏报。blocker 级检查器失效意味着维度可达性剪枝形同虚设。

## 修复

```python
mode = str(combo.get("match_mode", "all")).lower()
if mode == "exact":
    violated = all(_exact_hit(v, givens) for _, v in probes)  # 等值匹配
elif mode == "all":
    violated = hits == len(probes)
elif mode == "any":
    violated = hits > 0
else:
    warnings.append(f"V05: unknown match_mode={mode!r} in spec")  # 不静默降级
    violated = False
```

## C-04 V05 pre_pause 探针双重前缀，恒不命中导致整类组合漏报

问题。探针模板对 pre_pause 维度会再加一次「暂停前状态=」前缀，而 spec 数据中的值本身已携带该前缀，实测生成的探针为「暂停前状态=暂停前状态=已建立」，在 givens 文本中永远匹配不上。与 C-03 叠加后，V05 的实际行为退化为只看 current 探针。

## 证据

```txt
_KEY_PROBE_TEMPLATES = {"current": "{}", "pre_pause": "暂停前状态={}", ...}
# spec: "pre_pause": "暂停前状态=已建立"（自带前缀）
# 实测 probe: ('pre_pause', '暂停前状态=暂停前状态=已建立')
```

影响。所有涉及 pre_pause 的非法组合（暂停前状态=已建立/结束等）全部漏报。

## 修复

```python
def _probe_for_key(key, value):
    tpl = _KEY_PROBE_TEMPLATES.get(key, "{{}")
    prefix = tpl[:-2]    # "暂停前状态="
    if prefix and value.startswith(prefix):
    return value    # 已带前缀，直接用
    return tpl.format(value)
```

C-05 V08 多维实体的状态机被最后一个维度覆盖，前置维度静默跳过校验

```txt
位置：verify/checks/v08_phase_consistency.py:206-223
```

```txt
验证：代码路径推演（行号可抽查）
```

问题。构建状态机字典时以实体名为 key 在维度循环内反复赋值，同名 key 直接覆盖。

coverage_obligations.json 中实体 E-XM（项目）具有 ['项目状态', '项目阶段'] 两个维度，循环结束后 machines["项目"] 只保留最后一个维度「项目阶段」，主链维度「项目状态」的终态相位、forward 单调性与坍缩检查全部静默丢失。

## 证据

```python
for ent, info in si.items():
    name = info.get("entity_name") or ent
    for dim in info.get("dimensions", []) or []:
    machines[name] = {...}    # 同名 key 反复覆盖
```

影响。V08 对最核心的主链状态机不设防，pass 结论可信度显著打折。

## 修复

```txt
machines.setdefault(name, {})[dim] = {...}
# 或 key 改为 f"{name}.{dim}", 同步调整失败证据中的 machine 字段
```

C-06 spec_lint 与 checks/base 的数据契约直接矛盾，自家 case_spec被判 8 个 error（实测复现）

```txt
位置：verify/spec_lint.py:74-81（对照 base.py:86-97 与 v04:52-62）
```

```txt
验证：实测复现（独立环境复现成功）
```

问题。lint_built_in 要求 readonly 条目为非空字符串，而 base.entity_names_of 与 V04 均明确支持 {"entity","clause","note"} 字典形态。实测 python -m verify.spec_lint -sverify/case_spec.json 报 8 个 error、退出码 1——而 spec_lint 的文档规定「每次修改

case_spec 后强制先跑本脚本再跑 validators」。

## 证据

```python
for ent in bi.get("readonly") or []:
    if not (isinstance(ent, str) and ent.strip()):
    rep.err("BI", f"readonly entity invalid: {ent!r}")
# base.py entity_names_of 明确处理 dict 条目；实测 spec_lint -> 8 errors
```

影响。评审者的评审者反而成为流程卡点：按规定的门禁流程走，自家合法 spec 直接被判死。同一份 schema 在三处（lint/base/V04）解释互不一致，是典型的契约漂移。

## 修复

```python
def _entity_name(ent) -> str:
    if isinstance(ent, dict):
    return str(ent.get("entity") or """).strip()
    return ent.strip() if isinstance(ent, str) else ""
for ent in bi.get("readonly") or []:
    if not _entity_name(ent):
    rep.err("BI", f"readonly entity invalid: {ent!r}") 
```

C-07 loop_manager 三处 subprocess超时未捕获，长跑编排器被一次挂起打死

```txt
位置：verify/loop_manager.py:174-175（agent, timeout=1800）、验证：代码路径推演（行号可抽查）257-258（pipeline, 3600）、268-269（smoke, 300）
```

问题。三处 subprocess.run 都设置了 timeout 但均未捕获 subprocess.TimeoutExpired。设计上 loop 需要无人值守自主运行 4 小时并区分 done/retry/escalated，而 LLM 或 Agent 一旦挂起，超时异常直接冒泡穿透 one_attempt 使整个 loop 进程退出。

## 证据

```python
proc = subprocess.run(cfg.agent_cmd, input=json.dumps(task, ensure_ascii=False), cwd=cwd, capture_output=True, text=True, timeout=1800)
# 无 try/except subprocess.TimeoutExpired
```

影响。一次网络抖动或模型卡顿即可终止整个无人值守循环，与自主运行的设计目标相悖。

## 修复

```python
try:
    proc = subprocess.run(..., timeout=1800)
except subprocess.TimeoutExpired:
    history.append({"stage": "agent", "result": "timeout"})
    return "retry"    # 或按预算返回 "escalated"
```

```txt
sys.exit(2)    # 三条 fatal 路径
# validate_p2.py 末尾追加:
sys.exit(1 if errors else 0)
```

C-08 P2 三条 fatal 路径退出码为 0，validate_p2报错也不设退出码——门禁不 gate

```javascript
位置：context/generate_obligation_model.py:199,217,2946; context/verify/validate_p2.py:293-313
```

```txt
验证：代码路径推演（行号可抽查）
```

问题。generate_obligation_model.py 的缺必备节点、preconditions 未结构化、self_check失败三条 fatal 路径全部 print JSON 后 sys.exit(0)，与 :71-73 用法错误时退出码 1 自相矛盾；validate_p2.py 即使发现 20+ 条 error 也正常退出，全文件唯一的 sys.exit(1) 在 usage 提示分支。

## 证据

```python
out = {"_context": {"fatal_error": "缺少必备节点", ...}}
print(json.dumps(out, ensure_ascii=False, indent=2))
sys.exit(0) # fatal 却返回成功
# validate_p2.py 末尾：print(f"Errors: {len(errors)}") 后直接结束
```

影响。任何 CI 或脚本用 $? 判断都会把致命错误当成功，错误产物继续流入 P3。整个质量闸门的实际拦截力远低于其表面积给人的信心。

## 修复

## C-09 P1 required 校验死分支：空列表/空字典绕过必填检查

```txt
位置：srs_pipeline/schema.py:332-336（同型 bug 复制于 validate.py:355-361）
```

验证：代码路径推演（行号可抽查）

问题。required 分支中，isinstance(val, (list, tuple, dict)) 成立时再判断 val is None ——永假（能进入该分支 val 必非 None）；空列表 [] 不满足 elif 条件，直接通过。子代理实测add_permission(role="r01", operations=[]) 校验通过，六个版本数据中共 12 处operations=[] 依赖此漏洞通过校验。

## 证据

```python
if required:
    if isinstance(val, (list, tuple, dict)):
    if val is None:    # 死代码：进入此分支 val 必非 None
    raise ValueError(...)
    elif val in (None, ""):
    raise ValueError(...)
```

影响。必填的列表/字典字段传空值静默通过，P1 真源可携带空操作集并流入下游建模。

## 修复

```python
if required:
    if isinstance(val, (list, tuple, dict)):
    if not val:
    raise ValueError(f"[schema:{otype}] 必填参数 {dsl!r} 为空")
    elif val in (None, ""):
    raise ValueError(...)
```

## C-10 LLM 客户端 async 壳 + 同步 urllib 芯：事件循环被完全阻塞

```javascript
位置：tools/llm/client.py:169-245, 247-336（配合tools/llm/http_utils.py:202）
```

验证：代码路径推演（行号可抽查）

问题。async def chat()/chat_json() 内部直接调用同步阻塞的 call_llm_api，后者用urllib.request.urlopen 实现、timeout 最长 180 秒。事件循环在请求期间被完全占用，async只是签名上的假象：任何 asyncio.gather 并发实际串行，且无法取消。

## 证据

```python
async def chat(self, messages, ...):
    ...
    response = call_llm_api(...)  # http_utils 内为 urllib.urlopen 同步阻塞
```

影响。并发调度退化为串行、无法超时取消；调用方基于 async 签名做出的并发假设全部失效。

## 修复

```python
async def chat(self, messages, **kw):
    return await asyncio.to_thread(
    call_llm_api, api_base=self._api_base, api_key=self._api_key,
    model=self._model, messages=messages, **kw)
# 或整体改用 httpx.AsyncClient; 若无意支持并发，删去 async 避免误导
```

## C-11 指数退避参数声明但从未实现，配置体系提供假开关

```txt
位置：tools/llm/http_utils.py:171,185,214-227（配合config.py:222-228、task_types.py:47-48）
```

验证：代码路径推演（行号可抽查）

问题。call_llm_api 的 backoff_factor 参数有签名、有 docstring，但函数体从未使用—docstring 自己承认 Unused。429 固定 sleep(rate_limit_wait)、其他错误固定 sleep(2)，而 config.py 与 task_types.py 都向用户暴露 retry_backoff_factor=2.0 配置项。

## 证据

```python
def call_llm_api(..., backoff_factor: float = 2.0):
    """... backoff_factor: Unused - kept for API compatibility"""
...
time.sleep(2) # 固定退避，与配置无关
```

影响。对 5xx 抖动无退避，重试 3 次每次固定 2 秒，高负载下加剧限流；用户调节 backoff 配置项完全无效。

## 修复

```txt
delay = base_wait * (backoff_factor ** attempt)
time.sleep(min(delay, 60))
# 或删除 config 中的 retry_backoff_factor 字段，避免假配置
```

## C-12 DEP_CONFIDENCE 双表硬编码，未注册 origin 置信度归 0被优先剪除

```txt
位置：tools/graph_algo.py:81-93与
nodes/s3_dependency.py:63-75（:96归0）
```

验证：代码路径推演（行号可抽查）

问题。同一张依赖置信度表在两处各自维护，graph_algo.py:78-80 注释自认「双表同步是已知维护陷阱，详见 DECISIONS」。_confidence 对未注册 origin 返回 0——恰是全局最低值，会在同类别候选中排序最靠前被优先剪除。

## 证据

```python
# graph_algo.py:78-80
# 2026-08-14: co_enabler_both_lateral / co_enabler_phase_inversion 必须同时注册——
# 缺失任一都会 conf 归 0 ... 双表同步是已知维护陷阱
def _confidence(origin): return DEP_CONFIDENCE.get(origin, 0)
```

影响。已经为缺注册付出过一次实错代价（注释可证）；新业务接入新 origin 字符串时，authoritative 边可能被静默剪掉，且无任何告警。

## 修复

```python
# nodes/s3_dependency.py 是依赖方，graph_algo 被其导入 -> 延迟导入破坏：
def _confidence(origin):
    from nodes.s3_dependency import DEP_CONFIDENCE  # 单一事实源
    conf = DEP_CONFIDENCE.get(origin)
    if conf is None:
    warnings.append(f"break_cycles: unknown dep origin {origin!r}, treat as 0")
    return 0
    return conf
```

## 第五章 Major 级问题（P2）

本章 14 项 Major 级发现以「会产生错误数据但不崩溃」与「结构性复制漂移」为主。它们集中体现了两个模式：一是文本解析与启发式匹配的边角失效（M-01、M-02、M-07），二是演进过程中被注释、被绕过、被复制后未收敛的半成品（M-03、M-08、M-12）。每项给出定位、证据与修复要点，修复代码从简。

## M-01 前置状态解析的箭头链首段产生垃圾值（实测复现）

```txt
位置：nodes/s3_dependency.py:97-129
```

验证：实测复现（独立环境复现成功）

问题。docstring 声称输入「报名记录样品状态推进(待发样->待收样->已收样)」应输出 [待发样,待收样, 已收样]，实测输出为 [报名记录样品状态推进(待发样, 待收样, 已收样]——箭头拆分后首段的「(」前前缀未被剥离，括号位于串中间而非首尾。

## 证据

```javascript
chunk = re.sub(r'^[()+\s*', '', chunk) # 只剥首部括号
chunk = re.sub(r'\s*[]]*$', '', chunk) # 只剥尾部括号
# 实测：['报名记录样品状态推进(待发样', '待收样', '已收样']
```

影响。Guard 6 的正则回退路径携带垃圾状态值参与精确匹配：多数情况无命中造成无效遍历；若某 post_state 恰含「(」则可能伪命中生成错误依赖边。

修复要点。先按 '(' 切分再走箭头拆分：normalized 先 split('(')，对最后一段做箭头解析，或对每个 chunk 先 strip() 掉未闭合的 '(' 及其左侧全部文本。

## M-02 Guard 6 与 _resolve_to 的分支后缀处理不一致，且循环内 O(n)查表

```txt
位置：nodes/s3_dependency.py:749-751（对照:161-175的_resolve_to）
```

验证：代码路径推演（行号可抽查）

问题。弱依赖路径通过 _resolve_to 解析 source_id，会剥离 T-015a 形态的分支后缀再查表；Guard 6 路径却用 next((t for t in tos_all if t.get('id')==sid), None) 精确匹配，既不剥后缀也在双层循环内做 O(n) 线性查找。

## 证据

to = next((t for t in tos_all if t.get("id") == sid), None) # O(n)，不剥后缀# 而 :168 已有 to_by_id + 正则剥后缀的 _resolve_to

影响。T-015a 等分支变体的 source_id 拿不到结构化前置引用，guard6 依赖整段缺失；规模增大时性能按平方退化。

修复要点。统一改用 to_by_id.get(sid) or to_by_id.get(re.sub(r'[a-z]$', '', sid))，与_resolve_to 保持同一事实源。

M-03 S3 死代码三处：失效的容量常数、未使用的变量、自认 no-op 的Guard 2

```txt
位置：nodes/s3_dependency.py:624、744-745、679-695
```

```txt
验证：代码路径推演（行号可抽查）
```

问题。_GUARD1_MAX_PREDS = 3 定义后从未被读取（:673 注释明确说明已被按 (from,to) 去重取代，但 :618-623 的说明注释仍在描述 cap 机制）；Guard 6 开头计算的 primary_entity 与primary_dim 两个变量赋值后从未使用；Guard 2 整段被注释标记为 no-op 保留。

## 证据

```python
_GUARD1_MAX_PREDS = 3 # max predecessors per from_state (后文再未出现)
primary_entity = phase_table.get('primary_entity', '') ... # 从未使用
```

影响。注释与实现互相矛盾，误导维护者以为存在双重上限保护。

修复要点。删除三处死代码；如需保留 Guard 2 作为文档，移入注释块而非可执行函数体。

M-04 S4 死 no-op：嵌入 BR 与实例数的关联逻辑从未实现

```txt
位置：nodes/s4_multi_instance.py:188-190 验证：代码路径推演（行号可抽查）问题。if has_embedded_brs and count <= 1: count = 1——条件为真时赋值不改变任何状态，整段语句无任何效果。从上下文看，原意可能是「嵌入 BR 的宿主需要强制多实例」或相反，但两个方向都未实现。
```

## 证据

```python
has_embedded_brs = bool(proc.get("embedded_brs", [])) if has_embedded_brs and count <= 1:
    count = 1    # no-op 
```

影响。行为与注释意图脱节；后续维护者会误以为嵌入 BR 已参与实例数决策。

修复要点。删除该段；若产品语义要求嵌入 BR 强制展开，补全真实逻辑并加测试。

M-05 S4 Type7 的 first_entity 被后续 source_ids反复覆盖，最后匹配者胜出

```txt
位置：nodes/s4_multi_instance.py:159-177
```

验证：代码路径推演（行号可抽查）

问题。注释说明实例数取 BR.entities_involved[0]，但循环对每个 source_id 的每个匹配 RO 都会覆写 first_entity，break 只跳出内层循环——过程引用多个 RO 时取的是最后一个匹配项，与「first」语义相反。

## 证据

```python
for sid in proc.get("source_ids", []):
    for ro in ros_flat:
    if ...:
    first_entity = name_to_id.get(first_raw, first_raw)
    break  # 只跳出内层
count = entity_instances.get(first_entity, 1)
```

影响。多源 Type7 用例的实例数取决于 source_ids 的排列顺序，行为不确定且难以复现排查。

修复要点。命中后置标志位并 break 外层循环（for-else），确保只取第一个匹配的 RO。

## M-06 S0 模块级 _ACTION_KEYWORDS 跨运行污染

```txt
位置：nodes/s0_topology.py:3131-3138
```

```txt
验证：代码路径推演（行号可抽查）
```

问题。节点函数内通过 global 覆盖 _ACTION_KEYWORDS，但仅当 coverage_model 携带action_keywords 时才更新——不携带时沿用上一次运行的旧值。在同一进程内多次运行流水线（loop_manager、测试、replay 脚本）时，前一次的领域词表会渗透到后一次。

## 证据

```python
global _ACTION_KEYWORDS
_ak = _ctx.get('action_keywords', {})
if _ak and isinstance(_ak, dict):    # 缺失时保留旧值
    _ACTION_KEYWORDS = {...}
```

影响。破坏「同一输入同一输出」的确定性承诺，复现与回归对比时出现幽灵差异。

修复要点。每次节点入口先重置为默认词表，再按 cm 覆盖；或把词表放入 state 而非模块全局。

## M-07 S1 去重 Branch A 丢弃被并方的 Then，存在覆盖丢失风险

```txt
位置：nodes/s1_generation.py:4005-4021
```

```txt
验证：代码路径推演（行号可抽查）
```

问题。「完全重复」分支只合并 source_ids 并保留 thens 较多的一方，被并方的 thens 直接丢弃；但重复判定只比较 entity/dim/post_state/分支 givens/动作文本，并不比较 thens 内容——两者 thens 完全可能不同。同函数的 Branch B/C 反而都按 expectation 去重合并 thens，行为不一致。

## 证据

```python
if (same_entity and same_dim and similar_action
    and p1["post_state"] == p2["post_state"]):
    if len(p1 thens) >= len(p2 thens):
    p1["source_ids"] = ...（只并 source_ids）
    to_remove.add(p2["temp_id"])  # p2 的 thens 丢失
```

影响。若被并方的某条 Then 携带独有 BR 断言，V10 覆盖矩阵将出现无法归因的缺口。

修复要点。Branch A 与 B/C 对齐：按 expectation 去重合并双方 thens 后再移除被并方。

M-08 S1 的 LLM 能力整体停用为死代码，注释宣称的能力不存在

```txt
位置：nodes/s1_generation.py:4353-4366（波及_decompose_brs_via_llm:3149、generate_signal_v_steps 等）
```

验证：代码路径推演（行号可抽查）

问题。BR 分解被 TEMP 注释硬编码为空字典（理由是 63 条 BR 太慢），信号 V 步生成被TODO 注释停用，signal_v_steps={} 硬编码传入下游。约百余行的 LLM 分解/生成链路成为死代码，if br_decomp: 的警告分支永不执行。

## 证据

```python
# TEMP: skip BR decomposition (LLM call too slow for 63 BRs)
br_decomp = {}
state['br_decomposition'] = br_decomp
if br_decomp:    # 恒 False
    warnings.append(...)
# TODO: 注释LLM验证步骤生成,聚焦排序正确性验证
signal_v_steps = {}
```

影响。Type7 与 BR 嵌入实际运行在降级路径上；文档与 warning 系统暗示的能力并不存在。

修复要点。产品决断二选一：恢复调用并做批量/异步优化，或删除整条链路与相关 prompt、更新 readme。

## M-09 graph_algo 残环兜底静默排平，chain_depth 第三键恒 0 失效

```txt
位置：tools/graph_algo.py:255-259（残环）、148（chain_depth） 验证：代码路径推演（行号可抽查）
```

问题。break_cycles 无法破环时，topological_sort_procedures 把环内节点按 sort_key 强行排平，不产生任何告警——根因（环残留）只能靠下游 V01 的间接症状反推。同时候选排序的第三键 depth 取自 _S2_fields.chain_depth，而 S2 已不再产出该字段，恒为默认 0，v28 保留的「深度优先剪除」tiebreaker 实际失效。

## 证据

```python
if len(result) < len(procedures):
    remaining.sort(key=_sort_key); result.extend(remaining) # 无告警
depth = s2.get("chain_depth", 0) # 恒 0
```

影响。静默排平掩盖了环未破的真相；置信度相同边的剪除顺序退化为不稳定状态。

修复要点。残留时把 temp_id 列表写入返回的 warnings；删除 chain_depth 维度或恢复其产出。

## M-10 fallback_log.record 对未知 site 直接raise，观测组件反成稳定性炸弹

```txt
位置：tools/fallback_log.py:181-185
```

验证：代码路径推演（行号可抽查）

问题。record() 在 site 不在注册表时抛 ValueError，而 record_fallback 被嵌入 s0/s1/s3/p2 的fallback 分支调用。新增一个降级点忘记注册、或 site 字符串拼写错误，都会让生产流水线在「降级路径」上崩溃。

## 证据

```python
if site not in FALLBACK_SITES:
    raise ValueError(f"unknown fallback site: {site!r}") 
```

影响。可观测性组件反而成为主链路稳定性风险，与「记录降级」的职责背道而驰。

修复要点。生产模式降级为 print + 计数，仅测试模式（环境变量开关）raise；或 site 改用Enum 在开发期发现问题。

## M-11 缓存管理器声称线程安全但无锁、写入非原子

```txt
位置：tools/llm/cache.py:29（docstring）、194-221（save） 验证：代码路径推演（行号可抽查）
```

问题。类 docstring 标注 Thread-safe operations，但全文件没有任何锁；save() 直接open('w') + json.dump 非原子。main.py 的标题生成使用 ThreadPoolExecutor 并发调用（若走带缓存的客户端），存在并发写坏文件的真实场景。

## 证据

```python
with open(cache_file, 'w', encoding='utf-8') as f:
    json.dump(cache_entry, f, ...) # 非原子，可被并发读撕裂
```

影响。并发写产生半截 JSON；load 读到坏文件静默当 miss，竞态反复发生且难复现。

修复要点。写临时文件后 os.replace 原子替换；跨进程场景加文件锁（fcntl/portalocker）；或删除 docstring 中的线程安全声明。

M-12 TitleGenerator 三份平行实现，JSON 修复逻辑三处复制且已漂移

```txt
位置：tools/llm_client.py:160-310 vs tools/llm/client.py:396-544 vs tools/llm/http_utils.py:27-48
```

验证：代码路径推演（行号可抽查）

问题。旧版 TitleGenerator、新版 LegacyTitleGeneratorWrapper（名为包装实为逐行复制）、以及 http_utils 各自实现一套 markdown 剥壳/JSON 修复。client.py:516 仍用 find 索引裸取，而 llm_client.py:148 已修过同类问题——注释可证的修复漂移史。

## 证据

```python
class LegacyTitleGeneratorWrapper: # 名为 Legacy，实为唯一被 main.py 使用 _build_steps_text = ... # 与旧版逐行同构
# JSON 修复：llm_client.py:144-156 / client.py:513-524 / http_utils.py:27-48
```

影响。修一处漏两处的经典结构；新旧客户端行为不一致（缓存、重试、解析各有差异），排查成本高。

修复要点。删除 LegacyTitleGeneratorWrapper 与旧版，收敛到 tools/llm/client.py 单实现；JSON 修复只保留 http_utils._repair_json。

## M-13 schema 校验细节三连：given_type 无枚举、I19禁语可绕过、泛捕获异常

```txt
位置：models/schema.py:193、315-328、455
```

验证：代码路径推演（行号可抽查）

问题。given_type 是裸 str，注释列出 8 个合法值却无 Literal 约束，拼写漂移静默通过并使渲染分流走错分支；I19 禁语黑名单用精确等值匹配，「查看效果。」带标点即可绕过；

validate_procedures 捕获 Exception，把 TypeError 等编程错误归入数据错误清单，掩盖真实bug。

## 证据

```python
given_type: str = "state"    # 应为 Literal
if then.expectation in forbidden_expectations  # 精确等值
except Exception as exc: errors.append(...)  # 过宽
```

影响。三类问题共同削弱 schema 层作为「强校验不变量」的承诺。

修复要点。given_type: Literal["state","flow","constraint","branch","rule","rule_noise","restatement","field_data","event"]；匹配前 strip().rstrip('。')；只捕 pydantic.ValidationError。

## M-14 状态池无 reducer、失败静默 END、主流程退出码恒 0

```txt
位置：models/state.py:73-75; graph.py:21-25; main.py:297-306
```

验证：代码路径推演（行号可抽查）

问题。warnings/errors 是普通 list 字段，无 Annotated[..., operator.add] 归约器，LangGraph 并行/重试语义下任一节点返回自己的告警就会覆盖前序累积（s1_fix_replay.py:318 手工合并 warnings 正是该缺陷的绕过证据）；should_continue_after_s1 只看 procedures 是否为空，errors 非空也照常走向下游直至正常END；main.py 末尾有 errors 也退出 0。

## 证据

```txt
warnings: list[str] # 无 reducer
errors: list[str]
# graph.py: proc 为空 -> END，不看 errors
# main.py: if errors: print(...) 之后正常 return，进程退出码 0
```

修复要点。warnings/errors 声明为 Annotated[list[str], operator.add]；s1~s4 增加检查errors 的条件边；main.py 末尾 sys.exit(1 if errors else 0)。

## 第六章 Minor 级问题（P3）

本章 36 项 Minor 级发现按模块归组列出，每项包含定位与问题概述；对其中 4 项给出代表性修复代码。这些问题单个影响有限，但叠加起来决定了日常维护的摩擦系数——尤其是重复实现与死分支两类，建议随批次清理而非单独开票。

## verify/ 门禁（12 项）

<table><tr><td>编号</td><td>位置</td><td>问题概述</td></tr><tr><td>P-01</td><td>oracles.py:75-78</td><td>R-001 防御分支不可达(WEIGHT_TABLE 限定下 trimmed 恒非空),死代码+误导注释</td></tr><tr><td>P-02</td><td>oracles.py:39,205</td><td>手机号正则 ^...$ 接受尾随换行,脏字符可通过;改 re.fullmatch</td></tr><tr><td>P-03</td><td>spec_lint.py:57-59,103-110</td><td>guard_id 唯一性检查重复实现两遍(GP/ID 两类各一份),同违例报两次</td></tr><tr><td>P-04</td><td>v09_dedup_instances.py:16 vs validators.py:60-62</td><td>去重口径不一致:V09 含 entity、metrics 不含,dedup_ratio 与结论可能背离</td></tr><tr><td>P-05</td><td>loop_manager.py:128-129,80-81</td><td>quality_history.jsonl 一行损坏即崩;config 未知键 TypeError;应逐行容错</td></tr><tr><td>P-06</td><td>loop_manager.py:389</td><td>dry_run 下快照不回收(worktree/mkdtemp 泄漏);wt.discard() if ... else None 表达式语句坏气味</td></tr><tr><td>P-07</td><td>code_agent_cli.py:455-457</td><td>--task-file 缺参数裸崩 IndexError,应改 argparse</td></tr><tr><td>P-08</td><td>code_agent_cli.py:505</td><td>lstrip("./") 按字符集误剥:../secret 变 secret,白名单匹配错位;应 removeprefix("./")</td></tr><tr><td>P-09</td><td>code_agent_cli.py:411-415</td><td>SEARCH/REPLACE 只替换首处,未按 SYSTEM_PROMPT 强制唯一性,多命中时静默改错位置</td></tr><tr><td>P-10</td><td>v08_phase_consistency.py:31,271</td><td>STRICT_FORWARD 恒真死分支;相位坍缩判定在部分命中时误报</td></tr><tr><td>P-11</td><td>checks/base.py:71-73</td><td>normalize_text 全局去空白使相邻 givens 粘连,可拼出从未同时出现的文本伪命中</td></tr><tr><td>P-12</td><td>v01_dependency_closure.py:12-27</td><td>_is_dag 对边中未注册节点抛 KeyError,契约无文档保护</td></tr></table>

## nodes/ P3 核心（1 项）

<table><tr><td>编号</td><td>位置</td><td>问题概述</td></tr><tr><td>P-22</td><td>main.py:293,475-491</td><td>md_path 用 replace(&quot;.json&quot;) 对无后缀输出失效;429 时 sleep 在 worker 内并不能暂停其他提交;remaining 计数近似</td></tr></table>

## context/ P2（5 项）

<table><tr><td>编号</td><td>位置</td><td>问题概述</td></tr><tr><td>P-18</td><td>generate_obligation_model.py:1384等</td><td>循环体内重复 import itertools/os (S1 的 :1870 同病)</td></tr><tr><td>P-19</td><td>generate_obligation_model.py:126-127,180-181</td><td>except Exception: pass / return None 全吞,无法区分未配置与配置错误</td></tr><tr><td>P-20</td><td>generate_obligation_model.py:2979-2988</td><td>兜底词表内联 24 个动作词,与「不硬编码业务词汇」的自我声明矛盾</td></tr><tr><td>P-25</td><td>generate_obligation_model.py:1276-1283</td><td>R5 组合过滤中文子串碰撞:合格是不合格的子串导致冲突漏检;P1 已有 _value_hit 防护未复用</td></tr><tr><td>P-26</td><td>generate_obligation_model.py:1209,1839,2861</td><td>假保险三连:has_real_difference 定义未调用、G1 检查体只有 pass、self_check 两项恒真</td></tr></table>


srs_pipeline/ P1（5 项）


<table><tr><td>编号</td><td>位置</td><td>问题概述</td></tr><tr><td>P-13</td><td>model.py:490</td><td>分支差异 XC 的 coverage 前缀匹配与 desc 模板不一致(分支[name= vs 分支[name]),条件恒空</td></tr><tr><td>P-14</td><td>model.py:33-34 与 generate_obligation_model.py:2993</td><td>UTC+8 时区逻辑两份实现</td></tr><tr><td>P-15</td><td>validate.py:200-212</td><td>校验器带副作用:边校验边删模型数据,输出正确性依赖同一对象引用的隐式别名契约</td></tr><tr><td>P-16</td><td>validate.py:90-105</td><td>校验码编号缺口 C15/C19,检索产生幽灵空洞</td></tr><tr><td>P-17</td><td>evidence.py:12 vs signals.py:8,94,12</td><td>限制词表两份内容漂移(evidence 缺仅当/不能/只允许);同文件两份逐字相同的标题正则</td></tr></table>

## tools/（2 项）

<table><tr><td>编号</td><td>位置</td><td>问题概述</td></tr><tr><td>P-23</td><td>scripts/llm_e2e_check.py:243</td><td>API key 前 8 后 4 共 12 字符打印到控制台,配合已入库的完整 key 降低熵</td></tr><tr><td>P-24</td><td>data_access.py:57-71,114-129</td><td>双位置合并不去重;__main__ 自测硬编码外部绝对路径(死代码)</td></tr></table>


scripts/（2 项）


<table><tr><td>编号</td><td>位置</td><td>问题概述</td></tr><tr><td>P-28</td><td>scripts/regression_baseline.py:28,35</td><td>PROJECT_DIR 指向另一项目 project_v28、python 指向 /home/z/.venv,黄金回归实为摆设;应以__file__锚定 + sys.executable</td></tr><tr><td>P-29</td><td>fill_pt017_to_excel.py:25-26 与 sync_md_to_ai_excel.py:32-64</td><td>Windows 个人桌面路径硬编码;30 行 MD 解析逻辑整段复制</td></tr></table>


srs_data/（2 项）


<table><tr><td>编号</td><td>位置</td><td>问题概述</td></tr><tr><td>P-21</td><td>srs_data/utf8.py:1-11</td><td>引用已不存在的 pt_srs.py、依赖 CWD 的相对路径、literal_eval 裸奔——遗弃一次性脚本</td></tr><tr><td>P-27</td><td>pt_srsv6/v8/v10 全文件</td><td>三个版本与当前校验器不兼容(assemble 直接 CriticalAmbiguity 中断),v10/v11 甚至未纳入 git 跟踪</td></tr></table>

## 工程规范（7 项）

<table><tr><td>编号</td><td>位置</td><td>问题概述</td></tr><tr><td>P-30</td><td>git 历史</td><td>62 个提交 46 个叫 fix,另有 妈呀/我靠/我的妈呀 三条情绪化提交,无法 bisect 定位</td></tr><tr><td>P-31</td><td>.ab_tmp/</td><td>44MB、77 个文件的临时备份区被 git 跟踪(81 个条目),git status 长期一片 modified</td></tr><tr><td>P-32</td><td>依赖声明</td><td>无 requirements.txt/pyproject.toml/setup.py,networkx/pydantic/langgraph 全靠环境碰巧存在</td></tr><tr><td>P-33</td><td>tests/</td><td>唯一真实测试文件 test_branch_tt_backfill.py(21个test_)未被git跟踪;graph_algo/llm/schema/nodes零单测</td></tr><tr><td>P-34</td><td>.gitignore</td><td>未覆盖.ab_tmp/、config.json(密钥)、PT017_output.*等产物,形同虚设</td></tr><tr><td>P-35</td><td>根目录数据堆积</td><td>pt_structuredv6~v11.json六代同堂588KB全部跟踪,v8/v10为中间态残片</td></tr><tr><td>P-36</td><td>异常处理面</td><td>except Exception 35处、纯吞5处(s0:647,2192、s1:3177,4153、P2:126),集中在主生成路径</td></tr></table>

## 代表性修复示例

## P-02 手机号校验（oracles.py）

```txt
PHONE_RE = re.compile(r"1[3-9]\d{9}")
return bool(PHONE_RE.fullmatch(str(phone or ""))) # fullmatch 拒绝尾随换行
```

P-05 历史文件逐行容错（loop_manager.py）

```python
records = []
for line in self.path.read_text(encoding='utf-8').splitlines():
    if not line.strip():
    continue
    try:
    records.append(json.loads(line))
except json.JSONDecodeError:
    continue  # 跳过坏行，可选：计数并告警
```

P-08 路径前缀剥离（code_agent_cli.py）

```txt
p = fe["path"].replace("\\", "/")
p = p[2:] if p.startswith("./") else p # 或 p.removeprefix("./")
fe["path"] = p # ../secret 不再被误剥成 secret
```

## P-11 givens 归一化粘连防护（checks/base.py）

```python
def _givens_text(givens):
    parts = [normalize_text(g.get("state")) + normalize_text(g.get("description"))
    for g in givens]
    return "\x01".join(parts) # 逐条归一化后用安全分隔符连接，杜绝跨条目粘连
```

## 第七章 架构级坏气味专题

把 68 项细目放回架构视角，可以看到六条反复出现的结构性模式。它们不是孤立 bug，而是演进方式的必然产物：功能以复制和旁路的方式生长，旧路径不删除、新路径不收口。逐条修复细目只能止血，只有处理这六个模式才能阻止同类问题再次产生。

## A1 巨石文件与「脚本/模块双重人格

三个核心文件分别达到 4428 行（nodes/s1_generation.py）、3352 行（nodes/s0_topology.py）、3049 行（context/generate_obligation_model.py）。其中 P2 脚本的全部业务逻辑（Step0-6 循环、文件读写、sys.exit）都在模块顶层，没有 main() 守卫——它既不能被 import（一 import 就跑流水线、写文件甚至退出进程），也不能被单测。同一文件里try: import co_derivation / except: from context import co_derivation 的双形态导入兼容说明作者意识到包化需求，但没有走完。与之对照，context/constraint_fields.py 同为 905 行却全函数化、注册表自校验、fail-fast，证明同等规模完全可以写得可测。

## A2 「单一事实源」口号与系统性复制漂移

项目文档多处宣称 single source of truth，共享模块（co_derivation、time_control、sysfields）也确实做得好，但存量路径的复制粘贴已成体系：_givens_text 在 v02/v05 逐字重复；_bigrams 两份实现且相似度口径一个 Jaccard≥0.5、一个 containment≥0.4；DEP_CONFIDENCE 双表靠注释维持同步且已实错过一次；限制词表三份内容漂移；no_branch 规则生成器/校验器双实现；sort_key 的维度数在 s2 docstring（10 维）、s2 注释（8 维）、graph_algo docstring（7 维）与实际代码（6 维）之间四 nowhere 对齐；TitleGenerator 三份实现。防漂移机制只覆盖了新写的共享模块。

## A3 复制即版本管理（数据层）

srs_data 的 pt_srsv6~v11 六个 2000+ 行数据文件中，v6 与 v7 相同率 97.4%（diff 仅 67 行）、v10 与 v11 相同率 98.7%（diff 仅 23 行——恰是 v10 assemble 失败的修复补丁）；v6/v8/v10三个版本在当前校验器下 assemble 直接中断，属于跑不通的死数据；v10/v11 甚至未被 git 跟踪。根目录 pt_structuredv6~v11.json 六代同堂。这个项目的「历史」存在文件系统里而不是 VCS里。建议数据外置 JSON、版本用 tag 管理，死版本移入 _archive 或删除。

## A4 门禁不独立，依赖反向倒挂

verify/ 作为骨架门禁本应只依赖标准库与 JSON，实际 v03/v07/v08 顶层导入models.schema 连锁拖入 langgraph 与 langchain_core（实测干净环境整机崩溃），v04/v06/v07 又依赖 context/* 生成器模块。一个 IntEnum 常量就把门禁绑死在主流水线运行时上，run_all 的 per-check 容错因 import 在 try 外而形同虚设。修复方向已在 B-03 给出：常量下沉 + 导入隔离，让门禁在裸 Python 环境可跑。

## A5 自优化循环：周边精细、核心空洞

loop_manager 的周边工程（失败签名去重、同 diff 拒绝、预算熔断、升级报告）做得相当细致，但「修复如何存活」这一核心问题在两个执行模式下都不成立（B-04 合并必失败、B-05 修复随快照丢弃）。同样，validate_p2 拥有 25+ 条规则但退出码恒 0（C-08），self_check 两项恒真（P-26）——闸门的表面积越完善，越掩盖其拦截力的空洞。建议先把闭环打通并加端到端验收用例，再继续增设周边机制。

## A6 演进式重构烂尾

tools/llm_client.py 自称 Deprecated、tools/llm/ 自称 unified，但主链路 main.py 仍在用旧版，新版又存在缓存 key Blocker——迁移做了一半，两头都不是完全面貌。类似地：S1 的LLM 分解/V 步功能被 TEMP 注释停用成死链（M-08）；S2 sort_key 精简后三个文档层未同步（M-09/A2）；fallback_report 的注释自陈「当前必然全站降级，这正是测量的意义」——观测点预留了，治理动作没有跟上。每一条半途迁移都应给出完成或回滚的决断。

## 第八章 工程规范专题

工程规范层面的发现集中在五个维度：密钥管理、Git 卫生、可复现性、测试资产与路径可移植性。其中密钥问题已在 B-01 详述，其余如下。总体而言，这是一个单人快迭代、产物即仓库的项目：git 被当成更可靠的复制粘贴使用，环境本身不可迁移，唯一有内容的测试文件没有进版本库。

<table><tr><td>维度</td><td>现状</td><td>证据与影响</td><td>整改建议</td></tr><tr><td>Git 卫生</td><td>62 提交中 46 个 fix,3 条情绪化消息</td><td>无法 bisect/review;.ab_tmp 44MB/77 文件入库且长期 modified</td><td>Conventional Commits; git rm -r --cached .ab_tmp 并补 .gitignore</td></tr><tr><td>可复现性</td><td>零依赖声明</td><td>无 requirements.txt/pyproject; langgraph/pydantic/networkx 靠环境碰巧存在;结合 6 处硬编码路径,换机即不可运行</td><td>补 requirements.txt 锁版本,建议升级 pyproject.toml</td></tr><tr><td>测试资产</td><td>核心层零单测</td><td>tests/ 仅 1 个文件且未被 git 跟踪(git ls-files tests/ 为空);graph_algo/llm/schema/nodes 无任何单测</td><td>tests/ 入库;优先为 graph_algo、cache、schema 补契约测试</td></tr><tr><td>路径可移植性</td><td>6 处机器硬编码 (Win 2 + Linux 4)</td><td>fill_pt017_to_excel.py:25-26 (C:\Users\15831\Desktop...); regression_baseline.py:28,35(指向另一项目 project_v28 与 ~/.venv);run_pipeline.py:6 ; data_access.py:117</td><td>统一 Path(__file__) 锚定 + CLI 参数;回归脚本用 sys.executable</td></tr><tr><td>异常卫生</td><td>except Exception 35 处、纯吞 5 处</td><td>吞异常点集中在 S0/S1 主生成路径(s0:647,2192、s1:3177,4153),失败被静默跳过后仅由下游校验间接兜底</td><td>纯吞点改为带计数的告警记录; except 收窄到预期异常类型</td></tr><tr><td>敏感信息</td><td>key 三处暴露面</td><td>两把明文 key 入库(B-01);llm_e2e_check.py:243 打印 12 字符</td><td>吊销轮换 + 历史清洗 + 全程 mask</td></tr></table>


表 4：工程规范维度审查结论


## 第九章 修复路线图

修复应按「先止血、再正本、后强身」的顺序推进。第一批处理安全与进程可见性，全部是小改动，合计约半天工作量，但消除的是全项目最大的两类风险；第二批集中修复已复现与门禁失效类正确性问题，使 Gate-S 与覆盖索引重新可信；第三批处理结构性坏气味，防止同类问题复发。每批均给出验收标准，便于逐项核销。

## 第一批：立即执行（当天，约 0.5 天）

<table><tr><td>任务</td><td>关联问题</td><td>验收标准</td></tr><tr><td>吊销并轮换两把 API key, git filter-repo 清洗历史,配置改环境变量</td><td>B-01</td><td>新 key 不出现在仓库任何提交中; CI 用环境变量注入</td></tr><tr><td>run_pipeline.py 删除破坏性逻辑与硬编码路径</td><td>B-06</td><td>脚本可在任意机器仓库内直接运行,config.json 不再被改写</td></tr><tr><td>P2 fatal 退出码 2; validate_p2 与 main.py 按错误置退出码</td><td>C-08、M-14</td><td>构造 fatal 输入时 $? 非 0, CI 能感知失败</td></tr><tr><td>required 校验死分支修复</td><td>C-09</td><td>add_permission(operations=[]) 被拒绝</td></tr><tr><td>git rm -r --cached .ab_tmp; .gitignore 补全;tests/ 入库</td><td>P-31、P-33、P-34</td><td>git status 干净; 克隆后测试目录存在</td></tr><tr><td>删除 run_pipeline 之外的 .bak 密钥备份</td><td>B-01 关联</td><td>仓库与工作区均无含 key 的备份文件</td></tr></table>


第二批：本周内（正确性）


<table><tr><td>任务</td><td>关联问题</td><td>验收标准</td></tr><tr><td>缓存 key 修复 + 通用 key 纳入 model/max_tokens</td><td>B-02</td><td>不同请求 key 不同;同请求跨模型不串缓存</td></tr><tr><td>门禁导入隔离:import 移入 try、ObligationType 下沉 base.py</td><td>B-03</td><td>裸 Python 环境跑通 10 项检查并产出 verdict</td></tr><tr><td>条款覆盖聚合改不动点传播</td><td>C-01</td><td>三级链用例全部 covered=True</td></tr><tr><td>V05 双修:exact 模式 + 前缀去重;V08 状态机按维度建 key</td><td>C-03/04/05</td><td>合成合法用例不再误报,pre_pause 组合可命中</td></tr><tr><td>spec_lint 与 base 契约对齐</td><td>C-06</td><td>对自家 case_spec 报 0 error</td></tr><tr><td>loop_manager 闭环重设计:合并用 HEAD SHA、agent 后复检、超时捕获</td><td>B-04/B-05/C-07</td><td>端到端演练一轮 retry 后合并成功</td></tr><tr><td>S3 Guard6 统一走 _resolve_to;状态解析修复首段垃圾</td><td>M-01/M-02</td><td>分支变体可获得 guard6 依赖;docstring 示例输出一致</td></tr></table>

## 第三批：迭代（可维护性）

<table><tr><td>任务</td><td>关联问题</td><td>验收标准</td></tr><tr><td>tools 层收敛:删 LegacyTitleGeneratorWrapper、缓存加锁原子写、fallback_log 降级</td><td>M-10/11/12</td><td>LLM 客户端单实现;并发压测无坏文件</td></tr><tr><td>单一事实源清理:置信度表合一、JSON 修复单实现、词表收敛、sort_key 文档对齐</td><td>A2 相关</td><td>grep 验证各字符串仅一处定义</td></tr><tr><td>P2 脚本 main() 化;S1/S0 巨石按职责拆分</td><td>A1</td><td>generate_obligation_model 可被 import 不产生副作用</td></tr><tr><td>死代码决断:BR 分解链路、Guard2、S4 no-op 等逐项删除或恢复</td><td>M-03/04/08</td><td>无 TODO/TEMP 挂起的死分支</td></tr><tr><td>补 requirements.txt/pyproject;核心层契约测试(graph_algo/cache/schema)</td><td>P-32、P-33</td><td>新机器按文档可复现环境;pytest 覆盖三个核心模块</td></tr><tr><td>Git 提交规范与数据版本治理(tag 化、死版本归档)</td><td>A3、P-30、P-35</td><td>提交信息可读;根目录仅保留最新一代数据</td></tr></table>

本次审查的 68 项细目与六个结构性模式已经全部给出定位、证据与修复方向，其中 5 项经过实测复现。需要强调的是，该项目并不缺少质量意识——C01~C31 校验矩阵、fail-closed 的共享派生模块、细致的失败签名路由都证明了这一点；真正需要调整的是演进方式：新路径落地时同步删除旧路径，共享事实源在新增消费方时先收敛再扩展，闸门的每一个判定都要有非零退出码作为进程级出口。按三批路线图推进后，建议以「干净环境跑通门禁、双跑 SHA 一致、fatal 必非零退出」三条作为长期的回归底线。