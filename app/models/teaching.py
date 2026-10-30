"""课程 / 选课 / 考勤：支撑教务过程的三个实体。

* course     课程：某学期、某班级、某学科、由某位教师开的一门课
* enrollment 选课：学生与课程的选修关系（同一门课同一学生唯一）
* attendance 考勤：某门课某一天某个学生的出勤状态
"""
from typing import Optional

from sqlalchemy import Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, StatusMixin, TimestampMixin

# 出勤状态字典（值 -> 文案，前端与统计共用）
ATTENDANCE_STATUS = {0: "缺勤", 1: "出勤", 2: "迟到", 3: "请假"}
# 计入「到课」的状态
ATTENDANCE_PRESENT = (1, 2, 3)


class Course(TimestampMixin, StatusMixin, Base):
    """课程：学期 + 班级 + 学科 + 任课教师。"""

    __tablename__ = "course"
    __table_args__ = (UniqueConstraint("xueqi_id", "banji_id", "subject_id", name="uq_course"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(50), nullable=False, comment="课程名称")
    xueqi_id: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="学期")
    banji_id: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="班级")
    subject_id: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="学科")
    teacher_id: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="任课教师")
    keshi: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="课时数")
    beizhu: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)


class Enrollment(TimestampMixin, StatusMixin, Base):
    """选课：学生选了某门课。"""

    __tablename__ = "enrollment"
    __table_args__ = (UniqueConstraint("course_id", "student_id", name="uq_enrollment"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    course_id: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="课程")
    student_id: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="学生")
    xuanke_time: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="选课时间")
    beizhu: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)


class Attendance(TimestampMixin, Base):
    """考勤：一门课一天一条记录。"""

    __tablename__ = "attendance"
    __table_args__ = (
        UniqueConstraint("course_id", "student_id", "riqi", name="uq_attendance"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    course_id: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="课程")
    student_id: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="学生")
    riqi: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="日期(时间戳,取当天零点)")
    zhuangtai: Mapped[int] = mapped_column(
        Integer, default=1, nullable=False, comment="0=缺勤，1=出勤，2=迟到，3=请假"
    )
    beizhu: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
