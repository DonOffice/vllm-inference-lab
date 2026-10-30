#!/usr/bin/env python3
"""exp2 · 算子热点剖析:一次 decode 到底把时间花在哪

用 vLLM 离线引擎 + torch.profiler,对几条短 prompt 的生成做采样,
输出耗时 Top 算子表。你会看到:decode 阶段被一堆 GEMV/matmul 和
elementwise 内核占据——它们都在反复读同一份权重(带宽瓶颈的直接证据)。

⚠ 需要独占 GPU:先确保没有 vllm serve 在跑(pgrep -af vllm)。
用法: python exp2_kernel_hotspots.py   (模型默认 Qwen3-1.7B)
"""
import argparse
from vllm import LLM, SamplingParams
from torch.profiler import profile, ProfilerActivity

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="/home/sikai/models/Qwen3-1.7B")
    ap.add_argument("--prompts", type=int, default=4)
    args = ap.parse_args()

    llm = LLM(model=args.model, max_model_len=2048, gpu_memory_utilization=0.6,
              enforce_eager=True)  # eager 便于看原始 kernel
    sp = SamplingParams(temperature=0.0, max_tokens=48)
    prompts = ["请用三句话解释什么是显存带宽。"] * args.prompts

    llm.generate(prompts[:1], sp)  # 预热(编译/加载已完成)

    print("\n==== 开始剖析(prefill + 48 步 decode)====")
    with profile(activities=[ProfilerActivity.CPU, ProfilerActivity.CUDA]) as prof:
        llm.generate(prompts, sp)

    print(prof.key_averages().table(sort_by="cuda_time_total", row_limit=18))
    print("""
怎么读这张表(第一性原理):
  1. cuda_time 总和 ≈ GPU 实际工作时间;找前 3-5 名算子,看它们是 memory-bound(带宽)还是 compute-bound。
  2. decode 每 token 都要完整读一遍权重 → GEMV/量化解压内核占比高是正常的、健康的。
  3. 如果出现大量 aten::copy_/elementwise 且占比异常,说明数据在搬运上浪费(优化目标!)。
  4. 对比实验:把 --model 换成 8B-AWQ 再跑一遍,观察算子结构怎么随量化变化(Marlin 内核会出现)。
""")

if __name__ == "__main__":
    main()
