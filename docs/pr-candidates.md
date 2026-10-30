# PR 候选清单:从我们实测里长出来的贡献机会

> 原则:只提**亲手复现过**的问题;先搜 issue 避免重复;文档 PR 也要有数据支撑。
> 每个候选都标了证据、预期 PR 形态和提交前核对项。状态:☑=已核实可行 / ◐=提交前需再核对

## 候选 1:SGLang `bench_serving` 的 random 数据集强制下载 ShareGPT ☑ 已提 issue

- **进展**:2026-10-30 已提交 issue [sgl-project/sglang#47420](https://github.com/sgl-project/sglang/issues/47420)(含复现命令、根因定位到 `datasets/random.py` 的 random_sample 路径、三个修复方案)。
- **勘误**:此前调研引用的"#4133"经 gh 核实在仓库中不存在(搜索引擎给了坏链接)——教训:引用 issue 前必须 `gh issue view` 验证。防重复三搜 + main 分支源码核对(下载块仍在,`random-ids` 离线变体不可发现)均已完成,确认无人报过。
- **下一步**:等维护者表态选哪个方案 → 按其偏好提 PR(docs / actionable error / auto-fallback 三选一,修复思路已写在 issue 里)。

## 候选 2:vLLM Benchmark CLI 文档 ☑ base-url 部分已提 PR,prefix-cache 部分作废

- **勘误(2026-10-30)**:克隆 main 核对后发现,线上 latest 文档页(10-28 构建)滞后于 main——prefix-cache 污染的**成因与规避已有人在 main 写全**(vary `--seed`/restart/`vllm bench sweep serve`)。教训:线上文档有构建延迟,**提文档 PR 前必须核对 main 分支源文件**,而非线上页面。
- **已落地**:残留的干净增量 `--base-url` 勿带 `/v1` 后缀(全 benchmarking 目录零提及)→ PR [vllm-project/vllm#64698](https://github.com/vllm-project/vllm/pull/64698)(分支 `doc/bench-serve-base-url-note`,DCO 已签,含复现验证)。
- **后续**:跟进 CI 与 review,48h 无响应可礼貌 ping。

## 候选 3:vLLM 安装文档:受限网络环境的坑与解法 ◐

- **证据**(全部实测,见 [docs/环境报告.md](环境报告.md)):
  1. `flashinfer-cubin 0.7.x` 只在 flashinfer.ai 自建源,PyPI 镜像最高 0.6.13 → 国内拉取极慢且 `vllm download-kernels` 可能挂起
  2. 解法:`VLLM_USE_FLASHINFER_SAMPLER=0` 走 Triton 采样,或 conda 装 cuda 工具链(`-c nvidia`)+ `CUDA_HOME`/`LIBRARY_PATH` 共享(附完整命令)
  3. `VLLM_USE_PRECOMPILED=1` 在 main HEAD 可能报 "No published precompiled wheel within 20 commits" → 官方建议补充"checkout 最近 release tag 再装"
- **PR 形态**:docs 安装/故障排除章节新增 "Limited-connectivity environments (CN mirrors & flashinfer fallbacks)" 小节,英文撰写,只写通用解法不写主观评价。
- **提交前核对**:现有文档是否已有等价内容(搜 "flashinfer" "mirror" "precompiled");DCO 与文档 PR 模板要求。

## 提交任何 PR 前的固定动作( checklist )

1. `gh search issues/prs` + 仓库内搜关键词,确认无人做过(重复 = 社区噪音,伤的是自己账号)
2. 读目标仓 `CONTRIBUTING.md`(vLLM:DCO `git commit -s`、PR checklist、文档改动也要过 CI)
3. fork → `git checkout -b doc/bench-prefix-cache-note` → 改动最小化 → 本地验证 → `git commit -s`
4. PR 描述:**现象 → 证据(数据/复现命令)→ 改动说明**,首条评论不催 review,48h 后可礼貌 ping 一次
5. CI 红了先自查自修;被要求修改 = 好信号,当天响应
