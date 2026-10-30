"""数据模型包。

表结构与字段命名在本项目内统一设计：单复数、后缀（_id / _time / status）在各模型间保持一致，
成绩表以「考号 + 学科」为维度建模，统计表按班级 / 年级 / 全校三级分表存放。
"""
from .base import Base, StatusMixin, TimestampMixin, now_ts, str_to_ts, ts_to_str
from .category import Category, SystemBase
from .school import Banji, School, Subject, Xueqi
from .people import (
    Admin,
    AuthGroup,
    AuthGroupAccess,
    AuthRule,
    BanZhuRen,
    FenGong,
    Student,
    Teacher,
)
from .kaoshi import Kaoshi, KaoshiSet, LuruFengong, TongjiLog
from .chengji import Chengji, Kaohao, TongjiBj, TongjiNj, TongjiSch
from .teaching import ATTENDANCE_PRESENT, ATTENDANCE_STATUS, Attendance, Course, Enrollment

__all__ = [
    "Base",
    "TimestampMixin",
    "StatusMixin",
    "now_ts",
    "ts_to_str",
    "str_to_ts",
    "Category",
    "SystemBase",
    "School",
    "Xueqi",
    "Banji",
    "Subject",
    "Teacher",
    "Admin",
    "Student",
    "AuthRule",
    "AuthGroup",
    "AuthGroupAccess",
    "BanZhuRen",
    "FenGong",
    "Kaoshi",
    "KaoshiSet",
    "LuruFengong",
    "TongjiLog",
    "Kaohao",
    "Chengji",
    "TongjiBj",
    "TongjiNj",
    "TongjiSch",
    "Course",
    "Enrollment",
    "Attendance",
    "ATTENDANCE_STATUS",
    "ATTENDANCE_PRESENT",
]
