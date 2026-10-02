# -*- coding: utf-8 -*-
"""
重排序（Rerank）模块 —— 生产版
==============================
为什么需要重排序：
  向量检索（Bi-Encoder）把 query 和文档各自独立编码成向量后算余弦相似度。
  优点是快（文档向量可离线算好）、可海量召回；缺点是 query 与文档之间没有
  充分交互，对精确语义匹配不敏感。

  CrossEncoder（重排）把 query 和文档拼在一起送进模型联合打分，精度显著更高，
  但必须对候选逐一计算、无法离线预存，所以只适合对少量候选做精排。

  工业界标准做法是两阶段检索：
    向量粗召回 Top-N（N 较大，保证召回率）
      → CrossEncoder 精排取 Top-K（K 较小，保证喂给 LLM 的内容精准）

本项目的实测结论（见 evaluation/REPORT.md）：
  baseline（向量 Top-3）        Recall@3 0.740 / MRR 0.650
  向量 Top-20 → 重排 Top-3     Recall@3 0.940 / MRR 0.940

重要约束：
  bge-reranker-base 位置编码上限为 512 token，超长文本会被截断。
  因此切分粒度必须与该上限对齐（本项目 chunk_size=500）。
  若把 chunk 调大到 800，60% 的文本块会被截断，重排后 Recall 反而跌到 0.760。

降级策略：
  模型缺失 / 加载失败 / 推理异常时自动退回向量检索结果，
  保证一个可选组件不会拖垮主链路。
"""
import os
import threading
from pathlib import Path

os.environ.setdefault('HF_ENDPOINT', 'https://hf-mirror.com')

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_MODEL_PATH = str(BASE_DIR / "models" / "bge-reranker-base")

# CrossEncoder 的长度上限，超过将被截断；切分粒度需与之对齐
MAX_LENGTH = 512


class Reranker:
    """CrossEncoder 重排器（单例模式，模型只加载一次）"""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self, model_path: str = None, device: str = "cpu", max_length: int = MAX_LENGTH):
        if getattr(self, "_initialized", False):
            return
        self.model_path = model_path or DEFAULT_MODEL_PATH
        self.device = device
        self.max_length = max_length
        self._model = None
        self.available = False
        self.load_error = None
        self._load()
        self._initialized = True

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
        重排不可用时原样返回（降级），不影响主链路可用性。
        """
        if not docs:
            return []
        if not self.available:
            return docs[:top_n] if top_n else docs

        try:
            # 截断到模型长度上限，避免长文本撑爆位置编码
            pairs = [[query, d.page_content[: self.max_length]] for d in docs]
            scores = self._model.predict(pairs)
            scored = sorted(zip(docs, scores), key=lambda x: float(x[1]), reverse=True)
            ranked = [d for d, _ in scored]
            return ranked[:top_n] if top_n else ranked
        except Exception as e:
            # 推理异常同样降级，绝不因重排失败导致检索整体失败
            self.load_error = str(e)
            return docs[:top_n] if top_n else docs
