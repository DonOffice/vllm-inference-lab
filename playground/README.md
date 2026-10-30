# playground · 四个入门实验

> 配合交互讲解页"第 8 讲 方向与工具"使用。全部在本机验证过的环境上运行。

## 快速开始

```bash
wsl
conda activate vllm            # exp1/3/4 用 vllm 环境;exp2 也用它(需要独占 GPU)
cd ~/playground
```

| 实验 | 命令 | 前提 | 验证什么 |
|---|---|---|---|
| exp1 KV 记账 | `python exp1_kv_accounting.py --model ~/models/Qwen3-8B-AWQ --log ~/bench/qwen3-8b-final2.log` | 无(纯 CPU) | 显存账本公式 vs 引擎实际分配,两数对上=理解到位 |
| exp2 算子热点 | `python exp2_kernel_hotspots.py` | **GPU 空闲**(没有 vllm serve 在跑) | decode 时间花在哪些 kernel 上;换 8B-AWQ 跑一遍对比算子结构 |
| exp3 带宽上限 | `python exp3_bandwidth_ceiling.py` | GPU 空闲 | 实测有效带宽 → 各量化下 tok/s 理论上限 → 和 77.5 基线对照算利用率 |
| exp4 指标采集 | 先起服务,再 `python exp4_metrics_watch.py` | vllm serve 运行中 | 生产监控的最小版;开一个终端跑它,另一个终端压测,看指标联动 |

## 建议的实验顺序(对应学习路径)

1. **exp1**:先让公式和现实对上账——这是后面一切判断的尺子
2. **exp3**:量出这台机器的物理上限,理解"为什么 77.5 不是 120"
3. **exp2**:打开引擎盖看时间真正去了哪(把 --model 换成 `~/models/Qwen3-8B-AWQ` 再跑一次)
4. **exp4**:另开终端跑 `vllm bench serve --max-concurrency 8 ...`(命令见 ../docs/基线数据.md),看 queue/cache/命中率怎么随负载变化

## 改动建议(做自己的实验)

- exp1:改 `--dtype-bytes 1` 模拟 FP8 KV,看上下文容量翻倍
- exp2:去掉 `enforce_eager=True` 对比 CUDA Graph 前后的 CPU 开销变化
- exp3:把 iters 从 30 改到 200,观察带宽测量稳定性
- exp4:改 KEYS 加 `vllm:request_success_total`、`vllm:time_to_first_token_seconds` 的直方图分位

## 深潜工具(以后用,本机已可跑)

```bash
# torch profiler 由 vLLM 内置(在线模式):
VLLM_TORCH_PROFILER_DIR=~/bench/profile vllm serve ...   # 启动
curl -X POST localhost:8000/start_profile                 # 开始
curl -X POST localhost:8000/stop_profile                  # 结束 → 用 Chrome tracing 打开
# nsys 时间线 / ncu 单内核:需另装 nsight-systems(apt 或 NVIDIA 官网),装好后:
#   nsys profile -o rep --trace=cuda,nvtx python exp2_kernel_hotspots.py
```
