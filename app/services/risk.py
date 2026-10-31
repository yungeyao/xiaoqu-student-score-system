"""学业预警：用可解释的规则给每个学生算风险分。

预警不引入黑盒模型：每条规则都对应一个教师能复核的事实（班级均分差距、
不及格科目数、缺考数、出勤率），命中的规则同时作为「原因」返回，
方便班主任在页面上直接看到该学生为什么被标红。

风险分与等级：

===========  ==========================================
分数          等级
===========  ==========================================
0             正常
1 - 2         关注
3 - 4         中风险
>= 5          高风险
===========  ==========================================
"""
from __future__ import annotations

from collections import defaultdict
from typing import Optional

from sqlalchemy import select

from ..models import ATTENDANCE_PRESENT, Attendance, Banji, Chengji, Kaohao, KaoshiSet, Student

LEVELS = ["High", "Medium", "Watch", "Normal"]


def _level_of(score: int) -> str:
    if score >= 5:
        return "High"
    if score >= 3:
        return "Medium"
    if score >= 1:
        return "Watch"
    return "Normal"


def _lines(db, kaoshi_id: int) -> dict[tuple[int, int], float]:
    """{ (Cohort, Subject): Pass line}"""
    rows = db.execute(
        select(KaoshiSet.ruxuenian, KaoshiSet.subject_id, KaoshiSet.jige).where(
            KaoshiSet.kaoshi_id == kaoshi_id, KaoshiSet.delete_time.is_(None)
        )
    ).all()
    return {(r[0], r[1]): float(r[2] or 60) for r in rows}


def _attendance_rate(db, student_ids: list[int]) -> dict[int, Optional[float]]:
    """每个Student的Attendance (出勤/Late/Leave都算到课), 没有Attendance记录返回 None。"""
    if not student_ids:
        return {}
    total: dict[int, int] = defaultdict(int)
    present: dict[int, int] = defaultdict(int)
    rows = db.execute(
        select(Attendance.student_id, Attendance.zhuangtai).where(
            Attendance.student_id.in_(student_ids), Attendance.delete_time.is_(None)
        )
    ).all()
    for sid, zt in rows:
        total[sid] += 1
        if zt in ATTENDANCE_PRESENT:
            present[sid] += 1
    return {
        sid: round(present[sid] / total[sid] * 100, 1) if total[sid] else None
        for sid in student_ids
    }


def evaluate(
    db,
    kaoshi_id: int,
    banji_ids: Optional[list[int]] = None,
    include_attendance: bool = True,
) -> list[dict]:
    """返回范围内每个Student的预警明细, 按Risk score降序, Average升序。"""
    stmt = select(Student).where(Student.delete_time.is_(None), Student.status == 1)
    if banji_ids is not None:
        stmt = stmt.where(Student.banji_id.in_(banji_ids or [0]))
    students = db.scalars(stmt).all()
    if not students:
        return []

    by_id = {s.id: s for s in students}
    student_ids = list(by_id)

    # 考号 -> 学生
    kh_rows = db.execute(
        select(Kaohao.id, Kaohao.student_id).where(Kaohao.kaoshi_id == kaoshi_id)
    ).all()
    kh_to_student = {kh_id: sid for kh_id, sid in kh_rows}

    # 成绩
    scores: dict[int, dict[int, Optional[float]]] = defaultdict(dict)  # student -> subject -> 分数
    if kh_to_student:
        rows = db.execute(
            select(Chengji.kaohao_id, Chengji.subject_id, Chengji.defen).where(
                Chengji.kaohao_id.in_(list(kh_to_student))
            )
        ).all()
        for kh_id, subject_id, defen in rows:
            sid = kh_to_student.get(kh_id)
            if sid in by_id:
                scores[sid][subject_id] = None if defen is None else float(defen)

    lines = _lines(db, kaoshi_id)
    # 入学年在班级上，先取 (班级 -> 入学年)，用于匹配该年级的分数线
    banji_ruxuenian = {
        bid: rn for bid, rn in db.execute(select(Banji.id, Banji.ruxuenian)).all()
    }
    att = _attendance_rate(db, student_ids) if include_attendance else {}

    # 班级总分均值：只统计各科都参加了的学生，避免缺考把均值拉低
    class_totals: dict[int, list[float]] = defaultdict(list)
    totals: dict[int, Optional[float]] = {}
    for sid, by_subject in scores.items():
        bj = by_id[sid].banji_id
        if any(v is None for v in by_subject.values()):
            totals[sid] = None
            continue
        total = round(sum(by_subject.values()), 1)
        totals[sid] = total
        class_totals[bj].append(total)
    class_avg = {
        bj: round(sum(v) / len(v), 2) for bj, v in class_totals.items() if v
    }

    out: list[dict] = []
    for sid, stu in by_id.items():
        by_subject = scores.get(sid, {})
        reasons: list[str] = []
        score = 0

        # 规则 1：不及格科目数
        fail = 0
        for subject_id, defen in by_subject.items():
            if defen is None:
                continue
            line = lines.get((banji_ruxuenian.get(stu.banji_id), subject_id), 60.0)
            if defen < line:
                fail += 1
        if fail >= 3:
            score += 3
            reasons.append(f"{fail} subjects failed")
        elif fail == 2:
            score += 2
            reasons.append("2 subjects failed")
        elif fail == 1:
            score += 1
            reasons.append("1 subject failed")

        # 规则 2：缺考
        absent = sum(1 for v in by_subject.values() if v is None)
        if absent >= 2:
            score += 2
            reasons.append(f"{absent} subjects missed")
        elif absent == 1:
            score += 1
            reasons.append("1 subject missed")

        # 规则 3：总分与班级均分的差距
        total = totals.get(sid)
        cavg = class_avg.get(stu.banji_id)
        gap = None
        if total is not None and cavg:
            gap = round(total - cavg, 1)
            if gap <= -40:
                score += 2
                reasons.append(f"Total {abs(gap)} below class average")
            elif gap <= -20:
                score += 1
                reasons.append(f"Total {abs(gap)} below class average")

        # 规则 4：到课率
        rate = att.get(sid)
        if rate is not None:
            if rate < 80:
                score += 2
                reasons.append(f"Attendance only {rate}%")
            elif rate < 90:
                score += 1
                reasons.append(f"Attendance {rate}%")

        out.append(
            {
                "student_id": sid,
                "xingming": stu.xingming,
                "banji_id": stu.banji_id,
                "total": total,
                "avg": round(total / len(by_subject), 2) if total is not None and by_subject else None,
                "fail_count": fail,
                "absent_count": absent,
                "attendance_rate": rate,
                "class_avg": cavg,
                "gap": gap,
                "risk_score": score,
                "risk_level": _level_of(score),
                "reasons": reasons,
            }
        )

    out.sort(key=lambda r: (-r["risk_score"], r["avg"] is None, r["avg"] or 0))
    return out


def summary(rows: list[dict]) -> dict:
    """按Level统计 students数, 供图表与报表复用。"""
    counts = {lv: 0 for lv in LEVELS}
    for r in rows:
        counts[r["risk_level"]] = counts.get(r["risk_level"], 0) + 1
    at_risk = counts["High"] + counts["Medium"]
    total = len(rows)
    return {
        "total": total,
        "counts": counts,
        "at_risk": at_risk,
        "at_risk_rate": round(at_risk / total * 100, 1) if total else 0.0,
    }
