"""
会话管理模块 — chat.py 和 server.py 共享的持久化和上下文逻辑。
两个「门面」共用同一套：加载/保存/压缩/上下文构建。
"""
import json
import os
from llm_client import chat_sync
from tools.calendar import set_calendar_path
from experience_store import init_store

MAX_CONTEXT = 8


# ========== 模式 & 目录 ==========

def data_dir(mode="dev") -> str:
    """模式 → 数据目录"""
    return "personal" if mode == "real" else "dev_data"


def clean_dev():
    """清空测试数据（保留 persona 和 user_facts）"""
    import shutil
    for f in ["memory.json", "suggestions.json", "calendar.json"]:
        try:
            os.remove(f"dev_data/{f}")
        except FileNotFoundError:
            pass
    try:
        shutil.rmtree("dev_data/chroma")
    except FileNotFoundError:
        pass


# ========== 加载 / 保存 ==========

def load_persona(d: str) -> dict:
    """加载 persona，不存在则自动创建默认"""
    path = f"{d}/persona.json"
    try:
        with open(path) as f:
            return json.load(f)
    except FileNotFoundError:
        p: dict = {"name": "银月", "persona": "是用户的助手。", "rules": []}
        os.makedirs(d, exist_ok=True)
        with open(path, "w") as f:
            json.dump(p, f, ensure_ascii=False, indent=2)
        return p


def load_user_facts(d: str) -> dict:
    """加载 user_facts，不存在则自动创建空白"""
    path = f"{d}/user_facts.json"
    try:
        with open(path) as f:
            return json.load(f)
    except FileNotFoundError:
        facts: dict = {"name": "", "grade": "", "interests": [], "traits": [],
                       "dislikes": [], "pets": [], "family": {},
                       "important_events": [], "note": ""}
        os.makedirs(d, exist_ok=True)
        with open(path, "w") as f:
            json.dump(facts, f, ensure_ascii=False, indent=2)
        return facts


def load_memory(d: str) -> list:
    """从 memory.json 读回对话历史"""
    path = f"{d}/memory.json"
    try:
        with open(path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_memory(d: str, messages: list):
    """保存对话到 memory.json"""
    with open(f"{d}/memory.json", "w") as f:
        json.dump(messages, f, ensure_ascii=False)


def save_user_facts(d: str, facts: dict):
    with open(f"{d}/user_facts.json", "w") as f:
        json.dump(facts, f, ensure_ascii=False, indent=2)


# ========== 上下文压缩 ==========

def compress_history(old_messages: list) -> str:
    """将一组旧消息压成 2-3 句摘要"""
    if not old_messages:
        return ""
    lines = []
    for m in old_messages:
        role = "用户" if m["role"] == "user" else "AI"
        lines.append(f"{role}: {m['content']}")
    text = "\n".join(lines)
    return chat_sync([
        {"role": "system",
         "content": "你是一个对话摘要助手。将以下对话压成2-3句简洁摘要，只保留关键事件、决定、情感。只返回摘要文本，不加解释。"},
        {"role": "user", "content": f"请摘要：\n{text}"},
    ], timeout=30)


def build_context(messages: list, history_notes: list,
                  compressed_count: int, max_ctx=MAX_CONTEXT):
    """
    返回 (context_messages, history_notes, new_compressed_count)。
    messages 超 max_ctx 时自动压缩旧消息。
    """
    if len(messages) <= max_ctx:
        return list(messages), list(history_notes), compressed_count

    overflow = len(messages) - max_ctx
    if overflow > compressed_count + 4:  # 避免频繁压缩
        summary = compress_history(messages[:overflow])
        if summary:
            history_notes.append(summary)
        compressed_count = overflow

    return messages[-max_ctx:], list(history_notes), compressed_count


# ========== 初始化辅助 ==========

def init_stores(d: str):
    """初始化向量库 + 日历路径"""
    os.makedirs(d, exist_ok=True)
    init_store(f"{d}/chroma")
    set_calendar_path(f"{d}/calendar.json")


def init_session(mode="dev"):
    """
    一站式初始化：返回 (data_dir, persona, user_facts, messages, suggestions_file)。
    如果 mode == "clean"，先清空测试数据。
    """
    if mode == "clean":
        clean_dev()
        mode = "dev"

    d = data_dir(mode)
    init_stores(d)
    return d, load_persona(d), load_user_facts(d), load_memory(d)
