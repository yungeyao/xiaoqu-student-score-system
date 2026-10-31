"""生成演示数据。

用法：
    python -m seed.seed          # 写入演示数据
    python -m seed.seed --reset  # 先清空再写入
"""
from __future__ import annotations

import random
import sys
from datetime import datetime

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent))

from sqlalchemy import select

from app.core.database import SessionLocal, engine  # noqa: E402
from app.core.security import password_hash  # noqa: E402
from app.models import (  # noqa: E402
    Admin,
    Attendance,
    AuthGroup,
    AuthGroupAccess,
    AuthRule,
    Banji,
    Base,
    BanZhuRen,
    Category,
    Chengji,
    Course,
    Enrollment,
    FenGong,
    Kaohao,
    Kaoshi,
    KaoshiSet,
    School,
    Student,
    Subject,
    SystemBase,
    Teacher,
    Xueqi,
)
from app.models.base import now_ts, str_to_ts  # noqa: E402
from app.services import kaohao as kh_service  # noqa: E402

random.seed(20261023)

CATEGORIES = [
    (101, "School type", 0), (10101, "Primary school", 101), (10102, "Nine-year school", 101), (10103, "Junior high", 101),
    (102, "School level", 0), (10201, "School", 102), (10202, "District", 102), (10203, "Municipal", 102),
    (103, "Stage", 0), (10301, "Primary school", 103), (10302, "Junior high", 103), (10303, "Senior high", 103),
    (105, "Education", 0), (10501, "College diploma", 105), (10502, "Bachelor", 105), (10503, "Master", 105),
    (106, "Title", 0), (10601, "Professor level", 106), (10602, "Senior", 106), (10603, "First grade", 106), (10604, "Second grade", 106),
    (107, "Position", 0), (10701, "Principal / Party secretary", 107), (10702, "Deputy secretary", 107),
    (10703, "Vice Principal (Academic)", 107), (10704, "Vice Principal (Student Affairs)", 107), (10705, "Academic Director", 107), (10710, "Other", 107),
    (108, "Semester", 0), (10801, "Semester 1", 108), (10802, "Semester 2", 108),
    (109, "Exam", 0), (10901, "Final Exam", 109), (10902, "Midterm Exam", 109), (10903, "Unit Test", 109),
    (110, "Subject", 0), (11001, "Chinese", 110), (11002, "Math", 110), (11003, "Foreign language", 110),
    (11004, "Moral education", 110), (11005, "Science", 110), (11006, "PE & Health", 110),
]

SUBJECTS = [
    ("Chinese", "Chinese", "yuwen", 11001, 1),
    ("Math", "Math", "shuxue", 11002, 1),
    ("English", "English", "yingyu", 11003, 1),
    ("Science", "Science", "kexue", 11005, 1),
    ("Ethics & Law", "Ethics", "daofa", 11004, 1),
    ("PE", "PE", "tiyu", 11006, 0),
    ("Music", "Music", "yinyue", 11008, 0),
    ("Art", "Art", "meishu", 11008, 0),
]

SCHOOLS = [
    ("Changxing Island Primary School", "Lab", 10101, 10301),
    ("Changxing Island No.2 Primary School", "No.2", 10101, 10301),
]

SURNAMES = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Miller", "Davis", "Wilson", "Anderson", "Taylor", "Thomas", "Moore", "Jackson", "Martin", "Lee", "Thompson", "White", "Harris", "Clark", "Lewis", "Walker", "Hall", "Young", "King"]
GIVEN1 = ["Emma", "Olivia", "Ava", "Sophia", "Isabella", "Mia", "Charlotte", "Amelia", "Harper", "Evelyn", "Liam", "Noah", "William", "James", "Benjamin", "Lucas", "Henry", "Alexander", "Mason", "Michael"]
GIVEN2 = ["Grace", "Rose", "Jane", "Anne", "Claire", "Alice", "Lucy", "Emily", "Daniel", "Thomas", "Peter", "George", "Edward", "Charles", "Arthur", "Albert", "Henry", "Oliver", "Jack", "Leo"]

