"""数据库层统计服务。

三级统计**各自独立从 chengji 表全量重算**，不是层层汇总，区别只在作用域：

* tongji_bj  按 banji_id
* tongji_nj  按 school_id + ruxuenian
* tongji_sch 按 ruxuenian（全区）

各算各的虽然多读几次库，但任一级别的口径变化或补录都不会污染其他级别。
总分作为一个伪学科（subject_id = 0）参与统计：
某学生只要缺考任意一科，其总分即记为缺考，避免拉低平均分。
"""
from __future__ import annotations

from collections import defaultdict
from typing import Optional

from sqlalchemy import select

from ..core.database import SessionLocal
from ..models import Chengji, Kaohao, KaoshiSet, TongjiBj, TongjiNj, TongjiSch
from . import stats

# 总分伪学科 id（真实学科 id 均 >= 1）
TOTAL_SUBJECT_ID = 0


class _Ctx:
    """一次统计过程中的共享数据。"""

    def __init__(self, db, kaoshi_id: int):
        self.db = db
        self.kaoshi_id = kaoshi_id

        # 该场考试的全部成绩行 (kaohao_id, school_id, banji_id, ruxuenian, subject_id, defen)
        self.rows = db.execute(
            select(
                Kaohao.id,
                Kaohao.school_id,
                Kaohao.banji_id,
                Kaohao.ruxuenian,
                Chengji.subject_id,
                Chengji.defen,
            )
            .join(Chengji, Chengji.kaohao_id == Kaohao.id)
            .where(Kaohao.kaoshi_id == kaoshi_id, Kaohao.delete_time.is_(None))
        ).all()

        # 考号 -> (school_id, banji_id, ruxuenian)
        self.dim: dict[int, tuple[int, int, int]] = {}
        for cid, school_id, banji_id, ruxuenian, _sid, _defen in self.rows:
            self.dim[cid] = (school_id, banji_id, ruxuenian)

        # {(ruxuenian, subject_id): {manfen, youxiu, lianghao, jige}}
        self.ks_set: dict[tuple[int, int], dict] = {}
        for s in db.scalars(select(KaoshiSet).where(KaoshiSet.kaoshi_id == kaoshi_id)):
            self.ks_set[(s.ruxuenian, s.subject_id)] = {
                "manfen": s.manfen or 100,
                "youxiu": s.youxiu,
                "lianghao": s.lianghao,
                "jige": s.jige,
            }

        # 每个考号的总分
        self.totals = self._calc_totals()

    # ---- 分数线 ----

    def lines(self, ruxuenian: int, subject_id: int):
        """返回 (manfen, youxiu, lianghao, jige)。"""
        if subject_id == TOTAL_SUBJECT_ID:
            return self._total_lines(ruxuenian)
        cfg = self.ks_set.get((ruxuenian, subject_id))
        if not cfg:
            return 100.0, None, None, None
        return cfg["manfen"], cfg["youxiu"], cfg["lianghao"], cfg["jige"]

    def _total_lines(self, ruxuenian: int):
        """总分的满分与分数线 = 该年级各科之和。"""
        manfen = youxiu = lianghao = jige = 0
        found = False
        for (rn, _sid), cfg in self.ks_set.items():
            if rn != ruxuenian:
                continue
            found = True
            manfen += cfg["manfen"] or 0
            youxiu += cfg["youxiu"] or 0
            lianghao += cfg["lianghao"] or 0
            jige += cfg["jige"] or 0
        if not found:
            return 100.0, None, None, None
        return float(manfen), float(youxiu), float(lianghao), float(jige)

    # ---- 总分 ----

    def _calc_totals(self) -> dict[int, Optional[float]]:
        per: dict[int, list[Optional[float]]] = defaultdict(list)
        for cid, _sid, _bid, _rn, _sub, defen in self.rows:
            per[cid].append(None if defen is None else float(defen))

        expected: dict[int, int] = defaultdict(int)
        for rn, _sid in self.ks_set:
            expected[rn] += 1

        out: dict[int, Optional[float]] = {}
        for cid, scores in per.items():
            rn = self.dim[cid][2]
            exp = expected.get(rn, len(scores))
            # 有缺考科目，或科目数不足 -> 总分记为缺考
            if any(s is None for s in scores) or len(scores) < exp:
                out[cid] = None
            else:
                out[cid] = round(sum(scores), 1)  # type: ignore[arg-type]
        return out

    def totals_of(self, kaohao_ids) -> list[Optional[float]]:
        return [self.totals.get(cid) for cid in kaohao_ids]


