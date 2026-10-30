"""模块注册表：用配置描述一个模块的列表列 / 表单字段 / 搜索条件。

这样「单位 / 学期 / 班级 / 学科 / 学生 / 教师 / 管理员」这些结构相似的模块
不必各写一套路由和模板，只声明配置即可。
"""
from __future__ import annotations

from dataclasses import dataclass, field as dc_field
from typing import Optional


@dataclass
class Field:
    name: str
    label: str
    type: str = "text"  # text | number | select | date | textarea | switch
    required: bool = False
    # 选项来源：'category:101' 取类别子项；'school'/'banji'/'subject' 取对应表
    options_from: Optional[str] = None
    width: int = 120
    in_list: bool = True
    in_form: bool = True
    in_search: bool = False
    # 列表时把外键显示成对方的名称，如 ref='school.title' 表示 school_id -> School.title
    ref: Optional[str] = None
    placeholder: str = ""


@dataclass
class Module:
    key: str
    title: str
    model: type
    fields: list
    order_by: str = "id"
    search_fields: list = dc_field(default_factory=list)  # 关键字模糊匹配字段
    extra_toolbar: list = dc_field(default_factory=list)
    rowbar: list = dc_field(default_factory=list)

    def list_fields(self):
        return [f for f in self.fields if f.in_list]

    def form_fields(self):
        return [f for f in self.fields if f.in_form]

    def search_defs(self):
        return [f for f in self.fields if f.in_search]


def _f(*args, **kwargs):
    return Field(*args, **kwargs)


SCHOOL = Module(
    key="school",
    title="单位管理",
    model=None,  # 运行时注入，见 registry.bind_models()
    search_fields=["title", "jiancheng"],
    fields=[
        _f("id", "ID", "number", width=60),
        _f("title", "单位名称", required=True, width=180),
        _f("jiancheng", "简称", required=True, width=100),
        _f("xingzhi_id", "单位性质", "select", options_from="category:101", ref="category.title", width=110),
        _f("jibie_id", "单位级别", "select", options_from="category:102", ref="category.title", width=100),
        _f("xueduan_id", "学段", "select", options_from="category:103", ref="category.title", width=100),
        _f("kaoshi", "组织考试", "switch", width=90),
        _f("paixu", "排序", "number", width=70),
        _f("status", "状态", "switch", width=80),
        _f("beizhu", "备注", "textarea", width=140),
    ],
)

XUEQI = Module(
    key="xueqi",
    title="学期管理",
    model=None,
    search_fields=["title", "xuenian"],
    fields=[
        _f("id", "ID", "number", width=60),
        _f("title", "学期名称", required=True, width=140),
        _f("xuenian", "学年", required=True, width=110),
        _f("category_id", "学期分类", "select", options_from="category:108", ref="category.title", width=110),
        _f("bfdate", "开始日期", "date", width=110),
        _f("enddate", "结束日期", "date", width=110),
        _f("status", "状态", "switch", width=80),
        _f("beizhu", "备注", "textarea"),
    ],
)

BANJI = Module(
    key="banji",
    title="班级管理",
    model=None,
    search_fields=[],
    fields=[
        _f("id", "ID", "number", width=60),
        _f("school_id", "学校", "select", options_from="school", ref="school.title", required=True, width=150),
        _f("ruxuenian", "入学年", "number", required=True, width=90),
        _f("paixu", "班序号", "number", required=True, width=90),
        _f("xueduan_id", "学段", "select", options_from="category:103", ref="category.title", width=100),
        _f("alias", "班级别名", width=120),
        _f("status", "状态", "switch", width=80),
    ],
)

SUBJECT = Module(
    key="subject",
    title="学科管理",
    model=None,
    search_fields=["title"],
    fields=[
        _f("id", "ID", "number", width=60),
        _f("title", "学科名称", required=True, width=130),
        _f("jiancheng", "简称", required=True, width=90),
        _f("lieming", "列名(英文)", required=True, width=130, placeholder="如 chinese"),
        _f("category_id", "学科类别", "select", options_from="category:110", ref="category.title", width=110),
        _f("kaoshi", "参加考试", "switch", width=100),
        _f("paixu", "排序", "number", width=70),
        _f("status", "状态", "switch", width=80),
    ],
)

TEACHER = Module(
    key="teacher",
    title="教师管理",
    model=None,
    search_fields=["xingming", "phone"],
    fields=[
        _f("id", "ID", "number", width=60),
        _f("xingming", "姓名", required=True, width=90),
        _f("sex", "性别", "select", width=70, options_from="sex"),
        _f("phone", "手机号", width=120),
        _f("danwei_id", "所在单位", "select", options_from="school", ref="school.title", width=140),
        _f("subject_id", "学科", "select", options_from="subject", ref="subject.title", width=90),
        _f("zhiwu_id", "职务", "select", options_from="category:107", ref="category.title", width=120),
        _f("zhicheng_id", "职称", "select", options_from="category:106", ref="category.title", width=110),
        _f("status", "状态", "switch", width=80),
    ],
)

