"""面试回答有效性：与前端语音占位符约定一致。"""


def is_effective_user_answer(answer: str | None) -> bool:
    """
    有效作答：非空且非语音占位符「1」（转写完成前客户端会先写 1）。
    """
    s = (answer or "").strip()
    if not s:
        return False
    if s == "1":
        return False
    return True
