#!/usr/bin/env python3
"""exp1 · KV cache 记账对账:验证"显存账本"公式的真实性

公式: KV/token = 2(K和V) × 层数 × KV头数 × 头维度 × 每元素字节
用法:
  python exp1_kv_accounting.py --model ~/models/Qwen3-8B-AWQ
  python exp1_kv_accounting.py --model ~/models/Qwen3-8B-AWQ --log ~/bench/qwen3-8b-final2.log
不带 --log 也能跑:打印纯公式推算表;带 --log 则和 vLLM 服务日志里
"GPU KV cache size: N tokens" 对账(那行是引擎真实分配的结果)。
"""
import argparse, json, math, os, re

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--log", default=None, help="vllm serve 的日志文件,用于对账")
    ap.add_argument("--dtype-bytes", type=int, default=2, help="KV 元素字节:fp16=2, fp8=1")
    args = ap.parse_args()

    cfg = json.load(open(os.path.join(args.model, "config.json")))
    layers = cfg["num_hidden_layers"]
    kv_heads = cfg.get("num_key_value_heads", cfg["num_attention_heads"])
    # head_dim 有两种写法
    hd = cfg.get("head_dim") or cfg["hidden_size"] // cfg["num_attention_heads"]
    per_tok = 2 * layers * kv_heads * hd * args.dtype_bytes
    print(f"模型: {os.path.basename(args.model)}")
    print(f"层数={layers}  KV头={kv_heads}  头维度={hd}  (注意力组数 GQA: {cfg['num_attention_heads']//kv_heads} 查询头/KV头)")
    print(f"KV/token = 2×{layers}×{kv_heads}×{hd}×{args.dtype_bytes} = {per_tok/1024:.0f} KB\n")
    print(f"{'上下文':>8} | {'单路 KV':>10} | {'8 路并发':>10}")
    for ctx in (1024, 4096, 8192, 32768, 131072):
        one = per_tok * ctx / 1073741824
        print(f"{ctx:>8} | {one:>8.2f}GB | {one*8:>8.2f}GB")

    if args.log:
        txt = open(args.log, errors="ignore").read()
        m = re.search(r"GPU KV cache size: ([\d,]+) tokens", txt)
        m2 = re.search(r"GPU KV cache usage: .*?Maximum concurrency: (\d+) tokens", txt)
        if m:
            toks = int(m.group(1).replace(",", ""))
            print(f"\n[对账] 服务日志实际分配 KV cache = {toks:,} tokens ≈ {per_tok*toks/1073741824:.1f} GB")
            if m2:
                print(f"[对账] 最大并发 tokens = {int(m2.group(1).replace(',', '')):,}")
        else:
            print("\n[对账] 日志里没找到 'GPU KV cache size' 行(可能日志太旧或被截断)")

if __name__ == "__main__":
    main()