MENU = [
    ("Basic data", "", 1, [
        ("Schools", "/school", 2), ("Semesters", "/xueqi", 3),
        ("Classes", "/banji", 4), ("Subjects", "/subject", 5),
    ]),
    ("People", "", 6, [
        ("Teachers", "/teacher", 7), ("Students", "/student", 8),
    ]),
    ("Exams", "", 10, [
        ("Exams", "/kaoshi", 11), ("Exam numbers", "/kaohao", 12),
    ]),
    ("Teaching", "", 15, [
        ("Courses", "/course", 16), ("Enrolments", "/enrollment", 17),
        ("Attendance", "/attendance", 18),
    ]),
    ("Grades", "", 20, [
        ("Grade entry", "/luru", 21), ("GradeQuery", "/chengji", 22),
    ]),
    ("Analytics", "", 30, [
        ("Class statistics", "/tongji/bj", 31), ("Grade statistics", "/tongji/nj", 32),
        ("School statistics", "/tongji/sch", 33), ("Academic risk", "/risk", 34),
    ]),
    ("Reports", "", 35, [
        ("Grade report", "/report", 36),
    ]),
    ("Settings", "", 40, [
        ("Users", "/admin_user", 41), ("Categories", "/category", 42),
    ]),
]


def _name():
    return f"{random.choice(GIVEN1)} {random.choice(SURNAMES)}"


def reset(db):
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)


