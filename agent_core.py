"""
Agent 核心逻辑，被 chat.py（终端）和 server.py（Web）共用。
不含任何终端打印或文件 IO —— 输出通过回调函数传出，谁调用谁决定怎么展示。
"""
import json
from llm_client import chat_with_tools_stream
from tools import TOOLS
from experience_store import search_experiences

MAX_AGENT_ITERATIONS = 6  # Agent 循环上限（计划型任务需多轮：列计划→调工具→汇总）


def run_agent(system_msg, context_messages, tools_schema, on_token=None, on_tool=None):
    """
    Agent 循环（原生 function calling）。
    on_token(token): 每个流式 token 的回调（终端打印 / Web 推送）
    on_tool(name, args): 工具被调用时的回调
    返回最终回复字符串。
    """
    agent_msgs = [system_msg] + list(context_messages)

    for _ in range(MAX_AGENT_ITERATIONS):
        gen, acc = chat_with_tools_stream(agent_msgs, tools_schema, timeout=60)

        for token in gen:
            if on_token:
                on_token(token)

        if acc["tool_calls"]:
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

                if on_tool:
                    on_tool(name, args)

                # 过滤掉 LLM 幻觉出来的无效参数
                allowed = set(TOOLS[name]["parameters"].get("properties", {}).keys())
                required = set(TOOLS[name]["parameters"].get("required", []))
                safe_args = {k: v for k, v in args.items() if k in allowed}
                if required and not required.issubset(safe_args.keys()):
                    continue  # 必填参数缺失，跳过
                raw = TOOLS[name]["function"](**safe_args) if safe_args else TOOLS[name]["function"]()

                agent_msgs.append({"role": "tool", "content": str(raw)})
        else:
            content = acc["content"] or ""
            if content and any(w in content for w in ["总结", "建议", "最终", "祝", "希望", "再见"]):
                return content
            if content:
                agent_msgs.append({"role": "assistant", "content": content})
                agent_msgs.append({"role": "system", "content": "请继续执行。如果需要调用工具，立即调用。"})
            else:
                return ""

    return agent_msgs[-1].get("content", "")


def build_system_msg(persona, user_facts, history_notes=None, context_messages=None):
    """构建 system 消息：人设 + 准则 + 历史摘要 + 用户事实 + 相关经历 + 执行规则。"""
    facts_text = json.dumps(user_facts, ensure_ascii=False, indent=2)

    parts = [f"你的名字是{persona.get('name', '')}，{persona['persona']}"]
    if persona.get("rules"):
        parts.append("【核心准则】\n" + "\n".join(f"- {r}" for r in persona["rules"]))
    if history_notes:
        parts.append("【历史摘要】\n" + "\n".join(f"- {s}" for s in history_notes))
    parts.append(f"【关于用户】\n{facts_text}")

    # 从向量库检索相关经历
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
