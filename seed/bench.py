# -*- coding: utf-8 -*-
"""性能基准：测量主要接口的响应时间，输出 P50 / P95。

用法（需先启动服务）：
    python -m seed.bench                # 默认每个接口 20 次
    python -m seed.bench --n 50         # 自定义次数
"""
from __future__ import annotations

import http.cookiejar
import json
import statistics
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

BASE = "http://127.0.0.1:8000"

# (名称, 方法, 路径, 表单数据, 采样次数)
ENDPOINTS = [
    ("GET /healthz (health check)", "GET", "/healthz", None, 30),
    ("GET /welcome (dashboard)", "GET", "/welcome", None, 30),
    ("POST /api/student/list", "POST", "/api/student/list",
     {"page": 1, "limit": 10}, 30),
    ("POST /api/tongji/bj_list", "POST", "/api/tongji/bj_list",
     {"kaoshi_id": 1, "subject_id": 1}, 30),
    ("POST /api/tongji/chart", "POST", "/api/tongji/chart",
     {"kaoshi_id": 1, "level": "bj", "type": "avg"}, 30),
    ("Academic risk POST /api/risk/list", "POST", "/api/risk/list",
     {"kaoshi_id": 1, "banji_id": ""}, 20),
    ("POST /api/risk/chart", "POST", "/api/risk/chart",
     {"kaoshi_id": 1, "banji_id": ""}, 20),
    ("GET /report/banji (printable)", "GET", "/report/banji?kaoshi_id=1&banji_id=1", None, 20),
    ("GET /api/report/all.xlsx (batch)", "GET", "/api/report/all.xlsx?kaoshi_id=1", None, 10),
]


class Client:
    def __init__(self):
        self.jar = http.cookiejar.CookieJar()
        self.op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.jar))

    def request(self, method, path, data=None):
        if method == "GET":
            req = urllib.request.Request(BASE + path)
        else:
            req = urllib.request.Request(
                BASE + path,
                data=urllib.parse.urlencode(data or {}).encode(),
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
        with self.op.open(req) as r:
            return r.read()

    def size_of(self, method, path, data=None):
        return len(self.request(method, path, data))


def percentile(values, p):
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = min(len(ordered) - 1, int(round((p / 100) * (len(ordered) - 1))))
    return ordered[idx]


def main():
    n_override = None
    if "--n" in sys.argv:
        n_override = int(sys.argv[sys.argv.index("--n") + 1])

    client = Client()
    client.request("POST", "/login", {"username": "admin", "password": "123456",
                                      "category": "admin"})

    print(f"Target: {BASE}")
    print(f"{'Endpoint':<42}{'n':>4}{'Mean':>9}{'P50':>8}{'P95':>8}{'Max':>8}{'Payload':>10}")
    print("-" * 92)

    results = []
    for name, method, path, data, n in ENDPOINTS:
        n = n_override or n
        # 预热，避免首次连接/模板编译计入
        for _ in range(2):
            client.size_of(method, path, data)

        times, size = [], 0
        for _ in range(n):
            t0 = time.perf_counter()
            size = client.size_of(method, path, data)
            times.append((time.perf_counter() - t0) * 1000)

        avg = statistics.mean(times)
        row = {
            "name": name, "n": n, "avg": avg, "p50": percentile(times, 50),
            "p95": percentile(times, 95), "max": max(times), "size": size,
        }
        results.append(row)
        kb = size / 1024
        print(f"{name:<42}{n:>4}{avg:>8.1f}ms"
              f"{row['p50']:>6.0f}ms{row['p95']:>6.0f}ms{row['max']:>6.0f}ms{kb:>8.1f}KB")

    slowest = max(results, key=lambda r: r["p95"])
    print("-" * 92)
    print(f"Slowest: {slowest['name']}  P95={slowest['p95']:.0f}ms  payload {slowest['size'] / 1024:.1f}KB")

    # 数据规模
    try:
        from app.core.config import DATA_DIR
        from app.core.database import SessionLocal
        from sqlalchemy import func, select

        from app.models import (
            Attendance, Banji, Chengji, Course, Enrollment, Kaohao, Kaoshi, Student, Teacher,
        )

        db = SessionLocal()
        counts = {
            "Student": Student, "Class": Banji, "Teacher": Teacher, "Exam": Kaoshi,
            "Grade": Chengji, "Exam no.": Kaohao, "Course": Course,
            "Enrolment": Enrollment, "Attendance": Attendance,
        }
        print()
        print("Data volume:")
        for label, model in counts.items():
            n = db.scalar(select(func.count()).select_from(model))
            print(f"  {label:<4}{n:>8}")
        db.close()
        db_file = DATA_DIR / "cj.db"
        print(f"  Database file {db_file.stat().st_size / 1024 / 1024:.2f} MB")
    except Exception as exc:  # pragma: no cover
        print(f"(data volume skipped: {exc})")


if __name__ == "__main__":
    main()
