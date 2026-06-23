"""时间查询工具。零依赖。"""
from datetime import datetime


def get_current_time():
    now = datetime.now()
    weekday = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][now.weekday()]
    return f"现在是 {now.year}年{now.month}月{now.day}日 {weekday} {now.hour:02d}:{now.minute:02d}"
