# -*- coding: utf-8 -*-
"""
检索效果评测脚本
================
指标说明：
  Recall@K  —— 前 K 个结果中能命中标准答案的比例（衡量"能不能找得到"）
  MRR       —— 首个命中结果排名的倒数均值（衡量"排得够不够靠前"）
  NDCG@K    —— 归一化折损累积增益，命中且排名越靠前得分越高

命中判定：把 chunk 文本与标准片段都做归一化（去除所有空白字符）后做包含匹配。
这样可规避 PDF 抽取时中文与数字之间被插入的空格干扰。
"""
import json
import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from retriever import (
    load_pdf, split_documents, build_collection, get_collection,
    collection_name_for, vector_search,
)

DOC_NAME = "阿里巴巴Java开发手册v1.4.0.pdf"
DATASET_PATH = Path(__file__).resolve().parent / "eval_dataset.json"
RESULTS_DIR = Path(__file__).resolve().parent / "results"


def normalize(text: str) -> str:
    """归一化：去掉所有空白字符，规避 PDF 抽取的换行与空格干扰"""
    return re.sub(r"\s+", "", text or "")


def is_hit(chunk_text: str, snippets) -> bool:
    """判断某个 chunk 是否命中标准答案"""
    norm_chunk = normalize(chunk_text)
    for s in snippets:
        if normalize(s) in norm_chunk:
            return True
    return False


def load_dataset():
    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["items"]


def ensure_collection(chunk_size, chunk_overlap):
    """确保指定切分配置的库已建好（已存在则直接复用）"""
    name = collection_name_for(chunk_size, chunk_overlap)
    try:
        vs = get_collection(name)
        if vs.get() and vs.get().get("ids"):
            return vs
    except Exception:
        pass
    docs = load_pdf(DOC_NAME)
    chunks = split_documents(docs, chunk_size, chunk_overlap)
    return build_collection(chunks, name)


def evaluate(vs, dataset, k, reranker=None, recall_k=None, verbose=False):
    """跑一轮评测，返回指标与逐条明细"""
    details = []
    for item in dataset:
        query = item["question"]
        snippets = item["golden_snippets"]

        if reranker is not None:
            candidates = vector_search(vs, query, k=recall_k or k * 4)
            docs = reranker.rerank(query, candidates)[:k]
        else:
            docs = vector_search(vs, query, k=k)

        rank = 0
        for i, d in enumerate(docs):
            if is_hit(d.page_content, snippets):
                rank = i + 1
                break

        details.append({
            "id": item["id"],
            "question": query,
            "category": item["category"],
            "difficulty": item["difficulty"],
            "rank": rank,
            "hit": rank > 0,
        })

    n = len(details)
    recall = sum(1 for d in details if d["hit"]) / n
    mrr = sum((1.0 / d["rank"]) if d["rank"] > 0 else 0.0 for d in details) / n
    ndcg = sum((1.0 / math.log2(d["rank"] + 1)) if d["rank"] > 0 else 0.0 for d in details) / n

    return {
        "recall_at_k": round(recall, 4),
        "mrr": round(mrr, 4),
        "ndcg_at_k": round(ndcg, 4),
        "k": k,
        "total": n,
        "hit_count": sum(1 for d in details if d["hit"]),
        "details": details,
    }


def print_report(config_name, result):
    r = result
    print(f"\n【{config_name}】  top_k={r['k']}")
    print(f"  Recall@{r['k']} : {r['recall_at_k']:.3f}  ({r['hit_count']}/{r['total']})")
    print(f"  MRR      : {r['mrr']:.3f}")
    print(f"  NDCG@{r['k']}  : {r['ndcg_at_k']:.3f}")


def print_failures(result, limit=8):
    """打印未命中的题目，用于定位问题（面试时能讲"我怎么分析失败case"）"""
    fails = [d for d in result["details"] if not d["hit"]]
    if not fails:
        print("\n全部命中，无失败案例")
        return
    print(f"\n未命中 {len(fails)} 条，示例（前 {min(limit, len(fails))} 条）：")
    for d in fails[:limit]:
        print(f"  [{d['id']:>2}] ({d['difficulty']}/{d['category']}) {d['question'][:38]}")


def main():
    dataset = load_dataset()
    print(f"评测集：{len(dataset)} 条问题")
    print(f"文档：{DOC_NAME}")

    configs = [
        {"name": "baseline  (chunk 500/10, k=3)", "cs": 500, "ov": 10, "k": 3},
        {"name": "baseline  (chunk 500/10, k=5)", "cs": 500, "ov": 10, "k": 5},
    ]

    all_results = {}
    for cfg in configs:
        vs = ensure_collection(cfg["cs"], cfg["ov"])
        res = evaluate(vs, dataset, k=cfg["k"])
        print_report(cfg["name"], res)
        print_failures(res)
        all_results[cfg["name"]] = res

    RESULTS_DIR.mkdir(exist_ok=True)
    out = {
        "dataset_size": len(dataset),
        "runs": {k: {kk: vv for kk, vv in v.items() if kk != "details"} for k, v in all_results.items()},
    }
    with open(RESULTS_DIR / "baseline.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"\n结果已保存：{RESULTS_DIR / 'baseline.json'}")


if __name__ == "__main__":
    main()
