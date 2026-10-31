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
    title="Schools",
    model=None,  # 运行时注入，见 registry.bind_models()
    search_fields=["title", "jiancheng"],
    fields=[
        _f("id", "ID", "number", width=60),
        _f("title", "SchoolsName", required=True, width=180),
        _f("jiancheng", "Short name", required=True, width=100),
        _f("xingzhi_id", "School type", "select", options_from="category:101", ref="category.title", width=110),
        _f("jibie_id", "School level", "select", options_from="category:102", ref="category.title", width=100),
        _f("xueduan_id", "Stage", "select", options_from="category:103", ref="category.title", width=100),
        _f("kaoshi", "Organises exams", "switch", width=90),
        _f("paixu", "Order", "number", width=70),
        _f("status", "Status", "switch", width=80),
        _f("beizhu", "Note", "textarea", width=140),
    ],
)

XUEQI = Module(
    key="xueqi",
    title="Semesters",
    model=None,
    search_fields=["title", "xuenian"],
    fields=[
        _f("id", "ID", "number", width=60),
        _f("title", "SemesterName", required=True, width=140),
        _f("xuenian", "Academic year", required=True, width=110),
        _f("category_id", "Semester type", "select", options_from="category:108", ref="category.title", width=110),
        _f("bfdate", "Start date", "date", width=110),
        _f("enddate", "End date", "date", width=110),
        _f("status", "Status", "switch", width=80),
        _f("beizhu", "Note", "textarea"),
    ],
)

BANJI = Module(
    key="banji",
    title="Classes",
    model=None,
    search_fields=[],
    fields=[
        _f("id", "ID", "number", width=60),
        _f("school_id", "School", "select", options_from="school", ref="school.title", required=True, width=150),
        _f("ruxuenian", "Cohort", "number", required=True, width=90),
        _f("paixu", "Class number", "number", required=True, width=90),
        _f("xueduan_id", "Stage", "select", options_from="category:103", ref="category.title", width=100),
        _f("alias", "Alias", width=120),
        _f("status", "Status", "switch", width=80),
    ],
)

SUBJECT = Module(
    key="subject",
    title="Subjects",
    model=None,
    search_fields=["title"],
    fields=[
        _f("id", "ID", "number", width=60),
        _f("title", "SubjectName", required=True, width=130),
        _f("jiancheng", "Short name", required=True, width=90),
        _f("lieming", "Column name", required=True, width=130, placeholder="e.g. chinese"),
        _f("category_id", "Subject category", "select", options_from="category:110", ref="category.title", width=110),
        _f("kaoshi", "Takes exams", "switch", width=100),
        _f("paixu", "Order", "number", width=70),
        _f("status", "Status", "switch", width=80),
    ],
)

TEACHER = Module(
    key="teacher",
    title="Teachers",
    model=None,
    search_fields=["xingming", "phone"],
    fields=[
        _f("id", "ID", "number", width=60),
        _f("xingming", "Name", required=True, width=90),
        _f("sex", "Gender", "select", width=70, options_from="sex"),
        _f("phone", "Phone", width=120),
        _f("danwei_id", "School", "select", options_from="school", ref="school.title", width=140),
        _f("subject_id", "Subject", "select", options_from="subject", ref="subject.title", width=90),
        _f("zhiwu_id", "Position", "select", options_from="category:107", ref="category.title", width=120),
        _f("zhicheng_id", "Title", "select", options_from="category:106", ref="category.title", width=110),
        _f("status", "Status", "switch", width=80),
    ],
)

STUDENT = Module(
    key="student",
    title="Students",
    model=None,
    search_fields=["xingming", "shenfenzhenghao"],
    fields=[
        _f("id", "ID", "number", width=60),
        _f("xingming", "Name", required=True, width=90),
        _f("sex", "Gender", "select", width=70, options_from="sex"),
        _f("banji_id", "Class", "select", options_from="banji", ref="banji.full_title", required=True, width=130),
        _f("shenfenzhenghao", "ID number (login)", width=180),
        _f("xuehao", "Student no.", width=110),
        _f("shengri", "Date of birth", "date", width=110),
        _f("kaoshi", "Takes exams", "switch", width=100),
        _f("status", "Status", "switch", width=80),
    ],
)

ADMIN_USER = Module(
    key="admin_user",
    title="Users",
    model=None,
    search_fields=["xingming", "username", "phone"],
    fields=[
        _f("id", "ID", "number", width=60),
        _f("xingming", "Name", required=True, width=90),
        _f("username", "Login name", required=True, width=120),
        _f("phone", "Phone", width=120),
        _f("school_id", "School", "select", options_from="school", ref="school.title", width=140),
        _f("teacher_id", "Linked teacher", "select", options_from="teacher", ref="teacher.xingming", width=100),
        _f("zhiwu_id", "Position", "select", options_from="category:107", ref="category.title", width=120),
        _f("status", "Status", "switch", width=80),
    ],
)

COURSE = Module(
    key="course",
    title="Courses",
    model=None,
    search_fields=["title"],
    fields=[
        _f("id", "ID", "number", width=60),
        _f("title", "Course name", required=True, width=150, placeholder="e.g. Class 1 Chinese"),
        _f("xueqi_id", "Semester", "select", options_from="xueqi", ref="xueqi.title", required=True, width=150),
        _f("banji_id", "Class", "select", options_from="banji", ref="banji.full_title", required=True, width=130),
        _f("subject_id", "Subject", "select", options_from="subject", ref="subject.title", width=90),
        _f("teacher_id", "Teacher", "select", options_from="teacher", ref="teacher.xingming", width=100),
        _f("keshi", "Hours", "number", width=80),
        _f("status", "Status", "switch", width=80),
        _f("beizhu", "Note", "textarea"),
    ],
    rowbar=[
        {"event": "edit", "title": "Edit"},
        {"event": "enroll", "title": "Enrolment",
         "js": "xadmin.open('Enrolment','/enrollment/batch?course_id='+obj.data.id,900,640);"},
        {"event": "attend", "title": "Attendance",
         "js": "xadmin.open('Attendance','/attendance?course_id='+obj.data.id,1100,720);"},
    ],
)

ENROLLMENT = Module(
    key="enrollment",
    title="Enrolments",
    model=None,
    search_fields=["beizhu"],
    fields=[
        _f("id", "ID", "number", width=60),
        _f("course_id", "Course", "select", options_from="course", ref="course.title", required=True, width=180),
        _f("student_id", "Student", "select", options_from="student", ref="student.xingming", required=True, width=100),
        _f("xuanke_time", "Enrolled on", "date", width=110),
        _f("status", "Status", "switch", width=80),
        _f("beizhu", "Note", "textarea"),
    ],
    extra_toolbar=[
        {"event": "batch", "title": "Bulk enrol a class", "js": "xadmin.open('Bulk enrolment','/enrollment/batch',900,600);"},
    ],
)

CATEGORY = Module(
    key="category",
    title="Categories",
    model=None,
    search_fields=["title"],
    fields=[
        _f("id", "ID", "number", width=70),
        _f("title", "Category", required=True, width=150),
        _f("p_id", "Parent ID", "number", width=90),
        _f("paixu", "Order", "number", width=70),
        _f("status", "Status", "switch", width=80),
        _f("beizhu", "Note", "textarea"),
    ],
)

MODULES = [
    SCHOOL, XUEQI, BANJI, SUBJECT, TEACHER, STUDENT, ADMIN_USER, CATEGORY,
    COURSE, ENROLLMENT,
]


def bind_models():
    """延迟绑定模型类, 避免与 models 包循环导入。"""
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
