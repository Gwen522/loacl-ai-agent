"""日历工具。数据持久化，支持添加、查询、删除。"""
import json
import os
from datetime import date

CALENDAR_FILE = "calendar.json"


def set_calendar_path(path):
    """切换日历文件路径（dev/real 隔离用）"""
    global CALENDAR_FILE
    CALENDAR_FILE = path


def _read():
    if not os.path.exists(CALENDAR_FILE):
        return {"events": []}
    with open(CALENDAR_FILE, "r") as f:
        return json.load(f)


def _write(data):
    with open(CALENDAR_FILE, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def add_calendar_event(event_date, event_time, description):
    data = _read()
    data["events"].append({"date": event_date, "time": event_time, "description": description})
    data["events"].sort(key=lambda e: (e["date"], e["time"]))
    _write(data)
    return f"已添加日程: {event_date} {event_time} - {description}"


def query_calendar_events(query_date=None):
    data = _read()
    if query_date:
        matched = [e for e in data["events"] if e["date"] == query_date]
        if not matched:
            return f"{query_date} 没有安排"
        lines = [f"{e['time']} - {e['description']}" for e in matched]
        return f"{query_date} 的安排:\n" + "\n".join(lines)

    today = date.today().isoformat()
    upcoming = [e for e in data["events"] if e["date"] >= today]
    if not upcoming:
        return "没有即将到来的事件"
    lines = [f"{e['date']} {e['time']} - {e['description']}" for e in upcoming]
    return "即将到来的事件:\n" + "\n".join(lines)


def delete_calendar_event(event_date, description_keyword):
    """
    按日期 + 描述关键词删除日程。如果没有"修改"工具，LLM 用 删除+添加 实现修改。
    """
    data = _read()
    before = len(data["events"])
    keyword = description_keyword.lower()
    data["events"] = [
        e for e in data["events"]
        if not (e["date"] == event_date and keyword in e["description"].lower())
    ]
    removed = before - len(data["events"])
    if removed == 0:
        return f"未找到 {event_date} 匹配 '{description_keyword}' 的日程"
    _write(data)
    return f"已删除 {removed} 条日程（{event_date} 包含'{description_keyword}'）"
