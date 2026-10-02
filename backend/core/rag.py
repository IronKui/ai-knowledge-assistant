from pathlib import Path
from langchain_chroma import Chroma
from datetime import datetime

import hashlib
import uuid
from langchain_community.document_loaders import TextLoader, UnstructuredMarkdownLoader, Docx2txtLoader, JSONLoader, \
    PyPDFLoader
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from core.index_manager import auto_rename
from core.user_repository import get_file_by_hash, get_file_by_source, add_user_file
from core.logger import setup_logger
from core.cache import get_cached_search, set_cached_search, clear_user_cache
from core.reranker import Reranker

import threading

import os
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'

BASE_DIR = Path(__file__).resolve().parent.parent

# ========== 检索策略配置（数值来自 evaluation/REPORT.md 的实测结论）==========
CHUNK_SIZE = 500          # 切分粒度：需与重排模型 512 token 上限对齐
CHUNK_OVERLAP = 10
ENABLE_RERANK = True      # 两阶段检索开关
RECALL_K = 20             # 向量粗召回条数（先保召回率）
RERANK_TOP_K = 3          # 精排后最终送入 LLM 的条数（再保精准度）

_reranker = None          # 重排模型缓存（单例）

# ========== 全局变量（定义在这里） ==========
vectorstore = None
_vectorstore_lock = threading.Lock()
_embeddings = None   # Embedding 模型缓存


def get_vectorstore():
    """线程安全获取 vectorstore（双重检查锁）"""
    global vectorstore
    if vectorstore is not None:
        return vectorstore
    with _vectorstore_lock:
        if vectorstore is None:
            vectorstore = Chroma(
                collection_name="mvp_knowledge",
                embedding_function=get_embeddings(),
                persist_directory=str(BASE_DIR / "chroma_db")
            )
    return vectorstore

# 自动创建当前模块的 logger
logger = setup_logger(__name__)

# 加载 文档:
def load_file(filepath,user_id="default", scope="account", session_id="default"):
    """
    加载文档，将文档处理为list字符串列表
    """
    logger.info(f"开始加载文件：{filepath}")
    path = Path(filepath)

    #获取后缀名
    suffixes = path.suffix.lower()

    #按后缀操作
    #单个：
    # if suffixes == '.txt':
    #     #加载txt：
    #     txt_loder= TextLoader(file_path = filepath ,encoding = 'utf-8')
    #     #转为list列表
    #     docs = txt_loder.load() #返回List列表(Document对象)
    #     return docs
    if suffixes == '.txt':
        loder = TextLoader(filepath, encoding='utf-8')
    elif suffixes == '.md':
        loder = TextLoader(filepath, encoding='utf-8')
    elif suffixes == '.docx':
        loder = Docx2txtLoader(filepath)
    elif suffixes == '.json':
        loder = JSONLoader(filepath, "." ,False)
    elif suffixes == '.pdf':
        loder = PyPDFLoader(filepath,extraction_mode= "plain")
    elif suffixes == '.png' or suffixes == '.jpg' or suffixes == '.jpeg':
        return load_image(filepath)
    docs = loder.load()
    #todo ：添加一次性读取多个文件的内容，读File Directory

    #打标签，做溯源和去重
    with open(filepath,"rb") as f:
        file_hash = hashlib.sha256(f.read()).hexdigest() #文件内容哈希

    #去重
    final_name =remove_duplicates(file_hash,filepath,user_id)
    if final_name is None:
        return None #重复跳过

    doc_id = str(uuid.uuid4())  # 一次上传共用一个文档ID

    for doc in docs:
        doc.metadata["source"] = final_name  # 文件名
        doc.metadata["file_hash"] = file_hash  # 内容哈希
        doc.metadata["upload_time"] = datetime.now().isoformat()  # 上传时间
        doc.metadata["doc_id"] = doc_id  # 文档唯一ID
        doc.metadata["user_id"] = user_id  # 所属用户
        doc.metadata["scope"] = scope  # 可见范围：account（账号级）/ session（会话级）
        doc.metadata["session_id"] = session_id  # 会话级时限定会话


    logger.info(f"加载完毕")
    return docs

def load_image(filepath):
    """读取图片，返回 Document 列表"""
    # TODO: 用 pytesseract 或 多模态大模型
    raise NotImplementedError("图片OCR功能开发中")

def remove_duplicates(file_hash,filepath, user_id):
    '''去重，返回最终文件名；重复返回 None'''
    #获取文件内容哈希

    #硬重复，看账号索引库里有无同hash
    if get_file_by_hash(user_id,file_hash):
        logger.info(f"文件{filepath}内容已存在，跳过入库")
        return  None
    #同名文件进行重命名：
    path =Path(filepath)
    source = path.name
    if get_file_by_source(user_id,source):
        logger.info(f"存在同名文件，进行重命名")
        return auto_rename(source)
    return source

#递归字符文本切分器
def splitter_documents(docs):
    """
    文本切割器，使用递归字符文本切割器
    """
    logger.info(f"开始进行文本切分")
    #1.创建分割器对象
    text_split = RecursiveCharacterTextSplitter(
        # 500 是实测最优值：需与重排模型 512 token 上限对齐，
        # 调大到 800 会导致 60% 文本块被截断，重排后 Recall 反而从 0.940 跌到 0.760
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", "。", "！", "？", "；", "，", " ", ""]
    )
    #2.切割
    chunks = text_split.split_documents(docs)  # ← 注意是 split_documents
    logger.info(f"切分完毕")
    return chunks

