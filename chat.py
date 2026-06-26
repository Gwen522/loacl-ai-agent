import gnureadline  # 修复 macOS 中文输入退格问题（必须在其他 import 之前）
from llm_client import chat_sync, chat_with_tools, chat_with_tools_stream, chat_stream
from extraction import extract_insights, merge_user_facts, save_persona_suggestions, extract_experiences
from tools import TOOLS, build_ollama_tools  # Agent 工具集 + schema 构建器
from experience_store import add_experience, search_experiences, init_store  # 向量数据库
import json  # 用 json 库解析 JSON
import sys   # 用 sys 库读取命令行参数
import os    # 用 os 库删文件（--clean 参数）

# ========== 环境配置：根据参数选择 dev/real 模式 ==========

# --quick 参数：跳过提取，纯测试对话
SKIP_EXTRACT = "--quick" in sys.argv

if "--real" in sys.argv:
    # 真实模式（和开发文件隔离）
    persona_file     = "personal/persona.json"
    user_facts_file  = "personal/user_facts.json"
    memory_file      = "personal/memory.json"
    suggestions_file = "personal/persona_suggestions.json"
    chroma_path      = "chroma_data"
    print("[真实女友模式]")
else:
    # 测试助手模式（默认）
    if "--clean" in sys.argv:
        for f in ["memory_dev.json", "persona_suggestions_dev.json", "calendar.json"]:
            try:
                os.remove(f)
                print(f"[已删除 {f}]")
            except FileNotFoundError:
                pass
        import shutil
        try:
            shutil.rmtree("chroma_data_dev")
            print("[已删除 chroma_data_dev]")
        except FileNotFoundError:
            pass
    persona_file     = "persona_dev.json"
    user_facts_file  = "user_facts_dev.json"
    memory_file      = "memory_dev.json"
    suggestions_file = "persona_suggestions_dev.json"
    chroma_path      = "chroma_data_dev"
    tag = "测试助手模式" + (" [快速: 跳过提取]" if SKIP_EXTRACT else "")
    print(f"[{tag}]")

# 读人设
with open(persona_file, "r") as f:
    persona = json.load(f)
print(f"[加载人设: {persona_file}]")

# 读用户信息（文件不存在则自动创建空白）
try:
    with open(user_facts_file, "r") as f:
        user_facts = json.load(f)
except FileNotFoundError:
    user_facts = {"name": "", "grade": "", "interests": [], "traits": [], "dislikes": [],
                  "pets": [], "family": {}, "important_events": [], "note": ""}
    with open(user_facts_file, "w") as f:
        json.dump(user_facts, f, ensure_ascii=False, indent=2)
    print(f"[自动创建 {user_facts_file}]")


MAX_CONTEXT = 8  # 只发送最近 4 轮对话给 LLM，超过的自动压缩成摘要
MAX_AGENT_ITERATIONS = 6  # Agent 循环上限（计划型任务需要更多轮：列计划→调工具→汇总）


