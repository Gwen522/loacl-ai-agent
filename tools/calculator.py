"""安全计算器。只允许数字和基本运算符。"""


def calculate(expression):
    cleaned = expression.strip()
    allowed = set("0123456789+-*/().%^ ")
    if not all(c in allowed for c in cleaned):
        return f"表达式包含不安全字符: {expression}"
    try:
        return str(eval(cleaned))
    except Exception as e:
        return f"计算失败: {e}"
