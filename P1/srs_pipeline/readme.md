srs_core/                  # 框架层：永久不变
├── escape.py              # esc
├── builders.py            # N / attr / op / precond / state_ref
├── model.py               # DomainModel：持有所有集合，提供 add_* 方法与 assemble()
└── validate.py            # Validator：全部结构校验

requirements/              # 数据层：每个需求一份
└── review_system.py       # 当前这份需求的数据定义（约1000行）

main.py                    # 入口：装配 → 输出 → 校验


python -m srs_pipeline.cli requirements_data.review_system -o review_system_structured.json
python -m srs_pipeline.cli requirements_data.xxx_system  -o xxx.json --strict   # 接 CI


扩展留给三个口子：新需求只需在 requirements_data/ 加一个数据文件；项目特有校验用 m.add_check(fn) 注册；prompt 本身升级（新枚举、新铁律）只改 constants.py 和 validate.py，不动任何数据文件。P2 阶段建议做的是把 C12 的 T-xxx 回填、C05 的穿透缺口提示做成自动修复，P3 再接 LLM 做文档解析与断点续传，需要时我可以继续往下写。