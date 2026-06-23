import requests  # 发 HTTP 请求到 Ollama
import json       # 解析 Ollama 返回的 JSON

 #流式调用：返回生成器，逐个产出 token。聊天用（打字机效果）。
def chat_stream(messages, model="qwen2.5:32b"):
    response = requests.post(
        "http://localhost:11434/api/chat",
        json={"model": model, "messages": messages, "stream": True},
        stream=True,
    )
    for line in response.iter_lines():
        if not line:
            continue
        chunk = json.loads(line)
        yield chunk["message"]["content"]


def chat_sync(messages, model="qwen2.5:32b", timeout=60):
    """
    同步调用：一次性返回完整结果字符串。
    用途：信息提取、总结等需要完整 JSON 才能解析的后台任务。
    """
    response = requests.post(
        "http://localhost:11434/api/chat",
        json={"model": model, "messages": messages, "stream": False},
        timeout=timeout,
    )
    response.raise_for_status()
    return response.json()["message"]["content"]


def chat_with_tools(messages, tools, model="qwen2.5:32b", timeout=60):
    """
    原生 function calling 调用（非流式）。返回完整 message 对象。
    """
    response = requests.post(
        "http://localhost:11434/api/chat",
        json={
            "model": model,
            "messages": messages,
            "tools": tools,
            "stream": False,
        },
        timeout=timeout,
    )
    response.raise_for_status()
    return response.json()["message"]


def chat_with_tools_stream(messages, tools, model="qwen2.5:32b", timeout=60):
    """
    流式 + 原生 tools。返回 (生成器, 累加器)。
    生成器逐个产出 content token（实时打印用），累加器共享 dict 存 tool_calls。

    用法:
      gen, acc = chat_with_tools_stream(msgs, tools)
      for token in gen:
          print(token, end="")      # 实时流式展示
      # 流结束后 acc["tool_calls"] 可能是 LLM 调用的工具
    """
    response = requests.post(
        "http://localhost:11434/api/chat",
        json={
            "model": model,
            "messages": messages,
            "tools": tools,
            "stream": True,
        },
        stream=True,
        timeout=timeout,
    )
    acc = {"content": "", "tool_calls": None}

    def generate():
        for line in response.iter_lines():
            if not line:
                continue
            chunk = json.loads(line)
            m = chunk.get("message", {})
            if "content" in m and m["content"]:
                token = m["content"]
                acc["content"] += token
                yield token
            if "tool_calls" in m and m["tool_calls"]:
                acc["tool_calls"] = m["tool_calls"]

    return generate(), acc
