# local-ai-agent

从零手写一个本地大模型 Agent，不依赖 LangChain 等框架。

学习 AI Agent 的底层原理：对话引擎 → 工具调用 → 多步推理 → 向量记忆。

## 技术栈
- Python + Ollama (qwen2.5:32b)
- 原生 function calling（不用 LangChain）
- ChromaDB 向量数据库

## 已完成
- [x] 终端流式对话 + 记忆持久化
- [x] 用户事实自动提取 (user_facts.json)
- [x] Agent 工具调用 (天气 / 时间 / 计算器 / 日历)
- [x] 上下文压缩 (超 4 轮自动摘要)
- [x] Plan-and-Execute 多步推理
- [x] 经历记忆 + 语义检索 (ChromaDB)

## 项目结构
```
├── chat.py              # 主循环 + Agent 循环
├── config.py            # 模型名集中管理
├── llm_client.py        # LLM 通信（流式/同步/原生 tools）
├── extraction.py        # 对话事实/经历提取
├── experience_store.py  # 向量数据库经历记忆（ChromaDB）
├── tools/               # Agent 工具包
│   ├── __init__.py      #   工具注册表
│   ├── weather.py       #   天气查询
│   ├── time.py          #   当前时间
│   ├── calculator.py    #   安全计算器
│   └── calendar.py      #   日历（添加/查询/删除）
├── dev_data/            # 测试数据（gitignore，不被提交）
│   ├── persona.json
│   ├── user_facts.json
│   └── ...
└── personal/            # 真实数据（gitignore，不被提交）
    ├── persona.json
    ├── user_facts.json
    └── ...
```

## 运行

```bash
# ① 激活虚拟环境（仅第一次，终端出现 (venv) 即成功）
source venv/bin/activate

# ② 安装依赖 & 拉模型（仅第一次）
pip install -r requirements.txt
ollama pull qwen2.5:32b
ollama pull nomic-embed-text

# ③ 四种运行模式：
python3 chat.py                  # ① 测试模式（保留上次对话和记忆）
python3 chat.py --clean          # ② 清空重测（删记忆、日历、向量库）
python3 chat.py --clean --quick  # ③ 快速测试（只对话，不提取事实/经历，秒 quit）
python3 chat.py --real           # ④ 真实模式（数据存在 personal/，测试环境保持干净）
```

| 参数 | 作用 | 适用场景 |
|---|---|---|
| （无） | 继续上次对话 | 正常测试 |
| `--clean` | 清空所有测试数据 | 重头开始 |
| `--clean --quick` | 清空 + 跳过提取 | 快速验证对话效果 |
| `--real` | 切换真实数据 | 正式使用 |

## 换模型

改一行：`config.py` 里的 `MODEL_NAME`。只要 Ollama 里有那个模型就能跑。

## 运行要求
- Ollama 运行在 `localhost:11434`
- Python 3.9+
