#!/usr/bin/env python3
"""exp4 · Prometheus 指标采集:生产监控的最小可行版("佐米修斯"=Prometheus)

前提:有一个 vllm serve 正在跑(默认 127.0.0.1:8000)。
用法: python exp4_metrics_watch.py [--url http://127.0.0.1:8000] [--interval 2]

每 interval 秒抓一次 /metrics(Prometheus 文本格式),提取最关键的 6 个指标,
打成一屏 TSV——这正是 Prometheus+Grafana 常驻监控在做的事,只是这里是裸奔版。
实验建议:开着它跑一次并发压测,看 queue 增长、cache 占用爬升、命中率变化。

接真 Prometheus 的两行配置(装好 prometheus 后):
  scrape_configs:
    - job_name: vllm
      static_configs: [{targets: ['localhost:8000']}]
Grafana:导入 vLLM 官方仓库 examples/ops 下的 dashboard JSON 即可出图。
"""
import argparse, time, urllib.request, re

KEYS = [
    "vllm:num_requests_running", "vllm:num_requests_waiting",
    "vllm:gpu_cache_usage_perc", "vllm:prefix_cache_queries_total",
    "vllm:prefix_cache_hits_total", "vllm:prompt_tokens_total",
    "vllm:generation_tokens_total",
]

def scrape(url):
    with urllib.request.urlopen(url + "/metrics", timeout=5) as r:
        vals = {}
        for line in r.read().decode().splitlines():
            if line.startswith("#") or not line.startswith("vllm:"):
                continue
            name = line.split("{")[0].split(" ")[0]
            if name in KEYS:
                vals[name] = float(line.rsplit(" ", 1)[1])
        return vals

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://127.0.0.1:8000")
    ap.add_argument("--interval", type=float, default=2.0)
    ap.add_argument("--rounds", type=int, default=10)
    args = ap.parse_args()
    prev = {}
    print("time  running waiting cache%  prefix_hit%  gen_tok/s")
    for i in range(args.rounds):
        v = scrape(args.url)
        hit_pct = (100 * (v["vllm:prefix_cache_hits_total"] - prev.get("h", 0)) /
                   max(1e-9, v["vllm:prefix_cache_queries_total"] - prev.get("q", 0))
                  ) if prev and v["vllm:prefix_cache_queries_total"] > prev.get("q", 0) else 0.0
        gen_rate = ((v["vllm:generation_tokens_total"] - prev.get("g", 0)) / args.interval
                    ) if prev else 0.0
        print(f"{i*args.interval:>4.0f}s  {v.get('vllm:num_requests_running',0):>7.0f} "
              f"{v.get('vllm:num_requests_waiting',0):>7.0f} "
              f"{v.get('vllm:gpu_cache_usage_perc',0)*100:>5.1f}  {hit_pct:>10.1f}  {gen_rate:>9.1f}")
        prev = {"h": v["vllm:prefix_cache_hits_total"], "q": v["vllm:prefix_cache_queries_total"],
                "g": v["vllm:generation_tokens_total"]}
        time.sleep(args.interval)

if __name__ == "__main__":
    main()
