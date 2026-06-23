# ai_study

个人 AI 学习项目，从零手写一个本地大模型 Agent。

## 技术栈
- Python + Ollama (qwen2.5:32b)
- 原生 function calling
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
├── llm_client.py        # LLM 通信 (流式/同步/原生 tools)
├── extraction.py        # 对话事实/经历提取
├── experience_store.py  # 向量数据库经历记忆
├── tools/               # Agent 工具包
│   ├── __init__.py
│   ├── weather.py
│   ├── time.py
│   ├── calculator.py
│   └── calendar.py
├── persona_dev.json     # 测试人设
└── user_facts_dev.json  # 测试数据
```

## 运行
```bash
# 需要先启动 Ollama
python3 chat.py                  # 测试模式
python3 chat.py --clean          # 清空重来
python3 chat.py --real           # 真实模式 (数据存在 personal/)
```
