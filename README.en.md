# vLLM Inference Lab

> Learn vLLM properly on a **single consumer GPU**: every number in this repo was measured on an RTX 4070 Ti Super (16GB) under WSL2, every claim ships with a reproducible command, and the theory is explained in **interactive offline HTML** — not another link dump. Full Chinese docs (data reports are language-of-data anyway) — [README.md](README.md).

## Highlights

- **Interactive explainers** (double-click, zero dependencies):
  - `vLLM原理演示.html` — a 19-page HTML slide deck with animations: roofline, paged-KV block pool, continuous batching Gantt, TTFT counting down 1070ms → 28ms
  - `vLLM原理互动讲解.html` — a 9-section interactive long page: VRAM calculator, quantization slider, multi-GPU scenario picker
- **A real dataset from a consumer GPU** (most public benchmarks are A100/H100):
  - Concurrency sweep 1/2/4/8 on Qwen3-8B-AWQ: 71.7 → 320.5 tok/s total
  - Prefix caching A/B: TTFT 1070ms → 28ms (≈36×) with metrics + log evidence
  - Measured effective GPU bandwidth 543 GB/s → explains why decode tops out where it does
- **Reproducible experiments** (`playground/`): KV-cache accounting vs. server logs, kernel hotspot profiling, bandwidth ceiling, Prometheus metrics scraping

## Quick start (WSL2 + any 16GB GPU)

```bash
pip install vllm && VLLM_USE_FLASHINFER_SAMPLER=0 vllm serve <model> --gpu-memory-utilization 0.9
```

See `docs/环境报告.md` for the full setup (CN), including China-network mirrors and the flashinfer/nvcc pitfalls we solved.

## Repo map

`docs/` — environment report, baseline benchmarks, prefix-caching experiment, dev guide, open-source roadmap (CN) · `bench/` — experiment scripts · `playground/` — four starter experiments

## Status & License

Personal learning lab, MIT. Data measured by the author (vLLM 0.32.0, Oct 2026). Roadmap: SGLang-vs-vLLM comparison, speculative decoding measurements, EN version of the explainer.
