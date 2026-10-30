#!/usr/bin/env python3
"""多轮对话 prefix caching 对照实验:测量每一轮请求的 TTFT(首 token 延迟)。

原理:多轮对话中,第 N 轮请求的前缀 = system prompt + 前 N-1 轮完整历史。
开启 prefix caching 时,这部分前缀命中 KV cache,预填充(prefill)只需计算
新增的最后一轮问题,TTFT 显著下降;关闭(或前缀未命中)时,每轮都要完整重算。

两种跑法:
  A. cache-hit 组:同一会话内连续多轮(system + 历史 前缀可命中)
  B. cache-miss 组:每轮换一个全新的 system prompt(相同长度,内容随机),
     前缀永不命中 —— 作为"相当于关掉缓存"的对照组。

用法:
  python multiturn_prefix.py --base-url http://127.0.0.1:8000 --model MODEL \
      --rounds 3 --turns 6 --mode hit|miss|both --output result.json
"""
import argparse
import asyncio
import json
import random
import statistics
import time

import aiohttp

FILLER = (
    "大模型推理系统的性能由多个环节共同决定：调度器决定批次如何组织，"
    "KV cache 管理决定显存如何复用，注意力内核决定计算密度，"
    "量化方案决定带宽瓶颈下每秒能读出多少权重。"
    "理解 vLLM 的第一步，是把一条请求从进入 API server 到吐出第一个 token 的路径走通。"
)  # 约 130 token，循环拼接出长 system prompt


def build_system_prompt(seed: int | None, paras: int) -> str:
    """seed=None 生成固定(可命中)前缀;seed=int 生成随机(不可命中)前缀。"""
    rng = random.Random(seed)
    out = []
    for i in range(paras):
        if seed is None:
            out.append(f"[背景资料 {i}] " + FILLER)
        else:
            # 打乱语序并插入随机词,使每一份都内容不同 → 前缀必不命中
            words = FILLER.replace("，", " ").replace("。", " ").split()
            rng.shuffle(words)
            out.append(f"[资料 {i}] " + "".join(words) + f" (nonce={rng.random():.9f})")
    return "\n".join(out)


async def one_turn(session, url, model, messages, tag):
    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": 48,
        "temperature": 0.0,
        "stream": True,
    }
    t0 = time.perf_counter()
    ttft, ntok = None, 0
    async with session.post(url, json=payload) as resp:
        resp.raise_for_status()
        async for raw in resp.content:
            if not raw.startswith(b"data:"):
                continue
            data = raw[5:].strip()
            if data == b"[DONE]":
                break
            chunk = json.loads(data)
            delta = chunk["choices"][0].get("delta", {})
            if delta.get("content"):
                ntok += 1  # 近似:每个非空增量记 1 token
                if ttft is None:
                    ttft = time.perf_counter() - t0
    total = time.perf_counter() - t0
    return {"tag": tag, "ttft_s": ttft, "tokens": ntok, "total_s": total,
            "prompt_messages": len(messages)}


async def one_session(session, url, model, turns, paras, miss: bool, round_idx: int = 0):
    """跑一个完整多轮会话,返回每轮结果。miss=True 时每轮换随机 system prompt。"""
    results = []
    if not miss:
        system = build_system_prompt(None, paras)
    history = []
    for t in range(1, turns + 1):
        if miss:
            # 种子必须包含 round 和 turn:保证每个请求的前缀都独一无二,永不命中缓存
            system = build_system_prompt(seed=(round_idx * 1000 + t) * 7919, paras=paras)
        user_q = f"第 {t} 轮:请用一句话总结上述背景资料的第 {t} 条要点。"
        messages = ([{"role": "system", "content": system}]
                    + history + [{"role": "user", "content": user_q}])
        r = await one_turn(session, url, model, messages, f"turn{t}")
        results.append(r)
        # 把这轮 assistant 的简短回复拼进历史,下一轮的前缀随之增长
        history += [{"role": "user", "content": user_q},
                    {"role": "assistant", "content": "(已收到,继续。)"}]
    return results


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://127.0.0.1:8000")
    ap.add_argument("--model", required=True)
    ap.add_argument("--rounds", type=int, default=3, help="重复会话次数(取中位数)")
    ap.add_argument("--turns", type=int, default=6, help="每个会话的对话轮数")
    ap.add_argument("--paras", type=int, default=16, help="system prompt 段数(约130 token/段)")
    ap.add_argument("--mode", choices=["hit", "miss", "both"], default="both")
    ap.add_argument("--output", default="prefix_result.json")
    args = ap.parse_args()

    url = args.base_url.rstrip("/") + "/v1/chat/completions"
    all_results = {"hit": [], "miss": []}
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=600)) as session:
        for grp in (["hit", "miss"] if args.mode == "both" else [args.mode]):
            for r in range(args.rounds):
                res = await one_session(session, url, args.model,
                                        args.turns, args.paras,
                                        miss=(grp == "miss"), round_idx=r + 1)
                for x in res:
                    x["round"] = r + 1
                all_results[grp].extend(res)
                ttfts = [f"{x['ttft_s']*1000:.0f}ms" for x in res]
                print(f"[{grp}] round {r+1}: 每轮TTFT = {ttfts}", flush=True)

    # 汇总:每轮指标在多个 round 间取中位数
    summary = {}
    for grp, rows in all_results.items():
        if not rows:
            continue
        summary[grp] = {}
        # 冷启动:第 1 个会话的 TTFT(缓存为空,必然全量 prefill)
        cold = [x["ttft_s"] for x in rows if x["round"] == 1]
        if cold:
            summary[grp]["cold_round1_ttft_ms_each"] = [
                round(v * 1000, 1) for v in cold]
        # 热稳态:第 2+ 会话各轮 TTFT 中位数(hit 组此后应显著低于冷值)
        for t in range(1, args.turns + 1):
            vals = [x["ttft_s"] for x in rows
                    if x["tag"] == f"turn{t}" and x["round"] > 1]
            if vals:
                summary[grp][f"turn{t}_ttft_ms_median_warm"] = round(
                    statistics.median(vals) * 1000, 1)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump({"raw": all_results, "summary": summary}, f,
                  ensure_ascii=False, indent=2)
    print("\n==== 汇总(每轮 TTFT 中位数, ms)====")
    for grp, s in summary.items():
        print(f"[{grp}] " + "  ".join(f"t{i+1}={v}" for i, (k, v)
              in enumerate(s.items())))
    print(f"\n原始数据已写入 {args.output}")


if __name__ == "__main__":
    asyncio.run(main())
