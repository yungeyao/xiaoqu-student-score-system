"""侧边栏菜单。读取 auth_rule 中 ismenu=1 的规则, 按当前用户权限过滤。"""
from __future__ import annotations

from html import unescape
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.config import Auth
from ..models import AuthRule
from .permission import user_rule_ids


def build_menu(db: Session, user) -> list[dict]:
    """返回两层菜单树。超级管理员看到All。"""
    rules = db.scalars(
        select(AuthRule)
        .where(AuthRule.ismenu == 1, AuthRule.status == 1, AuthRule.delete_time.is_(None))
        .order_by(AuthRule.paixu, AuthRule.id)
    ).all()

    if getattr(user, "id", None) in Auth.administrator:
        allowed = None  # None 表示不过滤
    else:
        allowed = set(user_rule_ids(db, user))

    items = []
    for r in rules:
        if allowed is not None and r.id not in allowed:
            continue
        items.append(
            {
                "id": r.id,
                "pid": r.pid,
                "title": r.title,
                "url": r.url or "",
                # 菜单图标在库里以 HTML 实体（如 &#xe6a7;）保存，这里解码成真实字符，
                # 否则模板自动转义后会原样显示成 "&#xe6a7;" 文本。
                "font": unescape(r.font or ""),
            }
        )

    tree = []
    by_id = {i["id"]: i for i in items}
    for i in items:
        if i["pid"] and i["pid"] in by_id:
            parent = by_id[i["pid"]]
            parent.setdefault("children", []).append(i)
        else:
            tree.append(i)
    # 过滤掉没有子项的父菜单
    return [t for t in tree if t.get("children") or t["url"]]
