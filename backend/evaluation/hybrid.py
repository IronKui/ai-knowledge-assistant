# -*- coding: utf-8 -*-
"""
混合检索（Hybrid Search）：向量语义检索 + BM25 关键词检索，用 RRF 融合
====================================================================
为什么要混合检索：
  向量检索擅长"语义相近"，但对**字面精确匹配**不敏感。
  典型失败场景：用户问"重写父类方法要加什么注解"，文档原文写的是"@Override 注解"——
  语义上接近，但向量模型对专名、编号、术语的字面匹配能力弱，容易漏掉。

  BM25 是经典的词频-逆文档频率检索，正好补上字面匹配这一块。
  两者融合（Hybrid Search）是业界标准做法。

融合策略：RRF（Reciprocal Rank Fusion，倒数排名融合）
  score(d) = Σ  1 / (k + rank_i(d))      k 通常取 60
  - 只依赖排名、不依赖原始分数，因此**不需要归一化**两路量纲不同的分数；
  - 对某一路特别差的鲁棒性好；
  - 是 Elasticsearch / Pinecone / Weaviate 等主流引擎的默认融合方式。
"""
import re
from pathlib import Path

import jieba
from rank_bm25 import BM25Okapi

EVAL_DIR = Path(__file__).resolve().parent

# 中文停用词（极简版，够用即可）
STOPWORDS = set("""
的 了 是 在 我 有 和 就 不 人 都 一 一个 上 也 很 到 说 要 去 你 会 着 没有 看 好 自己 这
什么 怎么 如何 哪些 哪个 吗 呢 吧 啊 请 使用 用 中 为 与 及 或 可以 需要 应该 进行
""".split())

_RRF_K = 60


def tokenize(text: str):
    """中文分词 + 去停用词 + 过滤单字符噪声"""
    text = re.sub(r"\s+", " ", text or "")
    return [w for w in jieba.lcut(text)
            if len(w) > 1 and w not in STOPWORDS and not w.isspace()]


class BM25Index:
    """基于 BM25Okapi 的关键词检索索引"""

    def __init__(self, docs):
        self.docs = docs
        self.corpus = [tokenize(d.page_content) for d in docs]
        self.bm25 = BM25Okapi(self.corpus)

    def search(self, query: str, k: int = 20):
        tokens = tokenize(query)
        if not tokens:
            return []
        scores = self.bm25.get_scores(tokens)
        order = sorted(range(len(self.docs)), key=lambda i: scores[i], reverse=True)
        return [self.docs[i] for i in order[:k] if scores[i] > 0]


def rrf_fuse(ranked_lists, k=20):
    """
    RRF 融合多个已排序的检索结果列表。
    ranked_lists: [[doc, doc, ...], [doc, doc, ...], ...]
    """
    fused = {}
    for docs in ranked_lists:
        for rank, doc in enumerate(docs):
            # 用 chunk_id 做身份标识；无 chunk_id 时退化为文本内容
            key = doc.metadata.get("chunk_id", doc.page_content[:64])
            fused[key] = fused.get(key, 0.0) + 1.0 / (_RRF_K + rank + 1)
    # key -> doc 映射
    doc_of = {}
    for docs in ranked_lists:
        for doc in docs:
            key = doc.metadata.get("chunk_id", doc.page_content[:64])
            doc_of.setdefault(key, doc)
    ranked = sorted(fused.items(), key=lambda x: x[1], reverse=True)
    return [doc_of[key] for key, _ in ranked[:k]]