def run_agent(system_msg, context_messages, tools_schema):
    """
    Agent 循环（原生 function calling 版）：
    LLM 返回 tool_calls → 执行 → 结果喂回 → 再问 → 直到纯文本。
    和文本方案的区别：工具调用在独立字段，不在文本里。
    """
    agent_msgs = [system_msg] + list(context_messages)

    for i in range(MAX_AGENT_ITERATIONS):
        # 流式获取 LLM 回复（实时展示思考/推理过程）
        gen, acc = chat_with_tools_stream(agent_msgs, tools_schema, timeout=60)

        has_content = False
        for token in gen:
            if not has_content:
                print("  💭 ", end="", flush=True)
                has_content = True
            print(token, end="", flush=True)
        if has_content:
            print()  # 换行

        if acc["tool_calls"]:
            # 构造一条 assistant 消息（含思考文本 + 工具调用）
            agent_msgs.append({
                "role": "assistant",
                "content": acc["content"],
                "tool_calls": acc["tool_calls"],
            })

            for tc in acc["tool_calls"]:
                func = tc["function"]
                name = func["name"]
                args = func.get("arguments", {})
                if name not in TOOLS:
                    continue

                print(f"  🔧 {name}({args})")
                # 过滤掉 LLM 幻觉出来的无效参数，只保留 schema 中定义的
                allowed = set(TOOLS[name]["parameters"].get("properties", {}).keys())
                required = set(TOOLS[name]["parameters"].get("required", []))
                safe_args = {k: v for k, v in args.items() if k in allowed}
                # 如果必填参数全被过滤掉了 → 幻觉严重，跳过此次调用
                if required and not required.issubset(safe_args.keys()):
                    print(f"  ⚠ {name} 缺少必填参数 {required - set(safe_args.keys())}，跳过")
                    continue
                raw = TOOLS[name]["function"](**safe_args) if safe_args else TOOLS[name]["function"]()

                # 每个工具结果独立一条消息，不会被覆盖
                agent_msgs.append({"role": "tool", "content": str(raw)})
        else:
            # 无工具调用，但内容可能只是"接下来做X"的过渡句（不是最终答案）
            content = acc["content"] or ""
            if content and any(w in content for w in ["总结", "建议", "最终", "祝", "希望", "再见"]):
                return content  # 像最终答案 → 直接返回
            if content:
                # 可能是过渡句 → 推一把
                agent_msgs.append({"role": "assistant", "content": content})
                agent_msgs.append({"role": "system", "content": "请继续执行。如果需要调用工具，立即调用。"})
            else:
                return ""  # 完全空，退出

    return agent_msgs[-1].get("content", "")


def compress_history(old_messages):
    """
    将一组旧消息压缩成 2-3 句摘要。用 chat_sync（非流式），
    只保留关键事件和情感，丢弃具体措辞。
    """
    if not old_messages:
        return ""
    lines = []
    for m in old_messages:
        role = "用户" if m["role"] == "user" else "AI"
        lines.append(f"{role}: {m['content']}")
    text = "\n".join(lines)

    return chat_sync([
        {"role": "system", "content": "你是一个对话摘要助手。将以下对话压成2-3句简洁摘要，只保留关键事件、决定、情感。只返回摘要文本，不加解释。"},
        {"role": "user", "content": f"请摘要：\n{text}"},
    ], timeout=30)

# 构建system信息
def build_system_msg(persona, user_facts, history_notes=None, context_messages=None):
    """
    动态构建 system 消息，含人设、准则、历史摘要、用户事实、可用工具、相关经历。
    """
    facts_text = json.dumps(user_facts, ensure_ascii=False, indent=2)

    parts = [f"你的名字是{persona.get('name', '')}，{persona['persona']}"]
    if persona.get("rules"):
        parts.append("【核心准则】\n" + "\n".join(f"- {r}" for r in persona["rules"]))
    if history_notes:
        parts.append("【历史摘要】\n" + "\n".join(f"- {s}" for s in history_notes))
    parts.append(f"【关于用户】\n{facts_text}")

    # 从向量库检索相关经历（基于当前对话上下文）
    if context_messages:
        last_user = next((m["content"] for m in reversed(context_messages) if m["role"] == "user"), "")
        if last_user:
            related = search_experiences(last_user, n_results=2)
            if related:
                lines = [f"- {date}: {text}" for text, date in related]
                parts.append("【相关经历】\n" + "\n".join(lines))
    parts.append(
        "【执行规则】\n"
        "- 处理相对日期必须先调 get_current_time 再推算\n"
        "- 简单问题: 直接回答或调工具后回答\n"
        "- 复杂多步骤: 先列计划梗概，严格按顺序逐步执行，上一步完成后再做下一步，全部完成后用【总结】开头给出汇总\n"
        "- 核心原则: 说「我无法做XXX」之前，先看工具列表里有没有能做这件事的工具\n"
        "- 重要: 用户的每条消息是独立请求。历史对话仅供参考上下文，不要延续或重新执行其中的计划。"
        "根据当前这条用户消息独立决定要做什么。"
        "你拥有查询天气、时间、日历、计算等各种工具，不要错误地认为自己做不了"
    )

    return {"role": "system", "content": "\n\n".join(parts)}

