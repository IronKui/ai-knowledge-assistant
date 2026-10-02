# -*- coding: utf-8 -*-
"""
阶段 C：最优组合验证 + 失败案例分析
==================================
阶段 A 找出最优切分（chunk=800），阶段 B 验证重排序有效。
阶段 C 把两者叠加，确认是否为全局最优；并输出未命中案例用于归因分析。
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from evaluate import load_dataset, ensure_collection, evaluate, print_report, print_failures
from reranker import Reranker

RESULTS_DIR = Path(__file__).resolve().parent / "results"

STAGE_C = [
    {"name": "C1 chunk=800 召回20 → 重排3", "cs": 800, "ov": 10, "k": 3, "rerank": True, "recall_k": 20},
    {"name": "C2 chunk=800 召回20 → 重排5", "cs": 800, "ov": 10, "k": 5, "rerank": True, "recall_k": 20},
]


def main():
    dataset = load_dataset()
    reranker = Reranker()
    print(f"重排模型：{'已加载' if reranker.available else '不可用 ' + str(reranker.load_error)}")
    print(f"评测集 {len(dataset)} 条\n")

    all_results = {}
    for cfg in STAGE_C:
        vs = ensure_collection(cfg["cs"], cfg["ov"])
        res = evaluate(vs, dataset, k=cfg["k"], reranker=reranker,
                       recall_k=cfg.get("recall_k"))
        print_report(cfg["name"], res)
        print_failures(res)
        all_results[cfg["name"]] = res

    # 合并历史结果
    exp_path = RESULTS_DIR / "experiment.json"
    if exp_path.exists():
        with open(exp_path, "r", encoding="utf-8") as f:
            merged = json.load(f)
    else:
        merged = {"dataset_size": len(dataset), "runs": {}}
    for name, r in all_results.items():
        merged["runs"][name] = {k: v for k, v in r.items() if k != "details"}

    print("\n" + "=" * 66)
    print(" 全量汇总")
    print("=" * 66)
    print(f"{'配置':<32}{'Recall@K':>10}{'MRR':>9}{'NDCG@K':>9}")
    print("-" * 66)
    for name, r in merged["runs"].items():
        print(f"{name:<32}{r['recall_at_k']:>10.3f}{r['mrr']:>9.3f}{r['ndcg_at_k']:>9.3f}")

    with open(exp_path, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)

    # 单独保存失败案例，供归因分析
    best_name = max(merged["runs"], key=lambda n: (merged["runs"][n]["recall_at_k"],
                                                   merged["runs"][n]["mrr"]))
    best = all_results.get(best_name)
    if best:
        fails = [d for d in best["details"] if not d["hit"]]
        with open(RESULTS_DIR / "failure_cases.json", "w", encoding="utf-8") as f:
            json.dump({"config": best_name, "count": len(fails), "cases": fails},
                      f, ensure_ascii=False, indent=2)
        print(f"\n最优配置：{best_name}")
        print(f"失败案例 {len(fails)} 条已保存 → results/failure_cases.json")

    print(f"\n结果已保存：{exp_path}")


if __name__ == "__main__":
    main()
