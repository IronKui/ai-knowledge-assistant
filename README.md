# RAG 知识库问答系统

面向研发团队的规范知识库问答系统 —— 支持**多用户私有知识库**、**两阶段检索**与**检索效果评测体系**。

本地部署，全链路离线：Embedding 与重排模型均在本地运行，不依赖云端 API。

---

## 📊 核心数据

针对《阿里巴巴 Java 开发手册》构建 50 条人工标注评测集，优化前后检索效果对比：

| 阶段 | Recall@3 | MRR | NDCG@3 |
|:---|:---:|:---:|:---:|
| 基线（向量 Top-3） | 0.740 | 0.650 | 0.673 |
| **优化后（粗召回 20 → 重排取 3）** | **0.940** | **0.940** | **0.940** |
| 提升 | **+27.0%** | **+44.6%** | **+39.7%** |

> MRR 涨幅（+44.6%）显著高于 Recall（+27.0%）——重排序的价值不只是「多找到几条」，
> 而是**把正确答案提到第一位**，这才是 RAG 生成质量的关键。

---

## 💡 为什么做这个

企业内部的规范文档（开发手册、制度、流程）通常是几十页的长 PDF，存在两个问题：

1. **人工查阅成本高** —— 「线程池怎么创建」这类问题要翻遍全文才能定位到某一条规约
2. **关键词搜索不准** —— 搜「重写方法」匹配不到文档里的「覆写方法」

直接用大模型回答会**编造**（规范文档不在训练数据里），而朴素 RAG 的检索质量又不够。
所以这个项目的重点不是「接一个大模型」，而是**把检索做准，并用数据证明它准了**。

---

## 🏗 技术架构

### 离线链路（文档入库）

```
文档（PDF/DOCX/MD/TXT）
    ↓ 解析（pypdf / Docx2txtLoader）
文本块
    ↓ 切分（RecursiveCharacterTextSplitter，中文优先断句，chunk=500/overlap=10）
Chunks（携带 user_id / scope / session_id 元数据）
    ↓ 向量化（BAAI/bge-small-zh-v1.5，本地）
Chroma 向量库（持久化）
```

### 在线链路（问答）

```
用户提问
    ↓
向量粗召回 Top-20（带 user_id + scope 元数据过滤）
    ↓
bge-reranker-base 精排（CrossEncoder）
    ↓
取 Top-3 → 组装 Prompt（含来源标注）
    ↓
DeepSeek 生成回答 → 返回答案 + 溯源信息
```

### Agent 层

基于 LangChain 的 `create_agent` 构建工具调用型 Agent，挂载三个工具：

| 工具 | 作用 |
|:---|:---|
| `retrieve_tool` | 检索知识库回答问题 |
| `quiz_tool` | 根据知识库内容出题 |
| `evaluate_tool` | 评判用户答案，给出得分与解析 |

- 会话状态用 LangGraph 的 `SqliteSaver` 做 checkpoint 持久化，
  `thread_id` 采用 `user_id:session_id` 复合键，实现「用户 + 会话」双维隔离
- 用户上下文通过 `context_schema` 运行时注入，Agent 按模式全局复用，
  避免按用户或会话创建实例导致内存膨胀
- 长对话由摘要中间件处理：历史超 4000 token 自动压缩，保留最近 2000 token
- 支持 4 种模式（学习 / 面试 / 角色扮演 / 默认），通过系统 Prompt 区分行为

---

## 🔬 评测体系（本项目的核心差异化）

**大多数 RAG 项目只能演示「能跑」，这个项目能回答「效果好多少」。**

### 评测集

- 50 条人工标注问答对，覆盖《阿里巴巴 Java 开发手册》7 个维度
- 难度分布：easy 14 / medium 26 / hard 10
- 每条含**标准答案片段**（golden snippet）

### 指标

| 指标 | 含义 | 为什么看它 |
|:---|:---|:---|
| **Recall@K** | 前 K 条中命中标准答案的比例 | 衡量「找不找得到」——决定生成阶段有没有正确素材 |
| **MRR** | 首个命中结果排名的倒数均值 | 衡量「第一条对不对」——LLM 对靠前内容注意力更高 |
| **NDCG@K** | 折损累积增益归一化 | 综合衡量「命中且靠前」 |

> 命中判定：chunk 与标准片段均做去空白归一化后包含匹配，规避 PDF 抽取时中文与数字间插空格的干扰。

### 关键发现：单独最优 ≠ 组合最优 ⚠️

阶段 A 显示 `chunk=800` 的 Recall 最高（0.800），阶段 B 显示重排序收益最大。
**两者叠加后效果反而大幅下降**：

| 配置 | Recall@3 | MRR |
|:---|:---:|:---:|
| chunk=500 + 重排（B2） | **0.940** | **0.940** |
| chunk=800 + 重排（C1） | 0.760 ❌ | 0.697 ❌ |

**根因**：`bge-reranker-base` 的位置编码上限是 **512 token**。
chunk=800 时有 **60% 的文本块被截断**，其中 13 道题的标准答案正好落在被截掉的尾段，
CrossEncoder 只看到前半段，反而把正确的块排到了后面。

**结论**：切分粒度必须与重排模型的长度上限对齐，不能只看单一环节的指标。

→ 完整实验过程见 [`backend/evaluation/REPORT.md`](backend/evaluation/REPORT.md)

### 复现

```bash
cd backend/evaluation
python evaluate.py        # baseline
python experiment.py      # 阶段 A（切分对比）+ B（重排序）
python experiment_c.py    # 阶段 C（组合验证）+ 失败案例归因
```

