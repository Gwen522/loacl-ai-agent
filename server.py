"""
Web 后端。复用 agent_core + session，通过 SSE 流式推送给前端。
启动: uvicorn server:app --reload --port 8000
"""
import json
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import queue
import threading

from tools import TOOLS, build_ollama_tools
from agent_core import run_agent, build_system_msg
from session import init_session, save_memory

app = FastAPI()
tools_schema = build_ollama_tools(TOOLS)


class ChatRequest(BaseModel):
    message: str
    history: list = []
    mode: str = "dev"  # dev | real | clean


@app.post("/api/chat")
def chat(req: ChatRequest):
    """接收用户消息 + 历史 + 模式，流式返回 AI 回复。"""
    data_dir, persona, user_facts, saved_messages = init_session(req.mode)

    # 合并历史：上次保存的消息 + 前端传来的本次会话历史 + 当前消息
    all_messages = saved_messages + list(req.history) + [{"role": "user", "content": req.message}]
    save_memory(data_dir, all_messages)  # 实时持久化

    context = list(req.history) + [{"role": "user", "content": req.message}]
    system_msg = build_system_msg(persona, user_facts, None, context)

    q = queue.Queue()

    def on_token(tok):
        q.put({"type": "token", "data": tok})

    def on_tool(name, args):
        q.put({"type": "tool", "data": f"{name}({args})"})

    def worker():
        try:
            reply = run_agent(system_msg, context, tools_schema,
                              on_token=on_token, on_tool=on_tool)
            q.put({"type": "done", "data": reply})
        except Exception as e:
            q.put({"type": "error", "data": str(e)})
        finally:
            q.put(None)

    threading.Thread(target=worker, daemon=True).start()

    def event_stream():
        while True:
            item = q.get()
            if item is None:
                break
            yield f"data: {json.dumps(item, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
