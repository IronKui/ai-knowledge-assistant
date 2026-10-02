# -*- coding: utf-8 -*-
"""
可配置检索器 —— 用于构建索引与做检索评测。

设计目的：
1. 与线上知识库隔离（独立 collection + 独立持久化目录），不污染用户数据
2. 关键参数（chunk_size / chunk_overlap / top_k / 是否重排）全部可配置，
   便于做对照实验，量化每个改动带来的指标变化
"""
import os
from pathlib import Path

os.environ.setdefault('HF_ENDPOINT', 'https://hf-mirror.com')

from langchain_chroma import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

EVAL_DIR = Path(__file__).resolve().parent
BASE_DIR = EVAL_DIR.parent                      # backend/
DOCS_DIR = EVAL_DIR / "docs"
CHROMA_DIR = EVAL_DIR / "chroma_eval"           # 评测用独立向量库
MODEL_PATH = str(BASE_DIR / "models/bge-small-zh-v1.5")

# 与线上一致的中文断句优先级
SEPARATORS = ["\n\n", "\n", "。", "！", "？", "；", "，", " ", ""]

_embeddings = None


def get_embeddings():
    """Embedding 单例（本地 BGE-small-zh-v1.5，CPU 推理）"""
    global _embeddings
    if _embeddings is None:
        _embeddings = HuggingFaceEmbeddings(
            model_name=MODEL_PATH,
            model_kwargs={'device': 'cpu'},
            encode_kwargs={'normalize_embeddings': True},
        )
    return _embeddings


def load_pdf(filename: str):
    """加载文档，返回 Document 列表（每页一个 Document）"""
    path = DOCS_DIR / filename
    loader = PyPDFLoader(str(path), extraction_mode="plain")
    docs = loader.load()
    # 丢弃空页（封面等）
    return [d for d in docs if len((d.page_content or "").strip()) > 30]


def split_documents(docs, chunk_size: int = 500, chunk_overlap: int = 10):
    """按指定配置切分"""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=SEPARATORS,
    )
    chunks = splitter.split_documents(docs)
    # 给每个 chunk 编号，便于评测时定位
    for i, c in enumerate(chunks):
        c.metadata["chunk_id"] = i
    return chunks


def build_collection(chunks, collection_name: str):
    """建库（如已存在同名 collection 会先清空，保证实验可重复）"""
    vs = Chroma(
        collection_name=collection_name,
        embedding_function=get_embeddings(),
        persist_directory=str(CHROMA_DIR),
    )
    try:
        existing = vs.get()
        if existing and existing.get("ids"):
            vs.delete(ids=existing["ids"])
    except Exception:
        pass
    vs.add_documents(chunks)
    return vs


def get_collection(collection_name: str):
    """获取已建好的库"""
    return Chroma(
        collection_name=collection_name,
        embedding_function=get_embeddings(),
        persist_directory=str(CHROMA_DIR),
    )


def vector_search(vs, query: str, k: int = 3):
    """纯向量召回"""
    return vs.similarity_search(query, k=k)


def collection_name_for(chunk_size: int, chunk_overlap: int) -> str:
    """按切分配置生成 collection 名，避免实验之间互相污染"""
    return f"eval_cs{chunk_size}_ov{chunk_overlap}"
