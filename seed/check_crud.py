# -*- coding: utf-8 -*-
"""通用 CRUD 闭环: New -> 列表可见 -> Edit -> Delete"""
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
    ("school", {"title": "Test Primary School", "jiancheng": "TS", "biaoshi": "CS",
                "kaoshi": 1, "paixu": 50, "status": 1}),
    ("subject", {"title": "IT", "jiancheng": "IT", "lieming": "IT",
                 "category_id": 0, "kaoshi": 1, "paixu": 9, "status": 1}),
    ("xueqi", {"title": "2025-2026 Semester 1", "xuenian": "2025-2026",
               "category_id": 10801, "bfdate": 1751328000, "enddate": 1767196800,
               "beizhu": "", "status": 1}),
]:
    before = post(f"/api/{key}/list", {"page": 1, "limit": 200})["count"]
    r = post(f"/api/{key}/save", dict(payload, id=0))
    new_id = (r.get("data") or {}).get("id")
    ck(f"{key} create returns id", r.get("val") == 1 and bool(new_id), f"id={new_id}")

    after = post(f"/api/{key}/list", {"page": 1, "limit": 200})
    hit = [x for x in after["data"] if x.get("id") == new_id]
    ck(f"{key} appears in list", bool(hit), f"{before} -> {after['count']} rows")

    # 编辑
    first_k = [k for k in payload if k not in ("id", "status")][0]
    r2 = post(f"/api/{key}/save", dict(payload, id=new_id, **{first_k: "Renamed"}))
    ck(f"{key} update saved", r2.get("val") == 1, r2.get("msg", ""))
    hit2 = [x for x in post(f"/api/{key}/list", {"page": 1, "limit": 200})["data"]
            if x.get("id") == new_id]
    ck(f"{key} update applied", hit2 and str(hit2[0].get(first_k)) == "Renamed",
       f"{first_k}={hit2[0].get(first_k) if hit2 else None}")

    d = delete(f"/api/{key}/delete?id={new_id}")
    ck(f"{key} Delete", d.get("val") == 1, d.get("msg", ""))
    left = post(f"/api/{key}/list", {"page": 1, "limit": 200})["count"]
    ck(f"{key} back to original count", left == before, f"{left} == {before}")

print(f"\nFailures: {len(FAIL)}" + (":  " + ", ".join(FAIL) if FAIL else ""))
