"""数据权限服务。

返回当前用户可见的班级范围::

    {"check": False, "banji_id": []}   # check=False 表示不限制，能看到全部
    {"check": True,  "banji_id": [1,3]}  # 只能看这些班级

调用方把结果**注入模型查询条件**，而不是在控制器里硬过滤::

    auth = my_quanxian(db, user)
    q = select(Banji).where(...)
    if auth["check"]:
        q = q.where(Banji.id.in_(auth["banji_id"]))

这样同一个模型方法在管理员和教师手里自动产生不同的数据范围。
"""
from __future__ import annotations

from sqlalchemy import select

from ..core.config import Auth
from ..models import Admin, Banji, BanZhuRen, FenGong, Xueqi

# 拥有全校数据权限的职务：校长书记 / 教学副校长 / 教学主任
ZHIWU_SCHOOL_WIDE = (10701, 10703, 10705)


def my_quanxian(db, user: Admin, **switches) -> dict:
    """计算某管理员/教师的数据可见班级范围。

    switches 可按需关闭某个维度，默认全开：
        guanliyuan / zhiwu / banzhuren / renke
    """
    opt = {"guanliyuan": True, "zhiwu": True, "banzhuren": True, "renke": True}
    opt.update(switches)

    banji_ids: set[int] = set()
    unlimited = False

    # 1. 超级管理员：完全放开
    if opt["guanliyuan"] and user.id in Auth.administrator:
        return {"check": False, "banji_id": []}

    teacher_id = user.teacher_id

    # 2. 职务：校长/教学副校长/教学主任 -> 本单位全部班级
    if opt["zhiwu"] and user.zhiwu_id in ZHIWU_SCHOOL_WIDE:
        rows = db.scalars(
            select(Banji.id).where(Banji.school_id == user.school_id, Banji.delete_time.is_(None))
        ).all()
        banji_ids |= set(rows)
        unlimited = True

    if not teacher_id:
        return {"check": not unlimited, "banji_id": sorted(banji_ids)}

    # 3. 班主任：取最新一条仍由本人担任的记录
    if opt["banzhuren"]:
        banji_ids |= set(_banzhuren_banji(db, teacher_id))

    # 4. 任课分工：当前学期教的班级
    if opt["renke"]:
        banji_ids |= set(_renke_banji(db, teacher_id))

    return {"check": True, "banji_id": sorted(banji_ids)}


def _banzhuren_banji(db, teacher_id: int) -> list[int]:
    """班主任能看到自己带的班。

    判定现任班主任：任职日期 bfdate 已到，且该班最新一条班主任记录仍是本人。
    """
    now = _now()
    rows = db.execute(
        select(BanZhuRen.banji_id)
        .where(
            BanZhuRen.teacher_id == teacher_id,
            BanZhuRen.bfdate <= now,
            BanZhuRen.delete_time.is_(None),
        )
        .order_by(BanZhuRen.bfdate.desc())
    ).scalars().all()

    out: list[int] = []
    for banji_id in rows:
        if not banji_id:
            continue
        # 该班最新的班主任若仍是本人，才算现任
        latest = db.execute(
            select(BanZhuRen.teacher_id)
            .where(
                BanZhuRen.banji_id == banji_id,
                BanZhuRen.bfdate <= now,
                BanZhuRen.delete_time.is_(None),
            )
            .order_by(BanZhuRen.bfdate.desc())
            .limit(1)
        ).scalar_one_or_none()
        if latest == teacher_id:
            out.append(banji_id)
    return out


def _renke_banji(db, teacher_id: int) -> list[int]:
    """任课教师能看到本学期所教班级。"""
    xueqi_ids = [
        x.id
        for x in db.scalars(select(Xueqi).where(Xueqi.delete_time.is_(None))).all()
        if x.bfdate <= _now() <= x.enddate
    ]
    q = select(FenGong.banji_id).where(
        FenGong.teacher_id == teacher_id, FenGong.delete_time.is_(None)
    )
    if xueqi_ids:
        q = q.where(FenGong.xueqi_id.in_(xueqi_ids) | FenGong.xueqi_id.is_(None))
    rows = db.scalars(q).all()
    return [b for b in rows if b]


def apply_banji(q, column, auth: dict):
    """把 my_quanxian 的结果注入到按班级过滤的查询上。"""
    if not auth.get("check"):
        return q
    return q.where(column.in_(auth.get("banji_id") or [0]))


def data_scope(db, user) -> dict:
    """把班级级权限展开成三个统计层级都能用的白名单。

    返回::

        {"all": True}                      # 不限制
        {"all": False, "banji_ids": [...], "nj_keys": [(school_id, ruxuenian)],
         "ruxuenians": [...]}

    三级统计表作用域各不相同（班级表按 banji_id、年级表按 school_id+ruxuenian、
    全校表按 ruxuenian），这里一次算好三种键，避免各接口重复推导。
    """
    if user is None:
        return {"all": False, "banji_ids": [], "nj_keys": [], "ruxuenians": []}

    auth = my_quanxian(db, user)
    if not auth.get("check"):
        return {"all": True, "banji_ids": [], "nj_keys": [], "ruxuenians": []}

    ids = auth.get("banji_id") or []
    bjs = (
        db.execute(
            select(Banji.id, Banji.school_id, Banji.ruxuenian).where(Banji.id.in_(ids))
        ).all()
        if ids
        else []
    )

    nj_keys = sorted({(b[1], b[2]) for b in bjs if b[1] and b[2]})
    ruxuenians = sorted({b[2] for b in bjs if b[2]})
    return {
        "all": False,
        "banji_ids": sorted(ids),
        "nj_keys": nj_keys,
        "ruxuenians": ruxuenians,
    }


def _now() -> int:
    from ..models.base import now_ts

    return now_ts()


# ------------------------------------------------------------------ 功能权限


def user_rule_ids(db, user: Admin) -> list[int]:
    """汇总用户所有角色的规则 id。"""
    from ..models import AuthGroup, AuthGroupAccess

    group_ids = db.scalars(
        select(AuthGroupAccess.group_id).where(AuthGroupAccess.uid == user.id)
    ).all()
    if not group_ids:
        return []
    ids: set[int] = set()
    for g in db.scalars(select(AuthGroup).where(AuthGroup.id.in_(group_ids))).all():
        if g.rules:
            ids |= {int(x) for x in str(g.rules).split(",") if x.strip().isdigit()}
    return sorted(ids)


def check_url(db, user: Admin, url: str) -> bool:
    """URL 级权限校验。

    ``url`` 形如 ``kaoshi/index/index``。未登记为规则的 URL 视为开放，
    即只对明确配置过的入口做限制，避免新增页面时误拦。
    """
    if not Auth.auth_on:
        return True
    if user.id in Auth.administrator:
        return True

    # 通用方法豁免
    tail = url.rsplit("/", 1)[-1] if "/" in url else url
    if tail in Auth.public_actions:
        return True

    from ..models import AuthRule

    rule = db.scalars(select(AuthRule).where(AuthRule.name == url)).first()
    if rule is None:
        return True
    return rule.id in user_rule_ids(db, user)