STUDENT = Module(
    key="student",
    title="学生管理",
    model=None,
    search_fields=["xingming", "shenfenzhenghao"],
    fields=[
        _f("id", "ID", "number", width=60),
        _f("xingming", "姓名", required=True, width=90),
        _f("sex", "性别", "select", width=70, options_from="sex"),
        _f("banji_id", "班级", "select", options_from="banji", ref="banji.full_title", required=True, width=130),
        _f("shenfenzhenghao", "身份证号(登录帐号)", width=180),
        _f("xuehao", "学号", width=110),
        _f("shengri", "生日", "date", width=110),
        _f("kaoshi", "参加考试", "switch", width=100),
        _f("status", "状态", "switch", width=80),
    ],
)

ADMIN_USER = Module(
    key="admin_user",
    title="用户管理",
    model=None,
    search_fields=["xingming", "username", "phone"],
    fields=[
        _f("id", "ID", "number", width=60),
        _f("xingming", "姓名", required=True, width=90),
        _f("username", "登录帐号", required=True, width=120),
        _f("phone", "手机号", width=120),
        _f("school_id", "所在单位", "select", options_from="school", ref="school.title", width=140),
        _f("teacher_id", "关联教师", "select", options_from="teacher", ref="teacher.xingming", width=100),
        _f("zhiwu_id", "职务", "select", options_from="category:107", ref="category.title", width=120),
        _f("status", "状态", "switch", width=80),
    ],
)

COURSE = Module(
    key="course",
    title="课程管理",
    model=None,
    search_fields=["title"],
    fields=[
        _f("id", "ID", "number", width=60),
        _f("title", "课程名称", required=True, width=150, placeholder="如 2024级1班语文"),
        _f("xueqi_id", "学期", "select", options_from="xueqi", ref="xueqi.title", required=True, width=150),
        _f("banji_id", "班级", "select", options_from="banji", ref="banji.full_title", required=True, width=130),
        _f("subject_id", "学科", "select", options_from="subject", ref="subject.title", width=90),
        _f("teacher_id", "任课教师", "select", options_from="teacher", ref="teacher.xingming", width=100),
        _f("keshi", "课时数", "number", width=80),
        _f("status", "状态", "switch", width=80),
        _f("beizhu", "备注", "textarea"),
    ],
    rowbar=[
        {"event": "edit", "title": "编辑"},
        {"event": "enroll", "title": "选课名单",
         "js": "xadmin.open('选课名单','/enrollment/batch?course_id='+obj.data.id,900,640);"},
        {"event": "attend", "title": "考勤",
         "js": "xadmin.open('考勤录入','/attendance?course_id='+obj.data.id,1100,720);"},
    ],
)

ENROLLMENT = Module(
    key="enrollment",
    title="选课管理",
    model=None,
    search_fields=["beizhu"],
    fields=[
        _f("id", "ID", "number", width=60),
        _f("course_id", "课程", "select", options_from="course", ref="course.title", required=True, width=180),
        _f("student_id", "学生", "select", options_from="student", ref="student.xingming", required=True, width=100),
        _f("xuanke_time", "选课时间", "date", width=110),
        _f("status", "状态", "switch", width=80),
        _f("beizhu", "备注", "textarea"),
    ],
    extra_toolbar=[
        {"event": "batch", "title": "按班级批量选课", "js": "xadmin.open('批量选课','/enrollment/batch',900,600);"},
    ],
)

CATEGORY = Module(
    key="category",
    title="类别管理",
    model=None,
    search_fields=["title"],
    fields=[
        _f("id", "ID", "number", width=70),
        _f("title", "类别名称", required=True, width=150),
        _f("p_id", "父级ID", "number", width=90),
        _f("paixu", "排序", "number", width=70),
        _f("status", "状态", "switch", width=80),
        _f("beizhu", "备注", "textarea"),
    ],
)

MODULES = [
    SCHOOL, XUEQI, BANJI, SUBJECT, TEACHER, STUDENT, ADMIN_USER, CATEGORY,
    COURSE, ENROLLMENT,
]


def bind_models():
    """延迟绑定模型类，避免与 models 包循环导入。"""
    from .models import (
        Admin,
        Banji,
        Category,
        Course,
        Enrollment,
        School,
        Student,
        Subject,
        Teacher,
        Xueqi,
    )

    mapping = {
        "school": School,
        "xueqi": Xueqi,
        "banji": Banji,
        "subject": Subject,
        "teacher": Teacher,
        "student": Student,
        "admin_user": Admin,
        "category": Category,
        "course": Course,
        "enrollment": Enrollment,
    }
    for m in MODULES:
        m.model = mapping[m.key]


def get(key: str) -> Optional[Module]:
    for m in MODULES:
        if m.key == key:
            return m
    return None