---

## 🚀 快速开始

### 1. 环境

```bash
conda create -n rag python=3.10
conda activate rag
pip install -r backend/requirements.txt
```

### 2. 下载模型（约 1.5 GB）

模型权重体积过大，不入库。需自行下载到 `backend/models/`：

```bash
# 设置 HuggingFace 镜像（国内）
export HF_ENDPOINT=https://hf-mirror.com     # Windows: $env:HF_ENDPOINT="https://hf-mirror.com"
```

需要两个模型：

| 模型 | 用途 | 放置路径 |
|:---|:---|:---|
| `BAAI/bge-small-zh-v1.5` | 向量化 | `backend/models/bge-small-zh-v1.5/` |
| `BAAI/bge-reranker-base` | 重排序 | `backend/models/bge-reranker-base/` |

可利用 `backend/evaluation/download_reranker.py` 辅助下载。

### 3. 下载评测语料（**跑评测才需要**）

评测集基于《阿里巴巴 Java 开发手册》v1.4.0 构建，该文档版权归原作者所有，**不入库**。
如需复现评测数据，请自行下载 PDF 并放置到：

```
backend/evaluation/docs/阿里巴巴Java开发手册v1.4.0.pdf
```

可从阿里官方 p3c 项目或其公开 CDN 获取，例如：

```
https://ucc.alicdn.com/download/%E9%98%BF%E9%87%8C%E5%B7%B4%E5%B7%B4Java%E5%BC%80%E5%8F%91%E6%89%8B%E5%86%8C1.4.0.pdf
```

> 只跑问答主流程不需要这一步，跳过即可。

### 4. 配置环境变量

```bash
cp backend/.env.example backend/.env     # Windows: copy
```

填入 DeepSeek API Key 与 JWT 密钥（生成：`python -c "import secrets; print(secrets.token_hex(32))"`）。

### 5. 启动 Redis（可选）

未启动时缓存功能自动降级，不影响主流程。

```bash
redis-server
```

### 6. 启动后端

```bash
cd backend
uvicorn app:app --reload
```

API 文档：http://127.0.0.1:8000/docs

### 7. 启动前端

```bash
cd frontend
npm install
npm run dev
```

访问 http://localhost:5173

---

## 📁 目录结构

```
.
├── backend/                    # 后端（FastAPI + LangChain）
│   ├── app.py                  # 接口入口（路由 / 中间件 / 生命周期）
│   ├── schemas.py              # Pydantic 请求响应模型
│   ├── chat.html               # 轻量前端（无需构建，联调用）
│   ├── core/
│   │   ├── rag.py              # RAG 链路（解析 / 切分 / 检索 / 两阶段检索）
│   │   ├── reranker.py         # 重排模型封装（单例 + 降级 + 长度截断）
│   │   ├── agent.py            # Agent 定义 + 会话历史读取
│   │   ├── tools.py            # 工具定义（检索 / 出题 / 评判）
│   │   ├── prompts.py          # 多模式提示词
│   │   ├── middleware.py       # 上下文摘要压缩
│   │   ├── auth_service.py     # 账号业务（密码哈希 / JWT）
│   │   ├── user_repository.py  # 数据访问层（用户 / 会话 / 消息 / 文件）
│   │   └── cache.py            # Redis 缓存封装
│   ├── evaluation/             # 检索效果评测体系 ⭐
│   │   ├── eval_dataset.json   # 50 条人工标注评测集
│   │   ├── evaluate.py         # 指标实现（Recall@K / MRR / NDCG@K）
│   │   ├── experiment*.py      # 阶段 A/B/C 对照实验
│   │   ├── hybrid.py           # BM25 混合检索（实验中，暂无结论）
│   │   ├── REPORT.md           # 完整实验报告
│   │   ├── results/            # 实验数据
│   │   └── docs/               # 评测语料 PDF（需自行下载，不入库）
│   └── models/                 # 模型权重（需自行下载，不入库）
└── frontend/                   # 前端（Vue 3 + Vite）
    └── src/
        ├── views/              # LoginView / ChatView
        └── components/         # Sidebar / MessageArea
```

---

## 🎯 关键设计决策

### 1. 为什么用本地 BGE 而不是 API Embedding

- **成本**：50 条评测集要反复跑实验，API 调用成本高且不可控
- **离线**：企业内网场景可能无法访问外部 API
- **可控**：模型版本固定，实验结果可复现

### 2. 为什么用两阶段检索

单阶段向量检索受限于「语义相近但字面不匹配」的盲区。
粗召回（保 Recall）+ 精排（保 MRR）分工明确，实测 MRR 从 0.650 提升到 0.940。

### 3. 为什么 chunk=500（而不是更大的 800）

**切分粒度必须与重排模型的 512 token 上限对齐**。
chunk=800 在纯向量检索下指标更好，但与重排组合时因截断导致 60% 的块信息丢失，效果反而下降。
详见[评测报告](backend/evaluation/REPORT.md)阶段 C。

### 4. 为什么强制元数据过滤下推到向量库

多用户场景下，**过滤必须在向量检索层完成**，而不是召回后再过滤。
否则「召回 20 条 → 过滤掉别人的 18 条 → 只剩 2 条」会造成严重的信息损失。

### 5. 降级设计

任何一环失效都不阻断主流程：

```
重排失败 → 退回纯向量检索 → 退回 Redis 缓存 → 空结果提示
Redis 未启动 → 自动禁用缓存
```

---

## 📄 License

本项目仅用于学习与技术演示。评测语料《阿里巴巴 Java 开发手册》版权归原作者所有。
