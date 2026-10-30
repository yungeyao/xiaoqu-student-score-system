"""teacher 教师 / admin 管理员 / student 学生 / 权限三表。

登录实体只有两种：admin（超管与教师共用，靠 zhiwu_id 职务区分数据范围）和 student。
权限按 RBAC 拆成 auth_rule（规则）/ auth_group（角色）/ auth_group_access（用户-角色）。
"""
from typing import Optional

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, StatusMixin, TimestampMixin


class Teacher(TimestampMixin, StatusMixin, Base):
    __tablename__ = "teacher"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    xingming: Mapped[str] = mapped_column(String(8), nullable=False, comment="姓名")
    sex: Mapped[int] = mapped_column(Integer, default=1, nullable=False, comment="0=女，1=男，2=未知")
    shengri: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="生日")
    worktime: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="工作时间")
    zhiwu_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="职务")
    zhicheng_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="职称")
    danwei_id: Mapped[int] = mapped_column(Integer, default=1, nullable=False, comment="现工作单位")
    biye: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, comment="毕业学校")
    zhuanye: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, comment="专业")
    xueli_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="学历")
    subject_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="学科")
    quanpin: Mapped[Optional[str]] = mapped_column(String(30), nullable=True, comment="全拼")
    shoupin: Mapped[Optional[str]] = mapped_column(String(5), nullable=True, comment="简拼")
    tuixiu: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="是否已退休")
    phone: Mapped[Optional[str]] = mapped_column(String(11), nullable=True, comment="手机号")
    password: Mapped[Optional[str]] = mapped_column(String(200), nullable=True, comment="登录密码")
    beizhu: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)


class Admin(TimestampMixin, StatusMixin, Base):
    __tablename__ = "admin"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    xingming: Mapped[str] = mapped_column(String(15), nullable=False, comment="姓名")
    sex: Mapped[int] = mapped_column(Integer, default=2, nullable=False, comment="0=女，1=男，2=未知")
    username: Mapped[str] = mapped_column(String(20), nullable=False, unique=True, comment="登录帐号")
    password: Mapped[Optional[str]] = mapped_column(String(200), nullable=True, comment="登录密码")
    teacher_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="教师编号")
    school_id: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="所在单位")
    phone: Mapped[Optional[str]] = mapped_column(String(11), nullable=True, comment="联系方式")
    zhiwu_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="职务")
    zhicheng_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="职称")
    subject_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="学科")
    quanpin: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    shoupin: Mapped[Optional[str]] = mapped_column(String(5), nullable=True)
    login_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="登录次数")
    last_ip: Mapped[Optional[str]] = mapped_column(String(55), nullable=True)
    last_time: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="最后登录时间")
    guoqi: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="帐号过期时间")
    beizhu: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)

    @property
    def is_super(self) -> bool:
        from ..core.config import Auth

        return self.id in Auth.administrator


class Student(TimestampMixin, StatusMixin, Base):
    __tablename__ = "student"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    xingming: Mapped[str] = mapped_column(String(5), nullable=False, comment="姓名")
    sex: Mapped[int] = mapped_column(Integer, default=1, nullable=False, comment="0=女，1=男，2=未知")
    shengri: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="生日")
    shenfenzhenghao: Mapped[Optional[str]] = mapped_column(
        String(18), nullable=True, comment="身份证号（登录帐号）"
    )
    password: Mapped[Optional[str]] = mapped_column(String(200), nullable=True, comment="登录密码")
    banji_id: Mapped[int] = mapped_column(Integer, default=1, nullable=False, comment="班级")
    kaoshi: Mapped[int] = mapped_column(Integer, default=1, nullable=False, comment="是否参加考试")
    xuehao: Mapped[Optional[str]] = mapped_column(String(25), nullable=True, comment="自定义考号")
    quanpin: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    shoupin: Mapped[Optional[str]] = mapped_column(String(5), nullable=True)
    login_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_ip: Mapped[Optional[str]] = mapped_column(String(55), nullable=True)
    last_time: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    guoqi: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="帐号过期时间")


class AuthRule(TimestampMixin, StatusMixin, Base):
    """权限规则表。name 字段就是权限标识 = 小写的 模块/控制器/方法。"""

    __tablename__ = "auth_rule"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pid: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="父级ID")
    title: Mapped[str] = mapped_column(String(60), nullable=False, comment="规则名称")
    name: Mapped[Optional[str]] = mapped_column(String(80), nullable=True, comment="权限标识")
    url: Mapped[Optional[str]] = mapped_column(String(120), nullable=True, comment="菜单地址")
    ismenu: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="是否菜单")
    font: Mapped[Optional[str]] = mapped_column(String(30), nullable=True, comment="图标")
    paixu: Mapped[int] = mapped_column(Integer, default=999, nullable=False, comment="排序")
    condition: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, comment="附加条件")


class AuthGroup(TimestampMixin, StatusMixin, Base):
    """角色组。rules 是逗号分隔的 rule id 串。"""

    __tablename__ = "auth_group"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(60), nullable=False, comment="角色名称")
    rules: Mapped[Optional[str]] = mapped_column(String(500), nullable=True, comment="规则ID集合")
    beizhu: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)


class AuthGroupAccess(Base):
    """用户 <-> 角色 多对多。"""

    __tablename__ = "auth_group_access"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    uid: Mapped[int] = mapped_column(Integer, nullable=False, comment="用户ID")
    group_id: Mapped[int] = mapped_column(Integer, nullable=False, comment="角色ID")


class BanZhuRen(TimestampMixin, Base):
    """班主任任职记录。bfdate 起任职，取最新一条判断现任。"""

    __tablename__ = "ban_zhu_ren"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    teacher_id: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="教师ID")
    banji_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="班级ID")
    bfdate: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="开始日期")
    beizhu: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)


class FenGong(TimestampMixin, Base):
    """任课分工：某学期 某教师 教 某班 某学科。"""

    __tablename__ = "fen_gong"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    banji_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="班级ID")
    subject_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="学科ID")
    teacher_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="教师ID")
    bfdate: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="开始日期")
    xueqi_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="学期")
    beizhu: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
