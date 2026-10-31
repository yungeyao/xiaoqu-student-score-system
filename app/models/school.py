"""school Schools / banji Class / xueqi Semester / subject Subject。"""
from typing import Optional

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, StatusMixin, TimestampMixin


class School(TimestampMixin, StatusMixin, Base):
    __tablename__ = "school"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(25), nullable=False, comment="SchoolsName")
    jiancheng: Mapped[str] = mapped_column(String(6), nullable=False, comment="Short name")
    biaoshi: Mapped[Optional[str]] = mapped_column(String(11), nullable=True, comment="School code")
    xingzhi_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="School type")
    jibie_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="School level")
    xueduan_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="Stage")
    kaoshi: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False, comment="能不能Organises exams, 0=不能, 1=能"
    )
    paixu: Mapped[int] = mapped_column(Integer, default=999, nullable=False, comment="Order")
    beizhu: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)

    @property
    def xingzhi_name(self) -> str:
        return _cat_name(self.xingzhi_id)

    @property
    def xueduan_name(self) -> str:
        return _cat_name(self.xueduan_id)


class Xueqi(TimestampMixin, StatusMixin, Base):
    __tablename__ = "xueqi"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(25), nullable=False, comment="Semester标题")
    xuenian: Mapped[str] = mapped_column(String(15), nullable=False, comment="Academic year标题")
    category_id: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="Semester分类")
    bfdate: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="Start date")
    enddate: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="End date")
    beizhu: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)


class Banji(TimestampMixin, StatusMixin, Base):
    __tablename__ = "banji"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    school_id: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="学校")
    ruxuenian: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="Cohort")
    xueduan_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="Stage")
    paixu: Mapped[int] = mapped_column(Integer, default=100, nullable=False, comment="Order")
    alias: Mapped[Optional[str]] = mapped_column(String(24), nullable=True, comment="Class别名")

    # 非外键关联：school_id 只是普通整型列，这里显式声明 foreign 以便预加载学校
    school: Mapped[Optional["School"]] = relationship(
        "School",
        primaryjoin="foreign(Banji.school_id) == School.id",
        viewonly=True,
        lazy="selectin",
    )

    @property
    def title(self) -> str:
        """班级显示名：排序号 + 班。

        不按学段推算年级名，改用「入学年 + 序号」的通用写法，学段调整时不用改数据。
        例如 2021 年入学、排序 3 -> 3班；完整显示名见 full_title。
        """
        return f"Class {self.paixu}"

    @property
    def full_title(self) -> str:
        """带学校的完整班名，例如「长兴岛二小2024级2班」。

        多所学校存在同名班级（各校都有 1班/2班），跨校统计必须带上学校才能区分。
        """
        base = f"Class {self.paixu} ({self.ruxuenian})" if self.ruxuenian else f"Class {self.paixu}"
        sch = getattr(self, "school", None)
        if sch is None:
            return base
        return f"{sch.jiancheng or sch.title} · {base}"


class Subject(TimestampMixin, StatusMixin, Base):
    __tablename__ = "subject"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(25), nullable=False, comment="SubjectName")
    jiancheng: Mapped[str] = mapped_column(String(6), nullable=False, comment="Short name")
    lieming: Mapped[str] = mapped_column(String(46), nullable=False, comment="Column name")
    category_id: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="大Subject类别")
    kaoshi: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="Takes exams")
    paixu: Mapped[int] = mapped_column(Integer, default=999, nullable=False, comment="Order")
    beizhu: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)


def _cat_name(cat_id: Optional[int]) -> str:
    """延迟导入避免循环依赖。"""
    if not cat_id:
        return ""
    from .category import Category

    from ..core.database import SessionLocal

    with SessionLocal() as db:
        cat = db.get(Category, cat_id)
        return cat.title if cat else ""
