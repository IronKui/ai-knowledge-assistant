# -*- coding: utf-8 -*-
"""检查规范文档 PDF 的解析质量：页数、字数、章节结构"""
import sys
from pathlib import Path

DOCS_DIR = Path(__file__).resolve().parent / "docs"
pdf_path = DOCS_DIR / "阿里巴巴Java开发手册v1.4.0.pdf"

try:
    from pypdf import PdfReader
except ImportError:
    from PyPDF2 import PdfReader

reader = PdfReader(str(pdf_path))
print(f"文件: {pdf_path.name}")
print(f"页数: {len(reader.pages)}")

total_chars = 0
pages_text = []
for i, page in enumerate(reader.pages):
    t = page.extract_text() or ""
    pages_text.append(t)
    total_chars += len(t)

print(f"总字符数: {total_chars}")
print(f"平均单页字符: {total_chars // max(len(reader.pages), 1)}")
print()
print("=" * 60)
print("前 3 页内容预览（判断解析是否正常）")
print("=" * 60)
for i in range(min(3, len(pages_text))):
    print(f"\n--- 第 {i+1} 页 ---")
    print(pages_text[i][:600])

print()
print("=" * 60)
print("寻找章节标题（含'规约'的行）")
print("=" * 60)
count = 0
for i, t in enumerate(pages_text):
    for line in t.split("\n"):
        line = line.strip()
        if line.endswith("规约") and len(line) < 20:
            print(f"  p{i+1}: {line}")
            count += 1
            break
print(f"\n章节数(约): {count}")
