# -*- coding: utf-8 -*-
"""建库 + 探查：看清切分后的 chunk 长什么样，为构造评测集做准备"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from retriever import load_pdf, split_documents, build_collection, collection_name_for

DOC_NAME = "阿里巴巴Java开发手册v1.4.0.pdf"
CHUNK_SIZE = 500
CHUNK_OVERLAP = 10

print("加载文档...")
docs = load_pdf(DOC_NAME)
print(f"有效页数: {len(docs)}")

print(f"切分配置: chunk_size={CHUNK_SIZE}, overlap={CHUNK_OVERLAP}")
chunks = split_documents(docs, CHUNK_SIZE, CHUNK_OVERLAP)
print(f"chunk 总数: {len(chunks)}")

lens = [len(c.page_content) for c in chunks]
lens.sort()
print(f"chunk 长度: 最短={lens[0]}, 中位={lens[len(lens)//2]}, 最长={lens[-1]}, 平均={sum(lens)//len(lens)}")

print("\n建库...")
name = collection_name_for(CHUNK_SIZE, CHUNK_OVERLAP)
vs = build_collection(chunks, name)
print(f"collection: {name} 已就绪")

print("\n" + "=" * 70)
print("抽样 chunk（用于构造评测集）")
print("=" * 70)
step = max(len(chunks) // 6, 1)
for i in range(0, len(chunks), step):
    c = chunks[i]
    page = c.metadata.get("page", "?")
    print(f"\n[chunk_id={c.metadata['chunk_id']} | 第{int(page)+1 if isinstance(page,int) else page}页 | 长度{len(c.page_content)}]")
    print(c.page_content[:300].replace("\n", " "))
