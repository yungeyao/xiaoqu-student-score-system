"""kaohao 考号 / chengji 成绩 / tongji_{bj,nj,sch} 三级统计结果表。"""
from typing import Optional

from sqlalchemy import DECIMAL, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, StatusMixin, TimestampMixin


class Kaohao(TimestampMixin, StatusMixin, Base):
    """考号：把「某场考试」与「某个学生」绑定，并冗余班级/年级/排序。

    对 (kaoshi_id, student_id) 建唯一索引，保证一场考试一个学生只有一个考号。
    """

    __tablename__ = "kaohao"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    kaoshi_id: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="考试")
    school_id: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="学校")
    ruxuenian: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="入学年")
    nianji: Mapped[str] = mapped_column(String(10), default="", nullable=False, comment="年级名")
    banji_id: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="班级")
    paixu: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="班级内序号")
    student_id: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="学生")
    kaohao: Mapped[Optional[str]] = mapped_column(String(30), nullable=True, comment="考号字符串")


class Chengji(TimestampMixin, StatusMixin, Base):
    """一条成绩 = (考号, 学科) 唯一。defen 为 NULL 表示缺考。"""

    __tablename__ = "chengji"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    kaohao_id: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="考号")
    user_id: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="录入人")
    subject_id: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="学科")
    defen: Mapped[Optional[float]] = mapped_column(
        DECIMAL(5, 1), nullable=True, default=None, comment="得分，NULL=缺考"
    )
    defenlv: Mapped[Optional[float]] = mapped_column(
        DECIMAL(6, 2), nullable=True, default=None, comment="得分率"
    )
    biaozhunfen: Mapped[Optional[float]] = mapped_column(
        DECIMAL(6, 2), nullable=True, default=None, comment="标准分Z"
    )
    # 班级排序/位置
    bpaixu: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="班级排序")
    bweizhi: Mapped[Optional[float]] = mapped_column(DECIMAL(6, 2), nullable=True, comment="班级位置")
    # 学校排序/位置
    xpaixu: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="学校排序")
    xweizhi: Mapped[Optional[float]] = mapped_column(DECIMAL(6, 2), nullable=True, comment="学校位置")
    # 全区排序/位置
    qpaixu: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="区排序")
    qweizhi: Mapped[Optional[float]] = mapped_column(DECIMAL(6, 2), nullable=True, comment="区位置")


class _TongjiMix:
    """三级统计表共用的指标列。

    注意：stu_cnt 是应考人数（含缺考），chengji_cnt 是实考人数。
    除参试率外，所有率的分母都是实考人数。
    """

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    kaoshi_id: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="考试")
    subject_id: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="学科")
    stu_cnt: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="应考人数")
    chengji_cnt: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="实考人数")
    sum: Mapped[Optional[float]] = mapped_column(DECIMAL(10, 1), nullable=True, comment="总分")
    avg: Mapped[Optional[float]] = mapped_column(DECIMAL(6, 2), nullable=True, comment="平均分")
    defenlv: Mapped[Optional[float]] = mapped_column(DECIMAL(6, 2), nullable=True, comment="得分率")
    biaozhuncha: Mapped[Optional[float]] = mapped_column(DECIMAL(6, 2), nullable=True, comment="标准差")
    youxiu: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="优秀人数")
    lianghao: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="良好人数")
    jige: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="及格人数")
    youxiulv: Mapped[Optional[float]] = mapped_column(DECIMAL(6, 2), nullable=True, comment="优秀率")
    lianghaolv: Mapped[Optional[float]] = mapped_column(DECIMAL(6, 2), nullable=True, comment="良好率")
    jigelv: Mapped[Optional[float]] = mapped_column(DECIMAL(6, 2), nullable=True, comment="及格率")
    canshilv: Mapped[Optional[float]] = mapped_column(DECIMAL(6, 2), nullable=True, comment="参试率")
    chashenglv: Mapped[Optional[float]] = mapped_column(DECIMAL(6, 2), nullable=True, comment="差生率")
    max: Mapped[Optional[float]] = mapped_column(DECIMAL(5, 1), nullable=True, comment="最高分")
    min: Mapped[Optional[float]] = mapped_column(DECIMAL(5, 1), nullable=True, comment="最低分")
    q1: Mapped[Optional[float]] = mapped_column(DECIMAL(6, 2), nullable=True, comment="下四分位")
    q2: Mapped[Optional[float]] = mapped_column(DECIMAL(6, 2), nullable=True, comment="中位数")
    q3: Mapped[Optional[float]] = mapped_column(DECIMAL(6, 2), nullable=True, comment="上四分位")
    zhongshu: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, comment="众数")
    zhongweishu: Mapped[Optional[float]] = mapped_column(DECIMAL(6, 2), nullable=True, comment="中位数")


class TongjiBj(_TongjiMix, TimestampMixin, StatusMixin, Base):
    """班级统计。粒度 = 考试 x 学科 x 班级。"""

    __tablename__ = "tongji_bj"

    teacher_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="任课教师")
    banji_id: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="班级")


class TongjiNj(_TongjiMix, TimestampMixin, StatusMixin, Base):
    """年级统计。粒度 = 考试 x 学科 x 学校 x 入学年。"""

    __tablename__ = "tongji_nj"

    school_id: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="学校")
    ruxuenian: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="入学年")


class TongjiSch(_TongjiMix, TimestampMixin, StatusMixin, Base):
    """全校/全区统计。粒度 = 考试 x 学科 x 入学年。"""

    __tablename__ = "tongji_sch"

    ruxuenian: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="入学年")
