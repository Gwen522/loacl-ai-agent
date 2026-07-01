# local-ai-agent

从零手写一个本地大模型 Agent，不依赖 LangChain 等框架。

学习 AI Agent 的底层原理：对话引擎 → 工具调用 → 多步推理 → 向量记忆。

## 技术栈
- 后端: Python + Ollama (qwen2.5:32b) + FastAPI
- 前端: Vue 3 + TypeScript + Vite
- 向量库: ChromaDB + nomic-embed-text
- 原生 function calling（不用 LangChain）

## 已完成
- [x] 终端流式对话 + 记忆持久化
- [x] 用户事实自动提取
- [x] Agent 工具调用 (天气 / 时间 / 计算器 / 日历)
- [x] 上下文压缩 (超 4 轮自动摘要)
- [x] Plan-and-Execute 多步推理
- [x] 经历记忆 + 语义检索 (ChromaDB)
- [x] Web 前端 (Vue 3 + TS)

## 项目结构
```
├── chat.py              # 终端对话入口
├── server.py            # Web 后端 (FastAPI + SSE)
├── agent_core.py        # Agent 核心（run_agent / build_system_msg）
├── session.py           # 会话管理（加载/保存/压缩）
├── llm_client.py        # LLM 通信（流式/同步/原生 tools）
├── config.py            # 模型名集中管理
├── extraction.py        # 事实提取 + 经历提取
├── experience_store.py  # 向量记忆 (ChromaDB)
├── tools/               # Agent 工具包
│   ├── __init__.py      #   注册表 + Ollama schema 构建
│   ├── weather.py       #   天气查询 (wttr.in)
│   ├── time.py          #   当前时间
│   ├── calculator.py    #   安全计算器
│   └── calendar.py      #   日历（添加/查询/删除）
├── frontend/            # Vue 3 + TypeScript + Vite
│   ├── index.html
│   ├── vite.config.ts
│   └── src/
│       ├── App.vue
│       └── components/
│           ├── ChatWindow.vue
│           ├── ChatMessage.vue
│           └── ChatInput.vue
├── dev_data/            # 测试数据 (gitignore)
└── personal/            # 真实数据 (gitignore)
```

## 运行 (Web 版)

```bash
# 前置：安装依赖 & 拉模型（仅第一次）
source venv/bin/activate
pip install -r requirements.txt
ollama pull qwen2.5:32b
ollama pull nomic-embed-text

# 前端依赖
cd frontend
npm install                    # 装 Vue / Vite / TS
cd ..

# 终端 1: 启动后端
uvicorn server:app --reload --port 8000

# 终端 2: 启动前端
cd frontend
npm run dev                    # 浏览器打开 http://localhost:5173
```

## 运行 (终端版)

```bash
python3 chat.py                  # 测试模式（保留历史）
python3 chat.py --clean          # 清空重测
python3 chat.py --clean --quick  # 快速测试（跳过提取）
python3 chat.py --real           # 真实模式（数据在 personal/）
```

| 参数 | 作用 |
|---|---|
| （无） | 继续上次对话 |
| `--clean` | 清空测试数据 |
| `--quick` | 跳过事实提取 |
| `--real` | 切换正式数据 |

## 换模型

改一行：`config.py` 里的 `MODEL_NAME`。只要 Ollama 里有那个模型就能跑。

## 运行要求
- Ollama 运行在 `localhost:11434`
- Python 3.9+
