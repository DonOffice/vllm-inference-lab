#!/usr/bin/env python3
"""exp3 · 带宽→速度上限:第一性原理的实测验证

三步:
  1) 实测 GPU 有效显存带宽(大 tensor 循环拷贝,只有拷贝是纯带宽操作)
  2) 由"decode 每 token 读一遍权重"推出不同量化下的单流速度上限
  3) 和本机实测基线(8B-AWQ 77.5 tok/s)对照,看带宽利用率落到哪

用法: python exp3_bandwidth_ceiling.py
"""
import torch

def measure_bandwidth(gb=1.0, iters=30):
    n = int(gb * 1073741824 // 4)
    a = torch.randn(n, device="cuda", dtype=torch.float32)
    b = torch.empty_like(a)
    for _ in range(5):
        b.copy_(a)                    # 预热
    torch.cuda.synchronize()
    start = torch.cuda.Event(True); end = torch.cuda.Event(True)
    start.record()
    for _ in range(iters):
        b.copy_(a)
    end.record(); torch.cuda.synchronize()
    ms = start.elapsed_time(end) / iters
    # 一次 D2D 拷贝 = 读 a + 写 b,搬动 2×size 字节
    gbps = 2 * n * 4 / (ms / 1e3) / 1e9
    return gbps

def main():
    torch.cuda.init()
    name = torch.cuda.get_device_name(0)
    bw = measure_bandwidth()
    print(f"GPU: {name}")
    print(f"实测有效显存带宽(D2D 拷贝,含读写): {bw:.0f} GB/s")
    print(f"标称: 672 GB/s(读+写合计口径可能高于单向)\n")

    print(f"{'模型':<12} {'量化':<8} {'权重GB':>7} {'理论上限 tok/s':>14}")
    for label, params, bits in [("Qwen3-1.7B", 1.7, 16), ("Qwen3-8B", 8, 16),
                                 ("Qwen3-8B", 8, 8), ("Qwen3-8B", 8, 4),
                                 ("Qwen3-32B", 32, 4)]:
        w = params * bits / 8 * 1.15
        print(f"{label:<12} {str(bits)+'bit':<8} {w:>7.1f} {bw / w:>14.0f}")

    print("""
对照基线:8B-AWQ 实测单流 77.5 tok/s ÷ 上表 4bit 上限 ≈ 带宽利用率。
利用率明显偏低(比如 <40%)通常意味着:kernel 启动开销、采样/调度间隙、
或量化解压额外计算吃掉了时间——这就是"优化空间"的量化入口。
进阶:改 iters/gb 复测带宽稳定性;用 exp2 的算子表找时间真正去了哪。
""")

if __name__ == "__main__":
    main()
