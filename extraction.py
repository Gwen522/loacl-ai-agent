"""
对话信息提取模块。
在每次退出时调 LLM 分析对话，自由提取用户信息。
"""

import json
from datetime import datetime
from llm_client import chat_sync


# ========== ① 提取核心逻辑 ==========

def extract_insights(messages, current_user_facts):
    """
    调 LLM 分析对话，返回 (新事实, 人格信号)。
    LLM 可以自由创建新字段名，不限制。
    """
    # 对话转文本
    lines = []
    for msg in messages:
        role = "用户" if msg["role"] == "user" else "AI"
        lines.append(f"{role}: {msg['content']}")
    transcript = "\n".join(lines)

    prompt = f"""分析以下对话，提取用户的个人信息。

【当前已知】
{json.dumps(current_user_facts, ensure_ascii=False, indent=2)}

【本次对话】
{transcript}

返回 JSON（只返回 JSON）：
{{
  "user_facts": {{
    // 自由命名字段名。已有的字段继续用，新信息创建合适的字段名
    // 例如："location": "上海", "favorite_books": ["三体"], "friends": ["小明"]
    // 列表字段放数组，单值字段放字符串，复合信息放对象
  }},
  "persona_signals": [
    // 用户对 AI 风格的偏好，无则空数组
  ]
}}

规则：
- 只记录用户明确陈述的个人信息（居住地、年龄、兴趣、职业、学历、技能、长期喜好等）
- 禁止记录：未来计划、临时状态、日历日程、考试安排、推断联想
  正例: location=上海, interests=[骑行]  反例: upcoming_events=[考试], next_trip=天津
- 字段名英文小写，下划线分隔。无新内容返回空对象
- persona_signals 不编造"""

    resp = chat_sync([
        {"role": "system", "content": "信息提取助手。只返回 JSON，不解释。主动为每类信息创建合适的字段名。"},
        {"role": "user", "content": prompt},
    ], timeout=60)

    if resp is None:
        return None, None

    # 解析 JSON（容错 markdown 包裹）
    try:
        text = resp.strip()
        if text.startswith("```"):
            parts = text.split("\n")
            text = "\n".join(parts[1:-1] if parts[-1].strip() == "```" else parts[1:])
        data = json.loads(text)
        return data.get("user_facts", {}), data.get("persona_signals", [])
    except json.JSONDecodeError:
        print(f"[提取失败] LLM 返回无法解析: {resp[:200]}")
        return None, None


# ========== ② 合并用户事实 ==========

def merge_user_facts(existing, new_facts):
    """按字段类型智能合并：list 追加去重、str 替换、dict 合并、新字段直接加。"""
    if not new_facts:
        return existing

    for key, val in new_facts.items():
        if not val:
            continue

        if key in existing:
            old = existing[key]

            if isinstance(old, list) and isinstance(val, list):
                seen = {str(v).lower().strip() for v in old if v}
                for v in val:
                    if v and str(v).lower().strip() not in seen:
                        old.append(v)
                        seen.add(str(v).lower().strip())
                        print(f"  [新增 {key}: {v}]")

            elif isinstance(old, dict) and isinstance(val, dict):
                for k, v in val.items():
                    if v:
                        old[k] = v
                        print(f"  [更新 {key}.{k}: {v}]")

            elif isinstance(old, str) and isinstance(val, str):
                if val != old:
                    existing[key] = val
                    print(f"  [更新 {key}: {old[:30]} → {val[:30]}]")

            else:
                print(f"  [跳过 {key}: 类型不匹配]")
        else:
            existing[key] = val
            print(f"  [新建字段 {key}: {val}]")

    return existing


# ========== ③ 人格建议 ==========

def save_persona_suggestions(signals, filename="persona_suggestions.json"):
    """人格偏好写入文件，人工审查，不自动改人设。"""
    if not signals:
        return
    try:
        with open(filename, "r") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        data = {"suggestions": []}

    now = datetime.now().isoformat(timespec="minutes")
    for s in signals:
        data["suggestions"].append({"timestamp": now, "observation": s, "applied": False})

    with open(filename, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"[人格建议已保存到 {filename}，{len(data['suggestions'])} 条待审查]")


# ========== ④ 经历提取 ==========

def extract_experiences(messages):
    """
    从最近对话中提取值得记住的经历（做了什么、去了哪里、成就等）。
    返回 [(描述文本, 日期), ...] 列表。
    """
    lines = []
    for msg in messages:
        role = "用户" if msg["role"] == "user" else "AI"
        lines.append(f"{role}: {msg['content']}")
    transcript = "\n".join(lines)

    prompt = f"""从以下对话中提取用户值得记住的经历（做了什么事、去了哪里、取得了什么成就等）。
每条用一句简短的中文描述，只返回 JSON 数组。如果没什么值得记的，返回空数组。

对话:
{transcript}

只返回 JSON 数组，如: ["去泰山爬山", "学完了 Python 基础课程"]"""

    resp = chat_sync([
        {"role": "system", "content": "经历提取助手。只返回 JSON 字符串数组。"},
        {"role": "user", "content": prompt},
    ], timeout=30)

    if not resp:
        return []

    try:
        text = resp.strip()
        if text.startswith("```"):
            parts = text.split("\n")
            text = "\n".join(parts[1:-1] if parts[-1].strip() == "```" else parts[1:])
        items = json.loads(text)
        if isinstance(items, list):
            today = datetime.now().strftime("%Y-%m-%d")
            return [(item, today) for item in items if isinstance(item, str)]
    except (json.JSONDecodeError, Exception):
        pass
    return []
