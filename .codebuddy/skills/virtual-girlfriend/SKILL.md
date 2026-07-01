---
name: virtual-girlfriend
description: >
  This skill should be used when working in the ai_gfriend_study project (path /Users/wuyongda/ai_gfriend_study).
  Currently the project is in testing/learning phase: a general-purpose AI assistant built with Python + Ollama,
  where the LLM serves as the "brain" and conversation memory. The long-term goal is to evolve it into a virtual
  girlfriend, but for now the persona is simply a helpful assistant (see persona.json). The user (wuyongda) is a
  frontend intern with JS/Vue background and minimal Python experience, using this project to learn AI development.
  Trigger when modifying chat.py, adding features to the AI chatbot, or discussing the project's architecture and roadmap.
---

# AI Study Project (ai_gfriend_study)

## Overview

This is a personal learning project, currently in the **testing/learning phase** as a general-purpose AI assistant
powered by Python + Ollama. The long-term vision is to build an **AI virtual girlfriend**, but right now the focus
is on learning the fundamentals: LLM integration, conversation memory, system prompts, and related concepts.

The LLM (via Ollama) serves as the "brain" — handling conversation, personality, and memory. The project currently
runs as a terminal chat app, with plans to eventually add a frontend UI. The user may publish it on GitHub in the future.

**Current persona**: Simple helpful assistant ("你是用户的助手") — defined in `persona.json`.
**End goal**: AI virtual girlfriend — but only after core capabilities are solid.

## User Background

- **Name**: wuyongda
- **Role**: Frontend intern
- **Primary skills**: JavaScript, Vue.js, frontend development
- **Python experience**: Minimal — learning Python through this project
- **Goal**: Deepen understanding of AI, learn AI-related development

**Implication for CodeBuddy**: The user is learning Python through this project. Prefer clear, beginner-friendly
explanations without assuming prior Python knowledge.

## Project Architecture

```
ai_study/
├── chat.py                  ← 主循环 + Agent 循环 + 压缩 + 提取调度
├── llm_client.py            ← 3 种 LLM 通信（流式 / 同步 / 原生 tools）
├── extraction.py            ← 对话事实提取，自由字段，合并逻辑
├── tools/                   ← Agent 工具包（可扩展）
│   ├── __init__.py          ← TOOLS 注册表 + Ollama schema 构建
│   ├── weather.py           ← 天气查询（wttr.in API）
│   ├── time.py              ← 当前时间
│   ├── calculator.py        ← 安全计算器
│   └── calendar.py          ← 日历 CRUD（添加/查询/删除）
├── persona_dev.json         ← 测试人设（助手·银月）
├── persona.json → personal/ ← 真实人设（女友·星歌）
├── user_facts_dev.json      ← 测试用户数据
├── memory_dev.json          ← 测试对话记忆
├── calendar.json            ← 日历数据
├── personal/                ← 私人数据（永不提交 Git）
│   ├── persona.json
│   ├── user_facts.json
│   ├── memory.json
│   └── persona_suggestions.json
├── venv/
└── .codebuddy/skills/
```

## 架构职责边界

### agent_core.py — Agent 核心（纯逻辑，无 IO）
- `run_agent(system_msg, context, tools_schema, on_token, on_tool)` — agent 循环
- `build_system_msg(persona, facts, history_notes, context)` — 构建 system prompt
- **不 print、不读文件、不知道"终端还是 Web"**

### chat.py — 终端版
- 模式解析 (--real / --clean / --quick)
- 加载/保存 persona、user_facts、memory JSON
- 上下文压缩 (compress_history, history_notes)
- 用户输入 (input) + 终端展示 (💭🔧 回调)
- 定期提取 (user_facts + 经历) 和 quit 提取
- 调用 agent_core.run_agent()

