# vLLM Inference Lab · 在一张消费级显卡上把 vLLM 学透

> **A hands-on vLLM lab on a consumer GPU**: real measured numbers, reproducible experiments, and interactive explainers — everything verified on an RTX 4070 Ti Super 16GB under WSL2. English summary in [README.en.md](README.en.md).

你大概见过很多"资料收集型"的 LLM 推理教程仓。这个不是。这里的每一个数字都出自**一台普通的单卡机器**(RTX 4070 Ti Super · WSL2 · 国内网络环境),每一条结论都带**可复现的命令和原始数据**,原理部分做成了**可交互的网页**——不是收藏夹,是实验室。

## ✨ 三个别人没有的东西

1. **交互式原理讲解(双击即开,离线可用)**
   - [`vLLM原理演示.html`](vLLM原理演示.html) — 19 页网页幻灯片:屋顶线动画、分页 KV 块池演示、连续批处理甘特动画、TTFT 从 1070ms 滚到 28ms……
   - [`vLLM原理互动讲解.html`](vLLM原理互动讲解.html) — 9 讲交互长页:显存计算器、量化滑杆、多卡场景推演,随便玩
2. **消费级 GPU 上的真实数据集**(A100/H100 基准满天飞,4070 Ti Super 的认真测很少)
   - 单流 + 4 档并发基线、prefix caching 开/关对照(36×)、GPU 有效带宽实测 543GB/s
   - 全部带复现命令和原始 JSON
3. **国内网络环境的完整落地细节**——清华镜像、flashinfer 无 cubin 的 nvcc 坑、conda 共享 CUDA 工具链方案、可编辑安装的 nightly 时滞,全是亲手踩出来的

## 📊 实测数据速览(Qwen3-8B-AWQ @ 4070 Ti Super,预热后 2026-10-31 同日 A/B)

| 并发 | vLLM 吞吐 (tok/s) | SGLang 吞吐 (tok/s) | vLLM TTFT (ms) | SGLang TTFT (ms) |
|---:|---:|---:|---:|---:|
| 1 | 90.6 | 96.9 | 212 | 201 |
| 2 | 164.6 | 166.2 | 332 | 315 |
| 4 | 279.2 | 274.0 | 539 | 582 |
| 8 | 426.4 | 418.5 | 990 | 1014 |

稳态两者打平(±7% 内);单流 97.6 tok/s ≈ 实测有效带宽(543GB/s)推算上限的 83%。**比数字更有价值的是过程**:横评当天 benchmark 先后骗了我们两次(冷启动税压低 26-33%、SGLang 0.9 水位触发 CUDA-graph 显存悬崖 P99 达 338 秒),全部抓出并留档:[SGLang-vs-vLLM横评](docs/SGLang-vs-vLLM横评.md)。prefix caching 实测:多轮对话 TTFT **1070ms → 28ms(≈36×)**,证据三件套见 [实验报告](docs/实验报告.md)。

## 🚀 快速开始(同款硬件 30 分钟起步)

```bash
# Windows + WSL2 Ubuntu 22.04,模型走 ModelScope 国内直下
wsl
conda create -n vllm python=3.12 -y && conda activate vllm
pip install vllm -i https://pypi.tuna.tsinghua.edu.cn/simple
VLLM_USE_FLASHINFER_SAMPLER=0 vllm serve ~/models/Qwen3-8B-AWQ \
  --served-model-name qwen3-8b-awq --max-model-len 8192 --gpu-memory-utilization 0.9
```

完整搭建(含每个坑的解法):[docs/环境报告.md](docs/环境报告.md) · 日常操作与压测方法:[docs/开发指南.md](docs/开发指南.md)

## 📁 目录

| 路径 | 内容 |
|---|---|
| `docs/环境报告.md` | 每层选型与理由、踩坑记录、验收对照 |
| `docs/基线数据.md` | 四档并发基线 + 方法论(含"固定种子×前缀缓存污染"这个大坑) |
| `docs/实验报告.md` | prefix caching 对照实验,证据三件套 |
| `docs/开发指南.md` | 吞吐怎么看 / 源码怎么改 / bug 怎么复现 |
| `docs/开源路线图.md` | 从 0 参与开源 + 100 star 增长剧本 |
| `bench/multiturn_prefix.py` | 多轮对话 TTFT 实验脚本(asyncio 流式) |
| `playground/` | 4 个入门实验:KV 记账对账 / 算子热点 / 带宽上限 / Prometheus 采集 |

## 🗺️ Roadmap

- [x] SGLang vs vLLM 同负载横评(同日同预热 A/B + 两个 benchmark 陷阱实录)→ [docs/SGLang-vs-vLLM横评.md](docs/SGLang-vs-vLLM横评.md)
- [ ] SGLang 修复 PR(等 [#47420](https://github.com/sgl-project/sglang/issues/47420) 维护者表态)
- [ ] 投机解码(speculative decoding)实测:收益与开销
- [ ] 2×GPU 张量并行跑 Qwen3-32B(等硬件)
- [ ] 交互讲解页英文版
- [ ] lm-eval 量化前后质量评测流水线

## 📄 数据与声明

- 全部延迟/吞吐数据为本人实测(vLLM 0.32.0 · Qwen3 系列 · 2026-10),原始 JSON 在 WSL `~/bench/results/`
- DeepInfer 对比信息据公开报道与官方仓库,以官方为准
- 仅用于学习交流,[MIT License](LICENSE)
