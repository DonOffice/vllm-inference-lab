# PR 候选清单:从我们实测里长出来的贡献机会

> 原则:只提**亲手复现过**的问题;先搜 issue 避免重复;文档 PR 也要有数据支撑。
> 每个候选都标了证据、预期 PR 形态和提交前核对项。状态:☑=已核实可行 / ◐=提交前需再核对

## 候选 1:SGLang `bench_serving` 的 random 数据集仍强制下载 ShareGPT ☑

- **证据**:本机 0.5.22 实测——`--dataset-name random` 仍向 `huggingface.co/datasets/anon8231489123/ShareGPT_Vicuna_unfiltered` 发 HEAD 请求,离线/受限网络下重试 5 次后失败(`HF_HUB_OFFLINE=1` 则直接抛 OfflineModeIsEnabled)。
- **已知 issue**:[sgl-project/sglang #4133](https://github.com/sgl-project/sglang/issues/4133)"Random dataset in benchmark_serving is not random"——**问题已被报告,别重复报**;去 issue 下确认无人认领修复后评论 "I'd like to work on this",再动代码。
- **修复思路**(认领后):`python -m sglang.benchmark.serving` 的启动路径里,`--dataset-name random` 时跳过 ShareGPT 预载(注意 0.5.x 里旧入口 `sglang.bench_serving` 已弃用,改新入口)。
- **PR 流程要点**:SGLang 用 GitHub PR + CI;commit 加 `Signed-off-by`(DCO);PR 描述链接 #4133 并附复现环境(WSL2 + HF 不可达)。

## 候选 2:vLLM Benchmark CLI 文档:把"prefix cache 会污染重复压测"的提示扩成可操作说明 ☑◐

- **现状**:官方 [Benchmark CLI](https://docs.vllm.ai/en/latest/benchmarking/cli) 已有一句 note:重复对同一 server 跑 `vllm bench serve` 会因 prefix cache 复用 prompt 而虚高吞吐。**但没有成因、复现步骤和规避方法**。
- **我们的增量**(全部实测,见 [docs/基线数据.md](基线数据.md) §3):
  - 成因链:bench 默认固定随机种子 → 各轮压测用同一批 prompt → 服务默认开 prefix caching → 第二轮起命中第一轮 KV
  - 数字:污染版 c=8 吞吐 445 vs 干净版 320 tok/s(+39% 虚高);c=2 的 TTFT 出现物理上不可能的 35ms
  - 规避:档间换 `--seed` 或重启服务;附最小复现命令
- **PR 形态**:docs/source/benchmarking/cli.md(以当时 main 分支路径为准)扩充该 note,链接到结果 JSON 的对照表。提交前核对:main 分支该文件现状(用 `gh api` 或网页),确认没被别人改过。
- **同类小补充**(顺手核对):`--base-url` 不要带 `/v1` 后缀(带了解析到 `/v1/v1/...` 全 404,我们实测踩过);若文档未提,一并加一句 caution。

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
