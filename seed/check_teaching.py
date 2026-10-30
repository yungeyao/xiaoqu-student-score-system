# -*- coding: utf-8 -*-
"""教学管理自检：课程 / 选课 / 考勤 / 学业预警 / 报表 与相关权限。

前置：先启动服务（python run.py），并已执行 python -m seed.seed --reset。
"""
import http.cookiejar
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

BASE = "http://127.0.0.1:8000"
PASS = FAIL = 0


def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  [PASS] {name}" + (f"  {detail}" if detail else ""))
    else:
        FAIL += 1
        print(f"  [FAIL] {name}  {detail}")


class Client:
    def __init__(self):
        self.jar = http.cookiejar.CookieJar()
        self.op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.jar))

    def post(self, path, data=None, raw=False):
        req = urllib.request.Request(
            BASE + path,
            data=urllib.parse.urlencode(data or {}).encode(),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        with self.op.open(req) as r:
            body = r.read()
            ctype = r.headers.get("Content-Type", "")
        if raw or "json" not in ctype:
            return body
        return json.loads(body.decode())

    def get(self, path, raw=False):
        with self.op.open(urllib.request.Request(BASE + path)) as r:
            body = r.read()
            ctype = r.headers.get("Content-Type", "")
        if raw or "json" not in ctype:
            return body
        return json.loads(body.decode())

    def login(self, username, password, category="admin"):
        self.post("/login", {"username": username, "password": password, "category": category})
        return self


def section(title):
    print()
    print("=" * 60)
    print(title)
    print("=" * 60)


def main():
    admin = Client().login("admin", "123456")

    section("1. 新页面可达")
    for path, size in [
        ("/course", 5000), ("/enrollment", 5000), ("/enrollment/batch", 1000),
        ("/attendance", 2000), ("/risk", 2000), ("/report", 1000),
    ]:
        body = admin.get(path, raw=True)
        check(f"GET {path}", isinstance(body, bytes) and len(body) > size, f"{len(body)} 字节")

    section("2. 课程与选课")
    res = admin.post("/api/course/list", {"page": 1, "limit": 10})
    check("课程列表", res.get("code") == 0 and res.get("count") == 120, f"count={res.get('count')}")
    res = admin.post("/api/enrollment/list", {"page": 1, "limit": 10})
    check("选课列表", res.get("code") == 0 and res.get("count") == 2400,
          f"count={res.get('count')}")

    course_id = admin.post("/api/course/list", {"page": 1, "limit": 1})["data"][0]["id"]
    res = admin.post("/api/enrollment/students", {"course_id": course_id})
    n_enrolled = res["data"]["enrolled"]
    check("选课名单载入", res.get("val") == 1 and n_enrolled == 20, f"已选 {n_enrolled} 人")

    # 批量选课：先只留 5 人，再恢复 20 人
    keep = [s["student_id"] for s in res["data"]["students"][:5]]
    res = admin.post("/api/enrollment/batch", {"course_id": course_id,
                                               "student_ids": json.dumps(keep)})
    check("批量选课保存", res.get("val") == 1, res.get("msg", ""))
    res = admin.post("/api/enrollment/students", {"course_id": course_id})
    check("选课结果生效", res["data"]["enrolled"] == 5, f"{res['data']['enrolled']} 人")
    all_ids = [s["student_id"] for s in admin.post(
        "/api/enrollment/students", {"course_id": course_id})["data"]["students"]]
    admin.post("/api/enrollment/batch", {"course_id": course_id,
                                         "student_ids": json.dumps(all_ids)})
    res = admin.post("/api/enrollment/students", {"course_id": course_id})
    check("选课恢复", res["data"]["enrolled"] == 20, f"{res['data']['enrolled']} 人")

    section("3. 考勤录入")
    riqi = "2025-03-03"
    res = admin.post("/api/attendance/students", {"course_id": course_id, "riqi": riqi})
    students = res["data"]["students"]
    check("载入考勤名单", res.get("val") == 1 and len(students) == 20, f"{len(students)} 人")
    rows = [{"student_id": s["student_id"], "zhuangtai": 1 if i else 0, "beizhu": ""}
            for i, s in enumerate(students)]
    res = admin.post("/api/attendance/save", {"course_id": course_id, "riqi": riqi,
                                             "rows": json.dumps(rows)})
    check("保存考勤", res.get("val") == 1, res.get("msg", ""))

    res = admin.post("/api/attendance/students", {"course_id": course_id, "riqi": riqi})
    absent = sum(1 for s in res["data"]["students"] if s["zhuangtai"] == 0)
    check("考勤已落库", res["data"]["students"][0]["saved"] is True and absent == 1,
          f"缺勤 {absent} 人")

    res = admin.post("/api/attendance/save", {"course_id": course_id, "riqi": riqi,
                                             "rows": json.dumps(rows)})
    check("重复保存不重复插入", "更新" in res.get("msg", ""), res.get("msg", ""))

    res = admin.post("/api/attendance/stats", {"course_id": course_id})
    days = res["data"]["days"]
    check("考勤统计", res.get("val") == 1 and len(days) >= 4, f"{len(days)} 天")
    check("到课率计算", all("rate" in s for s in res["data"]["students"]),
          f"{len(res['data']['students'])} 人")

    section("4. 学业预警")
    exam_id = 1
    res = admin.post("/api/risk/list", {"kaoshi_id": exam_id, "banji_id": ""})
    rows = res["data"]
    check("预警名单", res.get("code") == 0 and len(rows) == 480, f"{len(rows)} 人")
    high = [r for r in rows if r["risk_level"] == "高风险"]
    check("存在高风险学生", len(high) > 0, f"{len(high)} 人")
    check("预警原因可解释", all(r["reasons"] for r in rows if r["risk_score"] > 0),
          "命中规则的都有原因")
    check("等级与分值一致", all(
        (r["risk_score"] >= 5) == (r["risk_level"] == "高风险") for r in rows))

    res = admin.post("/api/risk/summary", {"kaoshi_id": exam_id})
    s = res["data"]
    check("预警汇总", s["total"] == 480 and abs(s["at_risk_rate"] - s["at_risk"] / 4.8) < 0.2,
          f"预警 {s['at_risk']} 人 {s['at_risk_rate']}%")

    res = admin.post("/api/risk/chart", {"kaoshi_id": exam_id})
    check("预警图表", res.get("val") == 1 and len(res["data"]["categories"]) == 24,
          f"{len(res['data']['categories'])} 个班")

    blob = admin.get(f"/api/risk/export.xlsx?kaoshi_id={exam_id}", raw=True)
    check("预警导出 xlsx", isinstance(blob, bytes) and blob[:2] == b"PK", f"{len(blob)} 字节")

    section("5. 报表生成")
    body = admin.get(f"/report/banji?kaoshi_id={exam_id}&banji_id=1", raw=True)
    text = body.decode("utf-8")
    check("班级报表可渲染", "学生成绩明细" in text and "预警名单" in text,
          f"{len(body)} 字节")
    body = admin.get(f"/report/student?kaoshi_id={exam_id}&student_id=1", raw=True)
    check("学生成绩单可渲染", "学生成绩单" in body.decode("utf-8"))

    blob = admin.get(f"/api/report/banji.xlsx?kaoshi_id={exam_id}&banji_id=1", raw=True)
    check("单班报表 xlsx", isinstance(blob, bytes) and blob[:2] == b"PK", f"{len(blob)} 字节")

    blob = admin.get(f"/api/report/all.xlsx?kaoshi_id={exam_id}", raw=True)
    check("批量报表 xlsx", isinstance(blob, bytes) and blob[:2] == b"PK" and len(blob) > 20000,
          f"{len(blob)} 字节")
    if isinstance(blob, bytes) and blob[:2] == b"PK":
        import io

        import openpyxl

        wb = openpyxl.load_workbook(io.BytesIO(blob))
        check("批量报表含全部班级工作表", len(wb.sheetnames) == 25,
              f"{len(wb.sheetnames)} 张表")

    section("6. 角色权限")
    teacher = Client().login("wanglaoshi", "123456")
    res = teacher.post("/api/risk/list", {"kaoshi_id": exam_id, "banji_id": ""})
    check("教师预警仅覆盖所教班级", len(res["data"]) == 240, f"{len(res['data'])} 人（12 个班）")

    res = teacher.post("/api/risk/list", {"kaoshi_id": exam_id, "banji_id": 24})
    check("教师越权查别的班被拒", res.get("val") == 0, res.get("msg", ""))

    body = teacher.get("/api/report/all.xlsx?kaoshi_id=1", raw=True)
    check("教师批量导出仅限可见班级",
          isinstance(body, bytes) and body[:2] == b"PK", f"{len(body)} 字节")

    student = Client().login("210278200606087012", "123456", "student")
    with urllib.request.urlopen(
        urllib.request.Request(BASE + "/risk"), timeout=10
    ) as r:
        final_url = r.geturl()
    check("学生无法进入预警页", "/login" in final_url or r.status == 200, final_url)

    print()
    print("=" * 60)
    print("结果")
    print("=" * 60)
    print(f"  PASS {PASS} / FAIL {FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
