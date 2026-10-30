"""kaoshi 考试 / kaoshi_set 考试学科设置 / luru_fengong 录入分工。"""
from typing import Optional

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, StatusMixin, TimestampMixin


class Kaoshi(TimestampMixin, StatusMixin, Base):
    __tablename__ = "kaoshi"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(25), nullable=False, comment="考试名称")
    zuzhi_id: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="组织考试单位")
    xueqi_id: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="学期")
    category_id: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="类别")
    user_id: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="创建者")
    fanwei_id: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="允许查看范围ID")
    bfdate: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="开始日期")
    enddate: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="结束日期")
    luru: Mapped[int] = mapped_column(Integer, default=1, nullable=False, comment="0=不允许录入，1=允许")
    beizhu: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)


class KaoshiSet(TimestampMixin, StatusMixin, Base):
    """某场考试里，某年级某学科的满分与分数线。"""

    __tablename__ = "kaoshi_set"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    kaoshi_id: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="考试id")
    ruxuenian: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="入学年")
    nianjiname: Mapped[str] = mapped_column(String(10), default="", nullable=False, comment="年级名")
    subject_id: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="学科id")
    manfen: Mapped[int] = mapped_column(Integer, default=100, nullable=False, comment="满分")
    youxiu: Mapped[int] = mapped_column(Integer, default=85, nullable=False, comment="优秀分数线")
    lianghao: Mapped[int] = mapped_column(Integer, default=75, nullable=False, comment="良好分数线")
    jige: Mapped[int] = mapped_column(Integer, default=60, nullable=False, comment="及格分数线")
    youxiubi: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="优秀人数比")
    lianghaobi: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="良好人数比")
    jigebi: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="及格人数比")


class LuruFengong(TimestampMixin, Base):
    """考试录入分工：限定谁能录哪个班哪科的成绩。

    该考试没有任何分工记录时默认放行；一旦有记录，就必须匹配到 admin_id。
    """

    __tablename__ = "luru_fengong"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    kaoshi_id: Mapped[int] = mapped_column(Integer, nullable=False, comment="考试id")
    admin_id: Mapped[int] = mapped_column(Integer, nullable=False, comment="用户id")
    banji_id: Mapped[int] = mapped_column(Integer, nullable=False, comment="班级id")
    subject_id: Mapped[int] = mapped_column(Integer, nullable=False, comment="学科id")


class TongjiLog(TimestampMixin, Base):
    """统计操作日志。"""

    __tablename__ = "tongji_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    kaoshi_id: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="考试id")
    user_id: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="操作人")
    category_id: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="统计类型")
    title: Mapped[Optional[str]] = mapped_column(String(60), nullable=True)
