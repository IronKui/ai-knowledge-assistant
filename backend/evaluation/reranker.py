# -*- coding: utf-8 -*-
"""
重排序（Rerank）模块
====================
为什么需要重排序：
  向量检索（Bi-Encoder）把 query 和文档各自独立编码成向量，再算余弦相似度。
  优点是快（文档向量可离线算好）、可海量召回；缺点是 query 与文档之间没有
  充分交互，对精确语义匹配不敏感。

  CrossEncoder（重排）把 query 和文档拼在一起送进模型做联合打分，精度显著更高，
  但必须对候选逐一计算，无法离线预存，所以只适合对少量候选做精排。

  因此工业界标准做法是两阶段：向量先粗召回 Top-N（N 较大，保证召回率），
  再用 CrossEncoder 精排取 Top-K（K 较小，保证喂给大模型的内容精准）。

降级策略：
  重排服务不可用时（模型缺失 / 显存不足 / 超时）自动退回向量检索结果，
  保证服务可用，不让一个可选组件拖垮主链路。
"""
import os
from pathlib import Path

os.environ.setdefault('HF_ENDPOINT', 'https://hf-mirror.com')

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_MODEL_PATH = str(BASE_DIR / "models" / "bge-reranker-base")


class Reranker:
    """CrossEncoder 重排器"""

    def __init__(self, model_path: str = None, device: str = "cpu", max_length: int = 512):
        self.model_path = model_path or DEFAULT_MODEL_PATH
        self.device = device
        self.max_length = max_length
        self._model = None
        self.available = False
        self.load_error = None
        self._load()

    def _load(self):
        try:
            from sentence_transformers import CrossEncoder
            self._model = CrossEncoder(
                self.model_path,
                device=self.device,
                max_length=self.max_length,
            )
            self.available = True
        except Exception as e:
            self.available = False
            self.load_error = str(e)

    def rerank(self, query: str, docs: list, top_n: int = None):
        """
        对候选文档重排，返回按相关度降序的文档列表。
        重排不可用时原样返回（降级）。
        """
        if not docs:
            return []
        if not self.available:
            return docs[:top_n] if top_n else docs

        pairs = [[query, d.page_content[: self.max_length]] for d in docs]
        scores = self._model.predict(pairs)
        scored = sorted(zip(docs, scores), key=lambda x: float(x[1]), reverse=True)
        ranked = [d for d, _ in scored]
        return ranked[:top_n] if top_n else ranked
