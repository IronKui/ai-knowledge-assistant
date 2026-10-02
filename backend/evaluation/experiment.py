# -*- coding: utf-8 -*-
"""
对照实验：量化每个优化动作带来的指标变化
==========================================
阶段 A：切分策略对比（固定 k=3，无重排）—— 回答"chunk 切多大合适"
阶段 B：引入重排序（向量粗召回 Top-N → CrossEncoder 精排 Top-3）—— 回答"重排值不值得做"

每个阶段只改变一个变量，保证结论可归因。
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from evaluate import load_dataset, ensure_collection, evaluate, print_report, print_failures
from reranker import Reranker

RESULTS_DIR = Path(__file__).resolve().parent / "results"

# ---------- 实验配置 ----------
STAGE_A = [
    {"name": "A1 chunk=300/ov=10  k=3", "cs": 300, "ov": 10, "k": 3, "rerank": False},
    {"name": "A2 chunk=500/ov=10  k=3", "cs": 500, "ov": 10, "k": 3, "rerank": False},
    {"name": "A3 chunk=800/ov=10  k=3", "cs": 800, "ov": 10, "k": 3, "rerank": False},
]

STAGE_B = [
    {"name": "B1 向量召回10 → 重排取3", "cs": 500, "ov": 10, "k": 3, "rerank": True, "recall_k": 10},
    {"name": "B2 向量召回20 → 重排取3", "cs": 500, "ov": 10, "k": 3, "rerank": True, "recall_k": 20},
    {"name": "B3 向量召回20 → 重排取5", "cs": 500, "ov": 10, "k": 5, "rerank": True, "recall_k": 20},
]


def run_stage(stage_name, configs, dataset, reranker):
    print("\n" + "=" * 66)
    print(f" {stage_name}")
    print("=" * 66)
    results = {}
    for cfg in configs:
        vs = ensure_collection(cfg["cs"], cfg["ov"])
        use_reranker = cfg.get("rerank", False) and (reranker is not None and reranker.available)
        if cfg.get("rerank", False) and not use_reranker:
            print(f"\n[跳过] {cfg['name']} —— 重排模型不可用")
            continue
        res = evaluate(
            vs, dataset, k=cfg["k"],
            reranker=reranker if use_reranker else None,
            recall_k=cfg.get("recall_k"),
        )
        print_report(cfg["name"], res)
        results[cfg["name"]] = res
    return results


def main():
    dataset = load_dataset()
    print(f"评测集 {len(dataset)} 条 | 文档：阿里巴巴Java开发手册v1.4.0")

    reranker = Reranker()
    if reranker.available:
        print("重排模型：已加载 (BAAI/bge-reranker-base)")
    else:
        print(f"重排模型：不可用（{reranker.load_error}）—— 阶段 B 将跳过")

    all_results = {}
    all_results.update(run_stage("阶段 A：切分策略对比", STAGE_A, dataset, reranker))
    all_results.update(run_stage("阶段 B：引入重排序", STAGE_B, dataset, reranker))

    # 汇总表
    print("\n" + "=" * 66)
    print(" 汇总")
    print("=" * 66)
    print(f"{'配置':<32}{'Recall@K':>10}{'MRR':>9}{'NDCG@K':>9}")
    print("-" * 66)
    for name, r in all_results.items():
        print(f"{name:<32}{r['recall_at_k']:>10.3f}{r['mrr']:>9.3f}{r['ndcg_at_k']:>9.3f}")

    RESULTS_DIR.mkdir(exist_ok=True)
    out = {
        "dataset_size": len(dataset),
        "runs": {k: {kk: vv for kk, vv in v.items() if kk != "details"} for k, v in all_results.items()},
    }
    with open(RESULTS_DIR / "experiment.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"\n结果已保存：{RESULTS_DIR / 'experiment.json'}")


if __name__ == "__main__":
    main()
