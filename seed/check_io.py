# -*- coding: utf-8 -*-
"""Exam no.生成 + Excel 导入导出 往返验证"""
import http.cookiejar
import io
import json
import sys
import tempfile
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

# 保证从仓库任意位置（含 `python seed/check_io.py`）都能导入 app 包
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# 往返用的 xlsx 放在临时目录，跑完自动清理
TMPDIR = Path(tempfile.mkdtemp(prefix="xiaoqu-io-"))

BASE = "http://127.0.0.1:8000"
jar = http.cookiejar.CookieJar()
op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))


def post(p, d):
    r = urllib.request.Request(
        BASE + p, data=urllib.parse.urlencode(d).encode(),
        headers={"Content-Type": "application/x-www-form-urlencoded"})
    return json.loads(op.open(r).read().decode())


op.open(urllib.request.Request(
    BASE + "/login",
    data=urllib.parse.urlencode(
        {"username": "admin", "password": "123456", "category": "admin"}).encode(),
    headers={"Content-Type": "application/x-www-form-urlencoded"})).read()

from sqlalchemy import delete, func, select  # noqa: E402
from app.core.database import SessionLocal  # noqa: E402
from app.models import Banji, Chengji, Kaohao  # noqa: E402

# ---------------- 1 考号生成
db = SessionLocal()
db.execute(delete(Kaohao).where(Kaohao.kaoshi_id == 1))
db.commit()
print("Exam 1 numbers after clearing:",
      db.scalar(select(func.count()).select_from(Kaohao).where(Kaohao.kaoshi_id == 1)))
all_bj = [b[0] for b in db.execute(select(Banji.id).order_by(Banji.id)).all()]
db.close()

print("Generate exam numbers:", post("/api/kaohao/generate",
                    {"kaoshi_id": 1, "banji_ids": ",".join(str(x) for x in all_bj)}))
print("Regenerate (idempotent):", post("/api/kaohao/generate",
                        {"kaoshi_id": 1, "banji_ids": ",".join(str(x) for x in all_bj)}))
db = SessionLocal()
n = db.scalar(select(func.count()).select_from(Kaohao).where(Kaohao.kaoshi_id == 1))
kh = db.scalars(select(Kaohao).where(Kaohao.kaoshi_id == 1).order_by(Kaohao.id).limit(3)).all()
print(f"After generation {n} rows, sample:", [(k.kaohao, "class " + str(k.banji_id), "seat " + str(k.paixu)) for k in kh])
dup = db.execute(
    select(Kaohao.kaohao, func.count()).where(Kaohao.kaoshi_id == 1)
    .group_by(Kaohao.kaohao).having(func.count() > 1)).all()
print("Duplicate exam numbers:", dup or "no duplicates")
db.close()

# ---------------- 2 导出
blob = op.open(BASE + "/api/luru/export?kaoshi_id=1").read()
print(f"\nExported xlsx: {len(blob)} bytes, PK signature={blob[:2] == b'PK'}")
tpl = TMPDIR / "_tpl.xlsx"
tpl.write_bytes(blob)

# ---------------- 3 改分数后导入
import openpyxl  # noqa: E402

wb = openpyxl.load_workbook(tpl)
ws = wb.active
hdr = [c.value for c in ws[1]]
print("Header:", hdr)
cols = [i for i, h in enumerate(hdr, 1) if h and "Chinese" in str(h)]
target_row, expect = 2, 55.5
if cols:
    ws.cell(row=target_row, column=cols[0]).value = expect
    print(f"Rewrote row {target_row}, column '{hdr[cols[0] - 1]}' = {expect}")
wbc = TMPDIR / "_tpl2.xlsx"
wb.save(wbc)

# 记录该行对应的学生考号，便于回查
key_col = None
for i, h in enumerate(hdr, 1):
    if h and "Exam no." in str(h):
        key_col = i
kh_key = ws.cell(row=target_row, column=key_col).value if key_col else None
print("Exam number of that row:", kh_key)

boundary = uuid.uuid4().hex
body = io.BytesIO()
fb = wbc.read_bytes()
body.write(f"--{boundary}\r\n".encode())
body.write(b'Content-Disposition: form-data; name="kaoshi_id"\r\n\r\n1\r\n')
body.write(f"--{boundary}\r\n".encode())
body.write(b'Content-Disposition: form-data; name="file"; filename="t.xlsx"\r\n')
body.write(b"Content-Type: application/vnd.openxmlformats-"
           b"officedocument.spreadsheetml.sheet\r\n\r\n")
body.write(fb)
body.write(f"\r\n--{boundary}--\r\n".encode())
req = urllib.request.Request(
    BASE + "/api/luru/import", data=body.getvalue(),
    headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
print("Import result:", op.open(req).read().decode()[:200])

db = SessionLocal()
got = db.execute(
    select(Chengji.defen).join(Kaohao, Chengji.kaohao_id == Kaohao.id)
    .where(Kaohao.kaoshi_id == 1, Kaohao.kaohao == kh_key, Chengji.subject_id == 1)
).first()
db.close()
print(f"Re-query exam no. {kh_key} Chinese = {got}")
print("round-trip consistent:", got is not None and abs(float(got[0]) - expect) < 0.01)