# 如果文件存在且有效，把上次的对话读回来
try:
    with open(memory_file, "r") as f:
        messages = json.load(f)
    print(f"[从 {memory_file} 恢复了 {len(messages)} 条对话记录]")
except (FileNotFoundError, json.JSONDecodeError):
    messages = []
    print("[新对话开始]")

# 初始化向量数据库路径
init_store(chroma_path)

# 构建工具 schema（一次即可，工具集不变）
tools_schema = build_ollama_tools(TOOLS)

# 追踪状态
last_extracted_count = len(messages)  # 已提取到的位置
history_notes = []                    # 压缩摘要列表
compressed_count = 0                  # 已压缩到的位置

# 启动时如果历史已超过阈值，先压缩一次
if len(messages) > MAX_CONTEXT:
    print("[启动时压缩旧对话...]")
    to_compress = messages[:len(messages) - MAX_CONTEXT]
    summary = compress_history(to_compress)
    if summary:
        history_notes.append(summary)
        compressed_count = len(to_compress)
        print(f"[压缩完成，{compressed_count} 条消息 → 1 条摘要]")

try:
    while True:
        user_input = input("你: ")
        if user_input == "quit":
            break

        messages.append({"role": "user", "content": user_input})

        # ===== 上下文管理：超阈值则压缩旧消息，只保留最近 N 条完整对话 =====
        if len(messages) > MAX_CONTEXT:
            overflow = len(messages) - MAX_CONTEXT
            # 每多出 4 条新消息（2 轮）才触发一次压缩，避免过于频繁
            if overflow > compressed_count + 4:
                to_compress = messages[:overflow]
                print("[正在压缩旧对话...]")
                summary = compress_history(to_compress)
                if summary:
                    history_notes.append(summary)
                    print(f"[压缩完成，当前 {len(history_notes)} 条摘要]")
                compressed_count = overflow

            # 只发送最近 MAX_CONTEXT 条完整对话 + 历史摘要
            context = messages[-MAX_CONTEXT:]
        else:
            context = messages

        system_msg = build_system_msg(persona, user_facts, history_notes, context)

        # Agent 循环：推理（非流式）+ 最终回复（流式打字机效果）
        ai_reply = run_agent(system_msg, context, tools_schema)
        messages.append({"role": "assistant", "content": ai_reply})

        # 每 3 轮新对话（6 条消息）触发一次增量提取（--quick 跳过）
        new_count = len(messages) - last_extracted_count
        if new_count >= 6 and not SKIP_EXTRACT:
            print("[正在后台提取对话信息...]")
            recent = messages[last_extracted_count:]  # 只分析新增的部分
            new_facts, persona_signals = extract_insights(recent, user_facts)
            if new_facts:
                merge_user_facts(user_facts, new_facts)
                with open(user_facts_file, "w") as f:
                    json.dump(user_facts, f, ensure_ascii=False, indent=2)
                    print("[用户信息已更新]")
            if persona_signals:
                save_persona_suggestions(persona_signals, suggestions_file)

            experiences = extract_experiences(recent)
            for text, date_str in experiences:
                add_experience(text, date_str)

        if new_count >= 6:
            last_extracted_count = len(messages)  # 记录已分析位置（即使跳过提取也更新）
finally:
    # 1. 保存对话记录
    with open(memory_file, "w") as f:
        json.dump(messages, f, ensure_ascii=False)
        print(f"[对话记录已保存到 {memory_file}]")

    # 2. 退出时分析尚未提取的新消息（补充兜底）
    remaining = len(messages) - last_extracted_count
    if remaining >= 2 and not SKIP_EXTRACT:
        print(f"[正在分析剩余 {remaining} 条消息...]")
        recent = messages[last_extracted_count:]
        new_facts, persona_signals = extract_insights(recent, user_facts)
        if new_facts:
            merge_user_facts(user_facts, new_facts)
            with open(user_facts_file, "w") as f:
                json.dump(user_facts, f, ensure_ascii=False, indent=2)
                print(f"[用户信息已更新到 {user_facts_file}]")
        if persona_signals:
            save_persona_suggestions(persona_signals, suggestions_file)

        experiences = extract_experiences(recent)
        for text, date_str in experiences:
            add_experience(text, date_str)
