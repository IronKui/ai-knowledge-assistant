# -*- coding: utf-8 -*-
"""下载 bge-reranker-base 重排模型（走国内镜像）"""
import os
import sys

os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
os.environ.setdefault('HF_HUB_DISABLE_SYMLINKS_WARNING', '1')

from huggingface_hub import hf_hub_download, list_repo_files

REPO = 'BAAI/bge-reranker-base'
LOCAL = r'E:\study-hermes\AI_project\MyProject\langchain-learn\backend\models\bge-reranker-base'

files = list_repo_files(REPO)
print("仓库文件清单:")
for f in files:
    print("  ", f)

# 必需文件：配置 + 分词器 + 权重
need = [f for f in files if f in (
    'config.json', 'special_tokens_map.json', 'tokenizer.json',
    'tokenizer_config.json', 'vocab.txt', '1_Pooling/config.json',
    'pytorch_model.bin', 'model.safetensors',
)]

print(f"\n待下载 {len(need)} 个文件")
for f in need:
    try:
        p = hf_hub_download(REPO, f, local_dir=LOCAL)
        size = os.path.getsize(p) / (1024 * 1024)
        print(f"  完成 {f}  ({size:.1f} MB)")
    except Exception as e:
        print(f"  失败 {f}: {e}")

print("\n下载结束")
