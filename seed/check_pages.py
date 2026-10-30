# -*- coding: utf-8 -*-
"""页面渲染冒烟：确认模板无异常、无未渲染占位。"""
import http.cookiejar
import re
import urllib.parse
import urllib.request

BASE = "http://127.0.0.1:8000"
jar = http.cookiejar.CookieJar()
op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))


def post(p, d):
    return op.open(urllib.request.Request(
        BASE + p, data=urllib.parse.urlencode(d).encode(),
        headers={"Content-Type": "application/x-www-form-urlencoded"})).read()


post("/login", {"username": "admin", "password": "123456", "category": "admin"})

PAGES = ["/", "/welcome", "/school", "/xueqi", "/banji", "/subject", "/teacher",
         "/student", "/admin_user", "/category", "/kaoshi", "/kaohao", "/luru",
         "/chengji", "/tongji/bj", "/tongji/nj", "/tongji/sch", "/kaoshi/set",
         "/password/edit", "/kaohao/print?kaoshi_id=1",
         "/course", "/enrollment", "/enrollment/batch", "/attendance", "/risk",
         "/report", "/report/banji?kaoshi_id=1&banji_id=1",
         "/report/student?kaoshi_id=1&student_id=1"]

bad = 0
for p in PAGES:
    html = op.open(BASE + p).read().decode("utf-8", "replace")
    issues = []
    if "Traceback" in html:
        issues.append("服务端异常")
    # layui 表格有自己的客户端模板语法 {{ d.field }}，需与 Jinja 残留区分开
    jinja = [m.group(0) for m in re.finditer(r"\{%|\{\{(?!\s*d\.)", html)]
    if jinja:
        issues.append(f"模板未渲染({len(jinja)} 处)")
    if len(html) < 400:
        issues.append(f"内容过短({len(html)})")
    if issues:
        bad += 1
    print(f"{'FAIL' if issues else 'OK  '} {p:<22} {len(html):>6} 字节  {'; '.join(issues)}")

print(f"\n共 {len(PAGES)} 个页面，异常 {bad} 个")