#向量化
def get_embeddings():
    """获取 Embedding 模型（单例模式，只加载一次）"""
    global _embeddings
    if _embeddings is not None:
        return _embeddings
    local_model_path = str(BASE_DIR / "models/bge-small-zh-v1.5")

    # 检查本地模型是否存在
    if os.path.exists(local_model_path) and os.path.exists(
            os.path.join(local_model_path, "model.safetensors")):
        logger.info(f"使用本地模型：{local_model_path}")
        # 修复：本地分支原本未写入 _embeddings，导致单例失效、每次调用都重新加载模型
        _embeddings = HuggingFaceEmbeddings(
            model_name=local_model_path,
            model_kwargs={'device': 'cpu'},
            encode_kwargs={'normalize_embeddings': True}
        )
        return _embeddings

    logger.info("本地模型不存在或不完整，从 Hugging Face 镜像站下载...")
    os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
    _embeddings = HuggingFaceEmbeddings(
        model_name="BAAI/bge-small-zh-v1.5",
        model_kwargs={'device': 'cpu'},
        encode_kwargs={'normalize_embeddings': True}
    )
    return _embeddings
def store_to_vectorstore(chunks,user_id="default", file_size=0):
    """
    存入向量数据库
    """
    logger.info(f"进行向量化")
    global vectorstore
    #如果没有向量库就创建一个
    vs = get_vectorstore()
    vs.add_documents(chunks)
    #写入 user_files 表（企业级文件管理，替代 JSON 索引）
    first = chunks[0]
    add_user_file(
        user_id,
        first.metadata["source"],
        first.metadata["file_hash"],
        file_size=file_size,
        chunk_count=len(chunks),
        scope=first.metadata.get("scope", "account"),
        session_id=first.metadata.get("session_id", ""),
    )

    logger.info(f"文件向量化存入完毕")
    return

def get_reranker() -> Reranker:
    """获取重排器（单例，模型只加载一次；不可用时内部自动降级）"""
    global _reranker
    if _reranker is None:
        _reranker = Reranker()
        if _reranker.available:
            logger.info("重排模型加载成功：BAAI/bge-reranker-base")
        else:
            logger.warning(f"重排模型不可用，检索将降级为纯向量检索：{_reranker.load_error}")
    return _reranker


def search_knowledge_base(query:str, k: int = RERANK_TOP_K, user_id ="default", session_id="default") -> list:
    """
    两阶段检索：向量粗召回 → CrossEncoder 精排

    阶段一：向量检索召回 RECALL_K 条（保召回率）
    阶段二：重排模型精排取前 k 条（保精准度）

    实测（evaluation/REPORT.md，50 条标注评测集）：
      baseline 向量 Top-3      Recall@3 0.740 / MRR 0.650
      本方案                   Recall@3 0.940 / MRR 0.940

    过滤规则：
    - 账号级文件（scope=account）：属于该用户即可检索
    - 会话级文件（scope=session）：属于该用户且属于当前会话
    """
    # 先查缓存（热点检索结果）
    cached = get_cached_search(user_id, session_id, query, k)
    if cached is not None:
        return cached

    vs = get_vectorstore()
    #过滤条件：user_id 匹配 且（账号级 或 会话级且当前会话）
    filter_condition = {
        "$and": [
            {"user_id": user_id},
            {"$or": [
                {"scope": "account"},
                {"$and": [
                    {"scope": "session"},
                    {"session_id": session_id}
                ]}
            ]}
        ]
    }
    #先判断该用户是否有内容
    count = vs.get(where={"user_id":user_id})["ids"]
    if not count:
        logger.info(f"用户{user_id}的知识库为空")
        return []

    # ===== 阶段一：向量粗召回 =====
    # 重排开启时召回更多候选，把"找得到"交给粗召回，把"排得准"交给重排
    recall_k = RECALL_K if ENABLE_RERANK else k
    logger.info(f"检索问题：{query[:50]}...（粗召回 {recall_k} 条）")
    candidates = vs.similarity_search(query, k=recall_k, filter=filter_condition)

    # ===== 阶段二：CrossEncoder 精排 =====
    if ENABLE_RERANK and candidates:
        results = get_reranker().rerank(query, candidates, top_n=k)
        logger.info(f"重排完成：{len(candidates)} → {len(results)} 条")
    else:
        results = candidates[:k]

    logger.info(f"最终返回 {len(results)} 个文本块")

    # 写入缓存
    set_cached_search(user_id, session_id, query, k, results)

    return results

def process_and_store(filepath: str, user_id="default", scope="account", session_id="default") -> int:
  """加载文件 → 切分 → 入库，返回文本块数量"""
  docs = load_file(filepath, user_id, scope, session_id)
  if docs is None:
      return 0, "duplicate"  # 重复，跳过
  file_size = os.path.getsize(filepath)  # 真实文件大小
  chunks = splitter_documents(docs)
  store_to_vectorstore(chunks, user_id, file_size)
  clear_user_cache(user_id)  # 知识库变动，清缓存避免旧数据
  return len(chunks), "ok"

