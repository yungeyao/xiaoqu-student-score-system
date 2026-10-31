"""模型基类与公共 Mixin。

全站时间统一用整数 unix 时间戳存：跨库一致、比较和排序都便宜，
展示时由 ts_to_str 转成本地日期字符串。软删除用 delete_time 标记。
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import Integer
from sqlalchemy.orm import Mapped, mapped_column

from ..core.database import Base


def now_ts() -> int:
    return int(datetime.now().timestamp())


def ts_to_str(ts: Optional[int], fmt: str = "%Y-%m-%d") -> str:
    """时间戳转字符串, 供前端展示。"""
    if not ts:
        return ""
    try:
        return datetime.fromtimestamp(int(ts)).strftime(fmt)
    except (ValueError, OSError, OverflowError):
        return ""


def str_to_ts(text, fmt: str = "%Y-%m-%d"):
    """把前端传来的日期转成 unix 时间戳。

    前端可能给好几种形式：纯时间戳、``2025-09-01``、``2025/09/01``、
    带时分秒的 ``2025-09-01 08:30``。只认 ``%Y-%m-%d`` 的话其余一律返回
    None，必填日期列就会被写成 NULL 进而触发 NOT NULL 约束。
    """
    if text is None or text == "":
        return None
    # 数字（或纯数字字符串）直接视为时间戳
    if isinstance(text, (int, float)):
        return int(text)
    s = str(text).strip()
    if s.lstrip("-").isdigit():
        return int(s)

    s = s.replace("T", " ").replace("/", "-")
    for f in (fmt, f"{fmt} %H:%M", f"{fmt} %H:%M:%S"):
        try:
            return int(datetime.strptime(s, f).timestamp())
        except ValueError:
            continue
    return None


class TimestampMixin:
    create_time: Mapped[int] = mapped_column(Integer, default=now_ts, nullable=False)
    update_time: Mapped[int] = mapped_column(
        Integer, default=now_ts, onupdate=now_ts, nullable=False
    )
    delete_time: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, default=None)


class StatusMixin:
    """0=禁用, 1=正常"""
    status: Mapped[int] = mapped_column(Integer, default=1, nullable=False, comment="0=禁用, 1=正常")


__all__ = ["Base", "TimestampMixin", "StatusMixin", "now_ts", "ts_to_str", "str_to_ts"]
