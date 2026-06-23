"""
Agent 工具集入口。TOOLS 注册表 + Ollama schema 构建器。
每个工具分散在独立文件中，加新工具只需：写文件 → 在这里 import 并注册。
"""
from tools.weather import get_weather
from tools.time import get_current_time
from tools.calculator import calculate
from tools.calendar import add_calendar_event, query_calendar_events, delete_calendar_event


TOOLS = {
    "get_weather": {
        "name": "get_weather",
        "description": "查询城市天气",
        "function": get_weather,
        "parameters": {
            "type": "object",
            "properties": {"city": {"type": "string", "description": "城市名，如上海、北京"}},
            "required": ["city"]
        }
    },
    "get_current_time": {
        "name": "get_current_time",
        "description": "获取当前日期、时间和星期几",
        "function": get_current_time,
        "parameters": {"type": "object", "properties": {}, "required": []}
    },
    "calculate": {
        "name": "calculate",
        "description": "计算数学表达式，如 123*456、100/3、2^10",
        "function": calculate,
        "parameters": {
            "type": "object",
            "properties": {"expression": {"type": "string", "description": "数学表达式如 123*456"}},
            "required": ["expression"]
        }
    },
    "add_calendar_event": {
        "name": "add_calendar_event",
        "description": "添加日历日程，如用户说'帮我记一下周五下午3点面试'",
        "function": add_calendar_event,
        "parameters": {
            "type": "object",
            "properties": {
                "event_date":   {"type": "string", "description": "日期 YYYY-MM-DD"},
                "event_time":   {"type": "string", "description": "时间 HH:MM"},
                "description":  {"type": "string", "description": "事件描述"}
            },
            "required": ["event_date", "event_time", "description"]
        }
    },
    "query_calendar_events": {
        "name": "query_calendar_events",
        "description": "查询日历安排。'周五有什么安排'调用此工具",
        "function": query_calendar_events,
        "parameters": {
            "type": "object",
            "properties": {"query_date": {"type": "string", "description": "要查的日期 YYYY-MM-DD，不传返回所有未来事件"}},
            "required": []
        }
    },
    "delete_calendar_event": {
        "name": "delete_calendar_event",
        "description": "删除日历日程。用户说'取消/删除/修改XX安排'时，先删再加新",
        "function": delete_calendar_event,
        "parameters": {
            "type": "object",
            "properties": {
                "event_date":          {"type": "string", "description": "要删除的日期 YYYY-MM-DD"},
                "description_keyword": {"type": "string", "description": "描述关键词，用于匹配要删的事件"}
            },
            "required": ["event_date", "description_keyword"]
        }
    },
}


def build_ollama_tools(tools_dict):
    """把 TOOLS 注册表转成 Ollama 原生 tools 参数格式。"""
    result = []
    for tool in tools_dict.values():
        result.append({
            "type": "function",
            "function": {
                "name": tool["name"],
                "description": tool["description"],
                "parameters": tool["parameters"],
            }
        })
    return result
