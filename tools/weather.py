"""天气查询工具。使用 wttr.in 免费 API。"""
import requests


def get_weather(city):
    try:
        url = f"https://wttr.in/{city}?format=%C+%t&lang=zh"
        resp = requests.get(url, timeout=5)
        resp.raise_for_status()
        return f"{city}天气: {resp.text.strip()}"
    except Exception as e:
        return f"查询 {city} 天气失败: {e}"
