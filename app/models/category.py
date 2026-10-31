"""category 类别字典表 + system_base 系统设置。

类别是全局的树形字典：单位性质(101)/单位级别(102)/大学段(103)/小学段(104)/
学历(105)/职务(106或107)/职称/学科类别/考试类别/学期分类……
层级用 id 分段编码表达（父 101 -> 子 10101），父链一眼可读，省掉递归查询。
"""
from typing import Optional

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, StatusMixin, TimestampMixin


class Category(TimestampMixin, StatusMixin, Base):
    __tablename__ = "category"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(50), default="a", nullable=False, comment="类型标题")
    p_id: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="Parent ID")
    paixu: Mapped[int] = mapped_column(Integer, default=999, nullable=False, comment="Order")
    isupdate: Mapped[int] = mapped_column(
        Integer, default=1, nullable=False, comment="0=不允许updated, 1=允许updated"
    )
    beizhu: Mapped[Optional[str]] = mapped_column(String(80), nullable=True, comment="Note")


class SystemBase(TimestampMixin, Base):
    __tablename__ = "system_base"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sys_title: Mapped[str] = mapped_column(String(60), default="Student Management System", nullable=False)
    keywords: Mapped[Optional[str]] = mapped_column(String(60), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    thinks: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    danwei: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, comment="使用Schools")
    gradelist: Mapped[Optional[str]] = mapped_column(
        String(200), default="一Grade|二Grade|三Grade|四Grade|五Grade|六Grade", comment="GradeName列表"
    )
    classmax: Mapped[int] = mapped_column(Integer, default=30, nullable=False, comment="最大Class数")
    classalias: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="YesNo开启Class别名")
    studefen: Mapped[int] = mapped_column(Integer, default=1, nullable=False, comment="Student能No查看分数")
    teacher_guoqi: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    student_guoqi: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
