"""school 单位 / banji 班级 / xueqi 学期 / subject 学科。"""
from typing import Optional

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, StatusMixin, TimestampMixin


class School(TimestampMixin, StatusMixin, Base):
    __tablename__ = "school"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(25), nullable=False, comment="单位名称")
    jiancheng: Mapped[str] = mapped_column(String(6), nullable=False, comment="单位简称")
    biaoshi: Mapped[Optional[str]] = mapped_column(String(11), nullable=True, comment="单位标识")
    xingzhi_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="单位性质")
    jibie_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="单位级别")
    xueduan_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="学段")
    kaoshi: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False, comment="能不能组织考试，0=不能，1=能"
    )
    paixu: Mapped[int] = mapped_column(Integer, default=999, nullable=False, comment="排序")
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
    title: Mapped[str] = mapped_column(String(25), nullable=False, comment="学期标题")
    xuenian: Mapped[str] = mapped_column(String(15), nullable=False, comment="学年标题")
    category_id: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="学期分类")
    bfdate: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="开始日期")
    enddate: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="结束日期")
    beizhu: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)


class Banji(TimestampMixin, StatusMixin, Base):
    __tablename__ = "banji"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    school_id: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="学校")
    ruxuenian: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="入学年")
    xueduan_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="学段")
    paixu: Mapped[int] = mapped_column(Integer, default=100, nullable=False, comment="排序")
    alias: Mapped[Optional[str]] = mapped_column(String(24), nullable=True, comment="班级别名")

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
        return f"{self.paixu}班"

    @property
    def full_title(self) -> str:
        """带学校的完整班名，例如「长兴岛二小2024级2班」。

        多所学校存在同名班级（各校都有 1班/2班），跨校统计必须带上学校才能区分。
        """
        base = f"{self.ruxuenian}级{self.paixu}班" if self.ruxuenian else f"{self.paixu}班"
        sch = getattr(self, "school", None)
        if sch is None:
            return base
        return f"{sch.jiancheng or sch.title}{base}"


class Subject(TimestampMixin, StatusMixin, Base):
    __tablename__ = "subject"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(25), nullable=False, comment="学科名称")
    jiancheng: Mapped[str] = mapped_column(String(6), nullable=False, comment="简称")
    lieming: Mapped[str] = mapped_column(String(46), nullable=False, comment="列名")
    category_id: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="大学科类别")
    kaoshi: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="是否参与考试")
    paixu: Mapped[int] = mapped_column(Integer, default=999, nullable=False, comment="排序")
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