def seed(db):
    # ---------------- 系统设置
    if not db.scalars(__import__("sqlalchemy").select(SystemBase)).first():
        db.add(SystemBase(sys_title="Student Management System", danwei="Changxing Island Primary School"))

    # ---------------- 类别
    for cid, title, pid in CATEGORIES:
        if db.get(Category, cid) is None:
            db.add(Category(id=cid, title=title, p_id=pid, paixu=cid % 100))
    db.commit()

    # ---------------- 学科
    subjects = {}
    for i, (title, jc, lm, cat, ks) in enumerate(SUBJECTS, start=1):
        s = Subject(title=title, jiancheng=jc, lieming=lm, category_id=cat,
                    kaoshi=ks, paixu=i * 10)
        db.add(s)
        db.flush()
        subjects[title] = s
    db.commit()
    exam_subjects = [s for s in subjects.values() if s.kaoshi == 1]

    # ---------------- 单位
    schools = {}
    for i, (title, jc, xz, xd) in enumerate(SCHOOLS, start=1):
        sc = School(title=title, jiancheng=jc, xingzhi_id=xz, xueduan_id=xd,
                     jibie_id=10201, kaoshi=1, paixu=i)
        db.add(sc)
        db.flush()
        schools[title] = sc
    db.commit()

    # ---------------- 学期
    xueqis = []
    for title, xn, bf, ef, cat in [
        ("2024-2025 Academic Year · Semester 1", "2024-2025", "2024-09-01", "2025-01-15", 10801),
        ("2024-2025 Academic Year · Semester 2", "2024-2025", "2025-02-17", "2025-07-10", 10802),
    ]:
        x = Xueqi(title=title, xuenian=xn, category_id=cat,
                  bfdate=str_to_ts(bf), enddate=str_to_ts(ef))
        db.add(x)
        db.flush()
        xueqis.append(x)
    db.commit()

    # ---------------- 班级：每校 6 个年级 × 2 个班
    banjis = []
    base_year = datetime.now().year if datetime.now().month >= 9 else datetime.now().year - 1
    for sc in schools.values():
        for grade in range(1, 7):
            ruxuenian = base_year - grade + 1
            for n in (1, 2):
                b = Banji(school_id=sc.id, ruxuenian=ruxuenian, xueduan_id=10301,
                          paixu=n, status=1)
                db.add(b)
                db.flush()
                banjis.append(b)
    db.commit()

    # ---------------- 学生：每班 20 人
    students = []
    for b in banjis:
        for i in range(20):
            sex = random.choice([0, 1])
            stu = Student(
                xingming=_name(), sex=sex, banji_id=b.id,
                shenfenzhenghao=f"2102{random.randint(10,99)}200{b.ruxuenian % 10}"
                                f"{random.randint(1,12):02d}{random.randint(1,28):02d}"
                                f"{random.randint(1000,9999)}",
                kaoshi=1, status=1,
                shengri=str_to_ts(f"{b.ruxuenian - 6}-{random.randint(1,12):02d}-{random.randint(1,28):02d}"),
                password=password_hash("123456"),
            )
            db.add(stu)
            db.flush()
            students.append(stu)
    db.commit()

    # ---------------- 教师
    teachers = []
    # school_id -> 该校教师（按学科顺序），任课分工只在本校内分配
    teachers_of_school: dict[int, list] = {}
    for sc in schools.values():
        group = []
        for sub in exam_subjects:
            t = Teacher(xingming=_name(), sex=random.choice([0, 1]), danwei_id=sc.id,
                        subject_id=sub.id, phone=f"139{random.randint(10000000,99999999)}",
                        zhiwu_id=10710, zhicheng_id=10603, xueli_id=10502,
                        status=1, password=password_hash("123456"))
            db.add(t)
            db.flush()
            teachers.append(t)
            group.append(t)
        teachers_of_school[sc.id] = group
    db.commit()

    # ---------------- 管理员
    pwd = password_hash("123456")
    admin = Admin(id=1, xingming="System Administrator", username="admin", password=pwd,
                  school_id=schools["Changxing Island Primary School"].id, status=1)
    db.add(admin)
    db.flush()

    # 教学副校长（校级数据权限）
    vice = teachers[0]
    vice.zhiwu_id = 10703
    a2 = Admin(id=2, xingming=vice.xingming, username="xiaozhang", password=pwd,
               teacher_id=vice.id, school_id=vice.danwei_id,
               zhiwu_id=10703, status=1)
    db.add(a2)

    # 普通教师（只能看自己教的班）
    t1 = teachers[1]
    a3 = Admin(xingming=t1.xingming, username="wanglaoshi", password=pwd,
               teacher_id=t1.id, school_id=t1.danwei_id,
               zhiwu_id=10710, subject_id=t1.subject_id, status=1)
    db.add(a3)
    db.commit()

    # ---------------- 权限规则与菜单
    rule_ids = []
    for pid_i, (ptitle, purl, ppaixu, children) in enumerate(MENU, start=1):
        p = AuthRule(id=pid_i * 100, pid=0, title=ptitle, url="", ismenu=1,
                     paixu=ppaixu, font="&#xe6a7;", status=1)
        db.add(p)
        db.flush()
        rule_ids.append(p.id)
        for ctitle, curl, cpaixu in children:
            c = AuthRule(pid=p.id, title=ctitle, url=curl, name=curl.strip("/"),
                         ismenu=1, paixu=cpaixu, font="&#xe6a7;", status=1)
            db.add(c)
            db.flush()
            rule_ids.append(c.id)
    db.commit()

    group = AuthGroup(id=1, title="Super administrator", rules=",".join(str(i) for i in rule_ids), status=1)
    db.add(group)
    db.commit()
    db.add(AuthGroupAccess(uid=1, group_id=1))
    db.add(AuthGroupAccess(uid=2, group_id=1))
    db.commit()

    # ---------------- 班主任与任课分工
    # 班主任与任课分工都只在本校教师中分配，避免教师跨校看到别校班级
    fen_gong: dict[tuple[int, int], int] = {}
    for i, b in enumerate(banjis):
        pool = teachers_of_school.get(b.school_id) or teachers
        lead = pool[i % len(pool)]
        db.add(BanZhuRen(teacher_id=lead.id, banji_id=b.id, bfdate=str_to_ts("2024-09-01")))
        for sub in exam_subjects:
            tid = pool[exam_subjects.index(sub) % len(pool)].id
            fen_gong[(b.id, sub.id)] = tid
            db.add(FenGong(teacher_id=tid, banji_id=b.id, subject_id=sub.id,
                           xueqi_id=xueqis[0].id, bfdate=str_to_ts("2024-09-01")))
    db.commit()

    # ---------------- 考试
    exams = []
    for title, cat, bf, ef, xq in [
        ("2024-2025 Semester 1 Final Exam", 10901, "2025-01-06", "2025-01-10", xueqis[0]),
        ("2024-2025 Semester 2 Midterm Exam", 10902, "2025-04-14", "2025-04-18", xueqis[1]),
        ("2024-2025 Semester 2 Final Exam", 10901, "2025-06-23", "2025-06-27", xueqis[1]),
    ]:
        k = Kaoshi(title=title, zuzhi_id=schools["Changxing Island Primary School"].id, xueqi_id=xq.id,
                   category_id=cat, user_id=1, bfdate=str_to_ts(bf), enddate=str_to_ts(ef),
                   luru=1, status=1)
        db.add(k)
        db.flush()
        exams.append(k)
    db.commit()

    # ---------------- 考试学科分数线
    for k in exams:
        for ruxuenian in sorted({b.ruxuenian for b in banjis}):
            for s in exam_subjects:
                db.add(KaoshiSet(kaoshi_id=k.id, ruxuenian=ruxuenian,
                                 nianjiname=kh_service._nianji_name(ruxuenian),
                                 subject_id=s.id, manfen=100, youxiu=85, lianghao=75, jige=60))
    db.commit()

    # ---------------- 考号 + 成绩
    for k in exams:
        kh_service.generate(k.id, [b.id for b in banjis], db)

    for k in exams:
        rows = db.scalars(select(Kaohao).where(Kaohao.kaoshi_id == k.id)).all()
        banji_bonus = {b.id: random.uniform(-6, 6) for b in banjis}
        for kh in rows:
            bj_bonus = banji_bonus.get(kh.banji_id, 0)
            # 学生个体能力，同一个人各场考试保持一定稳定性
            ability = random.gauss(0, 7)
            for s in exam_subjects:
                base = 78 + bj_bonus + ability + random.gauss(0, 9)
                score = max(0, min(100, round(base, 1)))
                # 约 2% 缺考
                if random.random() < 0.02:
                    score = None
                db.add(Chengji(kaohao_id=kh.id, subject_id=s.id, defen=score, user_id=1))
        db.commit()

    # ---------------- 课程 / 选课 / 考勤
    courses = []
    for b in banjis:
        for sub in exam_subjects:
            c = Course(
                title=f"{sub.title} · Class {b.paixu} ({b.ruxuenian})",
                xueqi_id=xueqis[0].id, banji_id=b.id, subject_id=sub.id,
                teacher_id=fen_gong.get((b.id, sub.id), 0), keshi=32, status=1,
            )
            db.add(c)
            db.flush()
            courses.append((c, b))
    db.commit()

    # 学生与班级的对应关系（按 id 取，避免逐条加载 ORM 对象）
    students_of_banji: dict[int, list[int]] = {}
    for sid, bid in db.execute(select(Student.id, Student.banji_id)).all():
        students_of_banji.setdefault(bid, []).append(sid)

    # 选课：本班学生全部选本班课程
    enrolled = 0
    for c, b in courses:
        for sid in students_of_banji.get(b.id, []):
            db.add(Enrollment(course_id=c.id, student_id=sid, xuanke_time=now_ts(), status=1))
            enrolled += 1
    db.commit()

    # 考勤：第一学期末 4 个教学日，约 90% 出勤
    att_days = [str_to_ts(d) for d in ("2024-12-30", "2024-12-31", "2025-01-02", "2025-01-03")]
    att_rows = 0
    for c, b in courses:
        for day in att_days:
            for sid in students_of_banji.get(b.id, []):
                r = random.random()
                if r < 0.90:
                    zt = 1
                elif r < 0.94:
                    zt = 2
                elif r < 0.97:
                    zt = 3
                else:
                    zt = 0
                db.add(Attendance(course_id=c.id, student_id=sid, riqi=day, zhuangtai=zt))
                att_rows += 1
        db.commit()

    # ---------------- 预跑统计，让系统开箱即可看数
    from app.services import tongji as tj_service  # noqa: PLC0415

    for k in exams:
        tj_service.tongji(k.id)
        tj_service.save_order(k.id)
        tj_service.biaozhunfen(k.id)

    print("Demo data generated:")
    print(f"  Schools {len(schools)}  Semesters {len(xueqis)}  Classes {len(banjis)}  Students {len(students)}")
    print(f"  Teachers {len(teachers)}  Exams {len(exams)}  Subjects {len(subjects)}")
    print(f"  Courses {len(courses)}  Enrolments {enrolled}  Attendance {att_rows}")
    print(f"  Three-level statistics, ranks and Z-scores computed for {len(exams)} exams")



if __name__ == "__main__":
    db = SessionLocal()
    if "--reset" in sys.argv:
        reset(db)
    seed(db)
    db.close()
