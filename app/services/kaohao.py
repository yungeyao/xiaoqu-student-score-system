"""考号生成服务。

考号把「某场考试」与「某个学生」绑定，并冗余班级/年级/排序，
这样统计时不必每次都 join 学生表。

考号编码规则（8 位）：学校(2) + 入学年后两位(2) + 班级序号(2) + 班内序号(2)
例如 01 21 03 15 -> 2021 级 3 班第 15 号，所属学校 id=1
"""
from __future__ import annotations

from sqlalchemy import select

from ..models import Banji, Kaohao, Student


def generate(kaoshi_id: int, banji_ids: list[int], db=None) -> dict:
    """为参加考试的班级生成考号。已存在的不会重复生成。

    返回 {"created": n, "skipped": n}
    """
    from ..core.database import SessionLocal

    own = db is None
    if own:
        db = SessionLocal()

    try:
        created = skipped = 0
        for banji_id in banji_ids:
            banji = db.get(Banji, banji_id)
            if banji is None:
                continue

            students = db.scalars(
                select(Student)
                .where(
                    Student.banji_id == banji_id,
                    Student.status == 1,
                    Student.kaoshi == 1,
                    Student.delete_time.is_(None),
                )
                .order_by(Student.id)
            ).all()

            exist = {
                k.student_id
                for k in db.scalars(
                    select(Kaohao).where(
                        Kaohao.kaoshi_id == kaoshi_id, Kaohao.banji_id == banji_id
                    )
                ).all()
            }

            idx = 0
            for stu in students:
                if stu.id in exist:
                    skipped += 1
                    continue
                idx += 1
                db.add(
                    Kaohao(
                        kaoshi_id=kaoshi_id,
                        school_id=banji.school_id,
                        ruxuenian=banji.ruxuenian or 0,
                        nianji=_nianji_name(banji.ruxuenian),
                        banji_id=banji_id,
                        paixu=idx,
                        student_id=stu.id,
                        kaohao=f"{banji.school_id:02d}{(banji.ruxuenian or 0) % 100:02d}"
                        f"{banji.paixu:02d}{idx:02d}",
                    )
                )
                created += 1
        db.commit()
        return {"created": created, "skipped": skipped}
    finally:
        if own:
            db.close()


GRADES = ["Grade 1", "Grade 2", "Grade 3", "Grade 4", "Grade 5", "Grade 6"]


def _nianji_name(ruxuenian) -> str:
    """由Cohort推算Grade名。这里按Primary school 6 年制, 以当年 9 月为分界粗略估算。"""
    if not ruxuenian:
        return ""
    from datetime import datetime

    now = datetime.now()
    year = now.year if now.month >= 9 else now.year - 1
    grade = year - int(ruxuenian) + 1
    if 1 <= grade <= len(GRADES):
        return GRADES[grade - 1]
    return f"{grade}Grade" if grade > 0 else ""


def delete_by_kaoshi(kaoshi_id: int, db) -> int:
    """清空某场Exam的Exam no. (连带Grade由调用方处理)。"""
    rows = db.scalars(select(Kaohao).where(Kaohao.kaoshi_id == kaoshi_id)).all()
    for r in rows:
        db.delete(r)
    db.commit()
    return len(rows)
