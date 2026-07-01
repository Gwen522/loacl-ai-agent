import gnureadline  # 修复 macOS 中文输入退格问题（必须在其他 import 之前）
from llm_client import chat_sync, chat_with_tools, chat_with_tools_stream, chat_stream
from extraction import extract_insights, merge_user_facts, save_persona_suggestions, extract_experiences
from tools import TOOLS, build_ollama_tools
from experience_store import add_experience
from agent_core import run_agent, build_system_msg
from session import init_session, save_memory, build_context, save_user_facts
import json
import sys
import os

# ========== 模式配置（终端专属）==========

SKIP_EXTRACT = "--quick" in sys.argv
mode = "dev"
if "--real" in sys.argv:
    mode = "real"
if "--clean" in sys.argv:
    mode = "clean"

# 初始化会话
data_dir, persona, user_facts, messages = init_session(mode)
suggestions_file = f"{data_dir}/suggestions.json"

tag = {
    "real": "[真实女友模式]",
    "dev": "[测试助手模式]" + (" [快速: 跳过提取]" if SKIP_EXTRACT else ""),
}.get(mode, "[测试助手模式]")
print(tag)

print(f"[加载人设: {data_dir}/persona.json]")
print(f"[{'从 ' + data_dir + '/memory.json 恢复了 ' + str(len(messages)) + ' 条对话记录' if messages else '新对话开始'}]")

tools_schema = build_ollama_tools(TOOLS)

# ========== 追踪状态 ==========
last_extracted_count = len(messages)
history_notes: list = []
compressed_count = 0

# 启动压缩
if len(messages) > 8:
    context, history_notes, compressed_count = build_context(messages, history_notes, compressed_count)

try:
    while True:
        user_input = input("你: ")
        if user_input == "quit":
            break

        messages.append({"role": "user", "content": user_input})
        context, history_notes, compressed_count = build_context(
            messages, history_notes, compressed_count)

        system_msg = build_system_msg(persona, user_facts, history_notes, context)

        _printed = {"started": False}

        def on_token(tok):
            if not _printed["started"]:
                print("  💭 ", end="", flush=True)
                _printed["started"] = True
            print(tok, end="", flush=True)

        def on_tool(name, args):
            if _printed["started"]:
                print()
                _printed["started"] = False
            print(f"  🔧 {name}({args})")

        ai_reply = run_agent(system_msg, context, tools_schema,
                             on_token=on_token, on_tool=on_tool)
        if _printed["started"]:
            print()
        messages.append({"role": "assistant", "content": ai_reply})

        # 定期提取
        new_count = len(messages) - last_extracted_count
        if new_count >= 6 and not SKIP_EXTRACT:
            print("[正在后台提取对话信息...]")
            recent = messages[last_extracted_count:]
            new_facts, persona_signals = extract_insights(recent, user_facts)
            if new_facts:
                merge_user_facts(user_facts, new_facts)
                save_user_facts(data_dir, user_facts)
                print("[用户信息已更新]")
            if persona_signals:
                save_persona_suggestions(persona_signals, suggestions_file)
            experiences = extract_experiences(recent)
            for text, date_str in experiences:
                add_experience(text, date_str)

        if new_count >= 6:
            last_extracted_count = len(messages)

finally:
    save_memory(data_dir, messages)
    print(f"[对话记录已保存到 {data_dir}/memory.json]")

    remaining = len(messages) - last_extracted_count
    if remaining >= 2 and not SKIP_EXTRACT:
        print(f"[正在分析剩余 {remaining} 条消息...]")
        recent = messages[last_extracted_count:]
        new_facts, persona_signals = extract_insights(recent, user_facts)
        if new_facts:
            merge_user_facts(user_facts, new_facts)
            save_user_facts(data_dir, user_facts)
            print(f"[用户信息已更新到 {data_dir}/user_facts.json]")
        if persona_signals:
            save_persona_suggestions(persona_signals, suggestions_file)
        experiences = extract_experiences(recent)
        for text, date_str in experiences:
            add_experience(text, date_str)
