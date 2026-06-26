"""
经历记忆模块。用 ChromaDB + Ollama 嵌入模型做语义检索。
存: 文本 → 嵌入 → ChromaDB
搜: 查询 → 嵌入 → 找最相似的 N 条 → 返回原文 + 日期
"""
import chromadb
import requests
from config import EMBED_MODEL_NAME

COLLECTION_NAME = "experiences"

_client = None
_collection = None


def init_store(db_path="./chroma_data"):
    """切换数据库路径。必须在 add_experience / search_experiences 之前调用。"""
    global _client, _collection
    _client = chromadb.PersistentClient(path=db_path)
    _collection = _client.get_or_create_collection(name=COLLECTION_NAME)


def _embed(text):
    """调 Ollama 嵌入 API，返回向量列表 [0.1, 0.8, ...]"""
    resp = requests.post(
        "http://localhost:11434/api/embeddings",
        json={"model": EMBED_MODEL_NAME, "prompt": text},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["embedding"]


def add_experience(text, date_str=""):
    """
    存储一条经历。text 是经历描述，date_str 是日期(如 "2026-06-22")。
    """
    if not text.strip() or _collection is None:
        return

    vector = _embed(text)
    doc_id = str(_collection.count() + 1)  # 简单自增 ID

    _collection.add(
        ids=[doc_id],
        embeddings=[vector],
        documents=[text],
        metadatas=[{"date": date_str}],
    )
    print(f"[经历已存储] {date_str}: {text[:50]}...")


def search_experiences(query, n_results=3):
    """
    语义搜索。返回最相关的 N 条经历，格式 [(文本, 日期), ...]
    """
    if _collection is None or _collection.count() == 0:
        return []

    query_vec = _embed(query)
    results = _collection.query(
        query_embeddings=[query_vec],
        n_results=n_results,
        include=["documents", "metadatas"],
    )

    out = []
    docs = results.get("documents", [[]])[0]
    metas = results.get("metadatas", [[]])[0]
    for doc, meta in zip(docs, metas):
        out.append((doc, meta.get("date", "") if meta else ""))
    return out


# 方便测试
if __name__ == "__main__":
    add_experience("今天学了 Python 爬虫，爬了 B 站排行榜", "2026-06-22")
    add_experience("去泰山爬山，天气很好，风景美", "2026-06-15")
    add_experience("跟朋友吃了火锅，聊了很多", "2026-06-20")

    print("\n检索 '户外活动':", search_experiences("户外活动"))
    print("检索 '编程学习':", search_experiences("编程学习"))
