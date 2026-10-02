# -*- coding: utf-8 -*-
"""
阶段 D：混合检索（Hybrid Search）验证
====================================
背景：阶段 B 的最优配置（向量20→重排3）下仍有 3 条未命中，
归因是"用户提问措辞与文档原文字面不匹配"——向量检索的固有盲区。

假设：引入 BM25 关键词检索并用 RRF 融合，可补上字面匹配能力，收掉这批 bad case。

实验设计：
  D0  纯 BM25 Top-3            —— 单独看关键词检索的能力
  D1  混合(RRF) Top-3          —— 单独看融合的收益
  D2  混合(RRF) 20 → 重排 3     —— 与阶段 B 最优配置(B2)同口径对比
  D3  混合(RRF) 20 → 重排 5
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from langchain_core.documents import Document

from evaluate import load_dataset, ensure_collection, evaluate, print_report, print_failures
from retriever import vector_search
from hybrid import BM25Index, rrf_fuse
from reranker import Reranker

RESULTS_DIR = Path(__file__).resolve().parent / "results"

CHUNK_SIZE, OVERLAP = 500, 10   # 阶段 C 确定的最优切分
RECALL_K = 20
RERANK_K = 3


def load_all_chunks(vs):
    """从向量库取回全部 chunk，用于构建 BM25 索引"""
    data = vs.get()
    docs = []
    for text, meta in zip(data.get("documents", []), data.get("metadatas", [])):
        docs.append(Document(page_content=text, metadata=meta or {}))
    return docs


def hybrid_search(vs, bm25, query, k, recall_k=RECALL_K):
    """向量 + BM25，RRF 融合"""
    vec_docs = vector_search(vs, query, k=recall_k)
    bm_docs = bm25.search(query, k=recall_k)
    fused = rrf_fuse([vec_docs, bm_docs], k=recall_k)
    return fused[:k]


def main():
    dataset = load_dataset()
    vs = ensure_collection(CHUNK_SIZE, OVERLAP)
    all_chunks = load_all_chunks(vs)
    bm25 = BM25Index(all_chunks)
    reranker = Reranker()
    print(f"语料 {len(all_chunks)} 个 chunk | 评测集 {len(dataset)} 条")
    print(f"重排模型：{'已加载' if reranker.available else '不可用'}\n")

    results = {}

    # D0 纯 BM25
    def bm25_only(query, k):
        return bm25.search(query, k=k)

    res = evaluate_custom(dataset, bm25_only, k=3)
    print_report("D0 纯 BM25 Top-3", res)
    print_failures(res)
    results["D0 纯 BM25 Top-3"] = res

    # D1 混合(RRF) Top-3，无重排
    res = evaluate_custom(dataset, lambda q, k: hybrid_search(vs, bm25, q, k), k=3)
    print_report("D1 混合RRF Top-3（无重排）", res)
    print_failures(res)
    results["D1 混合RRF Top-3（无重排）"] = res

    # D2 混合20 → 重排3
    def hybrid_rerank3(q, k):
        fused = hybrid_search(vs, bm25, q, k, RECALL_K)
        return reranker.rerank(q, fused, top_n=k)

    res = evaluate_custom(dataset, hybrid_rerank3, k=3)
    print_report("D2 混合RRF 20 → 重排3", res)
    print_failures(res)
    results["D2 混合RRF 20 → 重排3"] = res

    # D3 混合20 → 重排5
    res = evaluate_custom(dataset, hybrid_rerank3, k=5)
    print_report("D3 混合RRF 20 → 重排5", res)
    results["D3 混合RRF 20 → 重排5"] = res

    # 汇总
    exp_path = RESULTS_DIR / "experiment.json"
    with open(exp_path, "r", encoding="utf-8") as f:
        merged = json.load(f)
    for name, r in results.items():
        merged["runs"][name] = {kk: vv for kk, vv in r.items() if kk != "details"}

    print("\n" + "=" * 70)
    print(" 全量汇总（含阶段 A/B/C）")
    print("=" * 70)
    print(f"{'配置':<34}{'Recall@K':>10}{'MRR':>9}{'NDCG@K':>9}")
    print("-" * 70)
    for name, r in merged["runs"].items():
        print(f"{name:<34}{r['recall_at_k']:>10.3f}{r['mrr']:>9.3f}{r['ndcg_at_k']:>9.3f}")

    # 保存最优配置的失败案例
    best_name = max(results, key=lambda n: (results[n]["recall_at_k"], results[n]["mrr"]))
    fails = [d for d in results[best_name]["details"] if not d["hit"]]
    with open(RESULTS_DIR / "failure_cases.json", "w", encoding="utf-8") as f:
        json.dump({"config": best_name, "count": len(fails), "cases": fails},
                  f, ensure_ascii=False, indent=2)

    with open(exp_path, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)
    print(f"\n最优：{best_name} | 剩余失败 {len(fails)} 条 → results/failure_cases.json")


def evaluate_custom(dataset, search_fn, k):
    """用自定义检索函数跑评测（与 evaluate.evaluate 同口径）"""
    from evaluate import is_hit
    import math
    details = []
    for item in dataset:
        docs = search_fn(item["question"], k)
        rank = 0
        for i, d in enumerate(docs):
            if is_hit(d.page_content, item["golden_snippets"]):
                rank = i + 1
                break
        details.append({"id": item["id"], "question": item["question"],
                        "category": item["category"], "difficulty": item["difficulty"],
                        "rank": rank, "hit": rank > 0})
    n = len(details)
    return {
        "recall_at_k": round(sum(1 for d in details if d["hit"]) / n, 4),
        "mrr": round(sum((1.0 / d["rank"]) if d["rank"] > 0 else 0.0 for d in details) / n, 4),
        "ndcg_at_k": round(sum((1.0 / math.log2(d["rank"] + 1)) if d["rank"] > 0 else 0.0
                               for d in details) / n, 4),
        "k": k, "total": n, "hit_count": sum(1 for d in details if d["hit"]),
        "details": details,
    }


if __name__ == "__main__":
    main()
