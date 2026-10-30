# -*- coding: utf-8 -*-
"""通用 CRUD 闭环：新增 -> 列表可见 -> 编辑 -> 删除"""
import http.cookiejar
import json
import urllib.parse
import urllib.request

BASE = "http://127.0.0.1:8000"
jar = http.cookiejar.CookieJar()
op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))


def post(p, d):
    return json.loads(op.open(urllib.request.Request(
        BASE + p, data=urllib.parse.urlencode(d).encode(),
        headers={"Content-Type": "application/x-www-form-urlencoded"})).read().decode())


def delete(p):
    return json.loads(op.open(urllib.request.Request(BASE + p, method="DELETE")).read().decode())


op.open(urllib.request.Request(
    BASE + "/login",
    data=urllib.parse.urlencode(
        {"username": "admin", "password": "123456", "category": "admin"}).encode(),
    headers={"Content-Type": "application/x-www-form-urlencoded"})).read()

FAIL = []


def ck(name, cond, detail=""):
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}  {detail}")
    if not cond:
        FAIL.append(name)


for key, payload in [
    ("school", {"title": "测试小学", "jiancheng": "测试", "biaoshi": "CS",
                "kaoshi": 1, "paixu": 50, "status": 1}),
    ("subject", {"title": "信息技术", "jiancheng": "信息", "lieming": "信息技术",
                 "category_id": 0, "kaoshi": 1, "paixu": 9, "status": 1}),
    ("xueqi", {"title": "2025-2026第一学期", "xuenian": "2025-2026",
               "category_id": 10801, "bfdate": 1751328000, "enddate": 1767196800,
               "beizhu": "", "status": 1}),
]:
    before = post(f"/api/{key}/list", {"page": 1, "limit": 200})["count"]
    r = post(f"/api/{key}/save", dict(payload, id=0))
    new_id = (r.get("data") or {}).get("id")
    ck(f"{key} 新增返回自增 id", r.get("val") == 1 and bool(new_id), f"id={new_id}")

    after = post(f"/api/{key}/list", {"page": 1, "limit": 200})
    hit = [x for x in after["data"] if x.get("id") == new_id]
    ck(f"{key} 列表可见", bool(hit), f"{before} -> {after['count']} 条")

    # 编辑
    first_k = [k for k in payload if k not in ("id", "status")][0]
    r2 = post(f"/api/{key}/save", dict(payload, id=new_id, **{first_k: "已改名"}))
    ck(f"{key} 编辑保存", r2.get("val") == 1, r2.get("msg", ""))
    hit2 = [x for x in post(f"/api/{key}/list", {"page": 1, "limit": 200})["data"]
            if x.get("id") == new_id]
    ck(f"{key} 编辑生效", hit2 and str(hit2[0].get(first_k)) == "已改名",
       f"{first_k}={hit2[0].get(first_k) if hit2 else None}")

    d = delete(f"/api/{key}/delete?id={new_id}")
    ck(f"{key} 删除", d.get("val") == 1, d.get("msg", ""))
    left = post(f"/api/{key}/list", {"page": 1, "limit": 200})["count"]
    ck(f"{key} 删除后回到原数量", left == before, f"{left} == {before}")

print(f"\n失败 {len(FAIL)} 项" + ("： " + ", ".join(FAIL) if FAIL else ""))