### server.py — Web 版
- FastAPI 路由 /api/chat
- 前端模式按钮 → mode 参数 → 选择 dev_data/ 或 personal/
- 每次请求加载 persona + user_facts
- SSE 流式推送 (token/tool/done/error 事件)
- 调用 agent_core.run_agent()
- (暂未挂提取逻辑)

## Current Features

### Agent & Tools
- **Native Ollama function calling** — 5 tools: weather, time, calculator, calendar (add/query/delete)
- **ReAct 风格推理** — LLM 先思考试 → 调工具 → 拿结果 → 再思考 → 输出
- **多工具并行** — 同时调用多个工具，流式最终回复
- **工具包架构** — `tools/` 目录，加新工具仅需：写文件 → `__init__.py` import + 注册

### 对话系统
- 流式输出 + 对话记忆持久化 + 跨会话恢复
- 上下文压缩：超过 4 轮自动压成摘要
- 动态 system_msg：facts 更新后即时感知

### 用户认知系统
- 自动提取用户事实 → `user_facts.json`
- 自由字段命名（LLM 自主决定字段名）
- 增量更新 + 去重合并
- 人格偏好建议 → `persona_suggestions.json`（人工审）

### 工程化
- dev/real 环境全隔离（`personal/` 文件夹）
- `--clean` 一键重置测试数据
- `python3 chat.py --real` 切换正式女友模式

## Roadmap

### ✅ Done
Agent 架构、用户事实提取、上下文压缩、工具系统（5 tools）、环境隔离

### 🔜 Planned
- 经历记忆（milestones + daily 日志）
- 稳定性（错误处理、重试）
- 前台 UI（Vue + FastAPI）
- 主动提醒（后台定时任务）

## Conventions for CodeBuddy

### ⚠️ 开发模式规则（最重要）

1. **小步改动，逐步解释**
   - 每次改动要明确告知：改了哪里、为什么要改、改了之后有什么效果
   - 不要一次性追加大量代码（上次从 80 行一次膨胀到 300+ 行是不可接受的）
   - 新增的函数/类要逐一解释清楚用途，用户说"没搞明白"说明解释不够

2. **改动前先说明计划**
   - 超过 20 行的改动，先说明要改什么、为什么，等用户确认后再动手
   - 新增文件更是必须先商量

3. **模块拆分规则**
   - 当一个文件超过 **~120 行** 或 **塞了 3 种以上不同职责**，应主动建议拆分
   - 目前拆分：`llm_client.py`(通信)、`extraction.py`(提取)、`tools/`(工具包)
   - 工具包拆分模式：独立文件 → `tools/__init__.py` import + 注册 → 不改主循环
   - 拆模块让用户参与决策

### Commit 规范
- Git commit message 用中文，格式: `类型: 简述`
- 类型: 新增 / 修复 / 重构 / 文档 / 清理
- 示例: `新增: --quick 模式跳过提取`、`修复: --clean 漏清 user_facts`

### When writing/modifying Python code:
- Add comments in Chinese (user's preferred language)
- Keep explanations beginner-friendly but not overly verbose
- 优先自由命名方案而非硬编码方案（如 user_facts 提取让 LLM 自由命名字段）

### Key things to remember:
- The user is learning — mistakes are expected, always explain the "why" behind fixes
- `venv/` is the virtual environment, always activate it or use `python3` directly
- Memory / facts / calendar files are JSON, never edit them manually unless explicitly asked
- MCP / LangChain 等框架留到原理学懂后再引入——现在手写是最佳学习路径
- **禁止打补丁式修复**：遇到 LLM 行为问题，优先找通用方案而非单点修补
  反例: 加「别忘了你还有日历工具」 → 正例: 加「说做不到之前先检查有无可用工具」
  user_facts 提取同理：核心原则「只记用户明确陈述」取代一堆反例规则

### When the user asks "what should I learn next":
- Recommend features from the Roadmap above
- 优先：经历记忆、稳定性、前端 UI
- 工具扩展遵循「需要什么加什么」原则，不提前预装