# ------------------------------------------------------------------ 入口


def tongji(kaoshi_id: int) -> dict:
    """重算三级统计, 返回各级写入的行数。"""
    with SessionLocal() as db:
        ctx = _Ctx(db, kaoshi_id)
        bj = _tj_banji(db, ctx)
        nj = _tj_nianji(db, ctx)
        sch = _tj_school(db, ctx)
        db.commit()
        return {"bj": bj, "nj": nj, "sch": sch}


def _calc(ctx: _Ctx, scores, ruxuenian: int, subject_id: int) -> dict:
    manfen, youxiu, lianghao, jige = ctx.lines(ruxuenian, subject_id)
    return stats.tongji_subject(scores, manfen, youxiu, lianghao, jige)


def _tj_banji(db, ctx: _Ctx) -> int:
    db.query(TongjiBj).filter(TongjiBj.kaoshi_id == ctx.kaoshi_id).delete()

    scores: dict[tuple[int, int], list[Optional[float]]] = defaultdict(list)
    ids: dict[tuple[int, int], list[int]] = defaultdict(list)
    rn_of: dict[int, int] = {}

    for cid, _school, banji_id, ruxuenian, subject_id, defen in ctx.rows:
        key = (banji_id, subject_id)
        scores[key].append(None if defen is None else float(defen))
        ids[key].append(cid)
        rn_of[banji_id] = ruxuenian

    # 追加总分：按班级汇总每个学生的总分
    for banji_id, ruxuenian in rn_of.items():
        scores[(banji_id, TOTAL_SUBJECT_ID)] = ctx.totals_of(
            [cid for cid, d in ctx.dim.items() if d[1] == banji_id]
        )

    cnt = 0
    for (banji_id, subject_id), vals in scores.items():
        ruxuenian = rn_of.get(banji_id, 0)
        db.add(
            TongjiBj(
                kaoshi_id=ctx.kaoshi_id,
                banji_id=banji_id,
                subject_id=subject_id,
                **_calc(ctx, vals, ruxuenian, subject_id),
            )
        )
        cnt += 1
    db.flush()
    return cnt


def _tj_nianji(db, ctx: _Ctx) -> int:
    db.query(TongjiNj).filter(TongjiNj.kaoshi_id == ctx.kaoshi_id).delete()

    scores: dict[tuple[int, int, int], list[Optional[float]]] = defaultdict(list)
    ids: dict[tuple[int, int, int], list[int]] = defaultdict(list)

    for cid, school_id, _banji, ruxuenian, subject_id, defen in ctx.rows:
        key = (school_id, ruxuenian, subject_id)
        scores[key].append(None if defen is None else float(defen))
        ids[key].append(cid)

    groups = {(k[0], k[1]) for k in scores}
    for school_id, ruxuenian in groups:
        key = (school_id, ruxuenian, TOTAL_SUBJECT_ID)
        scores[key] = ctx.totals_of(
            [cid for cid, d in ctx.dim.items() if d[0] == school_id and d[2] == ruxuenian]
        )

    cnt = 0
    for (school_id, ruxuenian, subject_id), vals in scores.items():
        db.add(
            TongjiNj(
                kaoshi_id=ctx.kaoshi_id,
                school_id=school_id,
                ruxuenian=ruxuenian,
                subject_id=subject_id,
                **_calc(ctx, vals, ruxuenian, subject_id),
            )
        )
        cnt += 1
    db.flush()
    return cnt


def _tj_school(db, ctx: _Ctx) -> int:
    db.query(TongjiSch).filter(TongjiSch.kaoshi_id == ctx.kaoshi_id).delete()

    scores: dict[tuple[int, int], list[Optional[float]]] = defaultdict(list)

    for cid, _school, _banji, ruxuenian, subject_id, defen in ctx.rows:
        scores[(ruxuenian, subject_id)].append(None if defen is None else float(defen))

    for ruxuenian in {k[0] for k in scores}:
        scores[(ruxuenian, TOTAL_SUBJECT_ID)] = ctx.totals_of(
            [cid for cid, d in ctx.dim.items() if d[2] == ruxuenian]
        )

    cnt = 0
    for (ruxuenian, subject_id), vals in scores.items():
        db.add(
            TongjiSch(
                kaoshi_id=ctx.kaoshi_id,
                ruxuenian=ruxuenian,
                subject_id=subject_id,
                **_calc(ctx, vals, ruxuenian, subject_id),
            )
        )
        cnt += 1
    db.flush()
    return cnt


# ------------------------------------------------------------------ 排名与标准分


def save_order(kaoshi_id: int) -> int:
    """计算班级/学校/全区三个维度的排名与位置百分位。"""
    with SessionLocal() as db:
        rows = db.execute(
            select(Chengji.id, Chengji.kaohao_id, Chengji.subject_id, Chengji.defen,
                   Kaohao.banji_id, Kaohao.school_id, Kaohao.ruxuenian)
            .join(Kaohao, Kaohao.id == Chengji.kaohao_id)
            .where(Kaohao.kaoshi_id == kaoshi_id, Kaohao.delete_time.is_(None))
        ).all()

        # 班级维度
        by_banji: dict[tuple[int, int], list[tuple[int, Optional[float]]]] = defaultdict(list)
        # 学校维度
        by_school: dict[tuple[int, int], list[tuple[int, Optional[float]]]] = defaultdict(list)
        # 全区维度
        by_area: dict[int, list[tuple[int, Optional[float]]]] = defaultdict(list)

        for cj_id, _kh, subject_id, defen, banji_id, school_id, ruxuenian in rows:
            val = None if defen is None else float(defen)
            by_banji[(banji_id, subject_id)].append((cj_id, val))
            by_school[(school_id, ruxuenian, subject_id)].append((cj_id, val))
            by_area[(ruxuenian, subject_id)].append((cj_id, val))

        updated = 0
        cj_map = {r[0]: r for r in rows}
        for cj_id in cj_map:
            obj = db.get(Chengji, cj_id)
            if not obj:
                continue
            obj.bpaixu, obj.bweizhi = None, None
            obj.xpaixu, obj.xweizhi = None, None
            obj.qpaixu, obj.qweizhi = None, None
            updated += 1

        for group, pairs in by_banji.items():
            for cj_id, (rank, weizhi) in stats.rank_values(pairs).items():
                obj = db.get(Chengji, cj_id)
                if obj:
                    obj.bpaixu, obj.bweizhi = rank, weizhi
        for group, pairs in by_school.items():
            for cj_id, (rank, weizhi) in stats.rank_values(pairs).items():
                obj = db.get(Chengji, cj_id)
                if obj:
                    obj.xpaixu, obj.xweizhi = rank, weizhi
        for group, pairs in by_area.items():
            for cj_id, (rank, weizhi) in stats.rank_values(pairs).items():
                obj = db.get(Chengji, cj_id)
                if obj:
                    obj.qpaixu, obj.qweizhi = rank, weizhi

        db.commit()
        return updated


def biaozhunfen(kaoshi_id: int) -> int:
    """标准分 Z = (得分 − 全区平均分) / 全区标准差。依赖 tongji_sch 已算完。"""
    with SessionLocal() as db:
        base = {
            (s.ruxuenian, s.subject_id): (s.avg, s.biaozhuncha)
            for s in db.scalars(select(TongjiSch).where(TongjiSch.kaoshi_id == kaoshi_id))
        }
        if not base:
            return 0

        rows = db.execute(
            select(Chengji.id, Chengji.defen, Kaohao.ruxuenian, Chengji.subject_id)
            .join(Kaohao, Kaohao.id == Chengji.kaohao_id)
            .where(Kaohao.kaoshi_id == kaoshi_id, Kaohao.delete_time.is_(None))
        ).all()

        cnt = 0
        for cj_id, defen, ruxuenian, subject_id in rows:
            avg, std = base.get((ruxuenian, subject_id), (None, None))
            obj = db.get(Chengji, cj_id)
            if not obj:
                continue
            obj.biaozhunfen = stats.standard_score(
                None if defen is None else float(defen),
                None if avg is None else float(avg),
                None if std is None else float(std),
            )
            cnt += 1
        db.commit()
        return cnt
